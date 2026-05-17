import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import TypedDict, Optional

from sqlalchemy import func

from langchain.tools import tool
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

from app.config import settings
from app.db import SessionLocal
from app.time_utils import beijing_now

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
# LLM Factory
# ══════════════════════════════════════════════
def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=settings.openai_api_key,
        openai_api_base=settings.deepseek_api_base,
        temperature=temperature,
        timeout=30,
        max_retries=2,
    )


# ══════════════════════════════════════════════
# LangChain Tools
# ══════════════════════════════════════════════
@tool
def get_user_learning_stats(user_id: str) -> str:
    """获取指定用户的学习统计数据（练习次数和正确率）。"""
    from app.models import PracticeRecordModel
    db = SessionLocal()
    try:
        records = db.query(PracticeRecordModel).filter(PracticeRecordModel.user_id == user_id).all()
        total = len(records)
        correct = sum(1 for r in records if r.is_correct)
        accuracy = round(correct / total * 100) if total > 0 else 0
        return f"练习{total}次，正确率{accuracy}%。"
    finally:
        db.close()


@tool
def get_top_mistakes(user_id: str, limit: int = 3) -> str:
    """获取用户最近的错题记录。"""
    from app.models import PracticeRecordModel
    db = SessionLocal()
    try:
        records = db.query(PracticeRecordModel).filter(PracticeRecordModel.user_id == user_id).all()
        mistakes = [r for r in records if not r.is_correct]
        if not mistakes:
            return "暂无错题记录"
        recent = mistakes[-limit:]
        return "；".join(f"题目{r.question_id}（选错）" for r in recent)
    finally:
        db.close()


@tool
def get_activity_trend(user_id: str) -> str:
    """获取用户近14天学习活跃趋势。"""
    from app.models import PracticeRecordModel, SpeakingRecordModel
    db = SessionLocal()
    try:
        since = beijing_now() - timedelta(days=14)
        practice_days = set()
        speaking_days = set()
        for r in db.query(PracticeRecordModel.answered_at).filter(PracticeRecordModel.user_id == user_id, PracticeRecordModel.answered_at >= since).all():
            practice_days.add(r.answered_at.strftime("%Y-%m-%d") if r.answered_at else "")
        for r in db.query(SpeakingRecordModel.created_at).filter(SpeakingRecordModel.user_id == user_id, SpeakingRecordModel.created_at >= since).all():
            speaking_days.add(r.created_at.strftime("%Y-%m-%d") if r.created_at else "")
        active_days = practice_days | speaking_days
        active_days.discard("")
        if not active_days:
            return "近14天暂无学习活动"
        return f"近14天学习{len(active_days)}天，练习{len(practice_days)}天，口语{len(speaking_days)}天。"
    finally:
        db.close()


@tool
def generate_questions_from_dialogue(dialogue_text: str, difficulty: str) -> str:
    """根据影视对话生成托业风格听力题。输入对话文本和难度，输出JSON格式题目列表。"""
    from app.ai import generate_questions_via_api
    try:
        questions = asyncio.run(generate_questions_via_api(dialogue_text, difficulty))
        return json.dumps(questions, ensure_ascii=False)
    except Exception as e:
        return f"出题失败：{str(e)}"


@tool
def evaluate_pronunciation(audio_base64: str, reference_text: str) -> str:
    """调用讯飞语音评测返回评分（总分、准确度、流畅度、完整度）。"""
    from app.ai import evaluate_audio, DEFAULT_SCORE
    api_key = getattr(settings, "xf_api_key", None)
    api_secret = getattr(settings, "xf_api_secret", None)
    app_id = getattr(settings, "xf_appid", None)
    if not all([api_key, api_secret, app_id]):
        return f"总分{DEFAULT_SCORE['total_score']}，准确度{DEFAULT_SCORE['accuracy']}，流畅度{DEFAULT_SCORE['fluency']}（降级评分）"
    try:
        result = asyncio.run(evaluate_audio(audio_base64, reference_text, app_id, api_key, api_secret))
        return f"总分{result['total_score']}，准确度{result['accuracy']}，流畅度{result['fluency']}，完整度{result['integrity']}"
    except Exception as e:
        return f"评测失败：{str(e)}"


# ══════════════════════════════════════════════
# Quiz Agent
# ══════════════════════════════════════════════
class QuizState(TypedDict):
    clip_id: str
    dialogue_text: str
    difficulty: str
    generated_questions: list[dict]
    error: str


def _quiz_generate(state: QuizState) -> QuizState:
    from app.ai import generate_questions_via_api
    try:
        questions = asyncio.run(generate_questions_via_api(state["dialogue_text"], state["difficulty"]))
        state["generated_questions"] = questions
        state["error"] = ""
    except Exception as e:
        state["error"] = f"出题失败: {str(e)}"
        state["generated_questions"] = []
    return state


def _quiz_format(state: QuizState) -> QuizState:
    if state["error"]:
        return state
    llm = get_llm(temperature=0.4)
    prompt = (
        "将以下题目列表整理为标准 JSON 数组格式。每个元素必须包含 "
        "question (string), options (3个string的数组), answer (int 0-2), "
        f"explanation (string)。原始数据：{json.dumps(state['generated_questions'], ensure_ascii=False)}"
    )
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        state["generated_questions"] = json.loads(content)
    except Exception as e:
        logger.warning(f"格式化题目失败: {e}，使用原始输出")
    return state


quiz_graph = StateGraph(QuizState)
quiz_graph.add_node("generate", _quiz_generate)
quiz_graph.add_node("format", _quiz_format)
quiz_graph.set_entry_point("generate")
quiz_graph.add_edge("generate", "format")
quiz_graph.add_edge("format", END)
quiz_app = quiz_graph.compile()


# ══════════════════════════════════════════════
# Speaking Agent
# ══════════════════════════════════════════════
class SpeakingState(TypedDict):
    user_id: str
    clip_id: Optional[str]
    original_text: str
    audio_base64: str
    score_result: dict
    coach_feedback: str
    chat_history: list
    error: Optional[str]


def _speaking_evaluate(state: SpeakingState) -> SpeakingState:
    try:
        result_str = evaluate_pronunciation(state["audio_base64"], state["original_text"])
        state["score_result"] = _parse_speaking_score(result_str)
        state["error"] = None
    except Exception as e:
        logger.error(f"评测节点失败: {e}")
        state["score_result"] = {"total_score": 70, "accuracy": 70, "fluency": 70, "integrity": 70}
        state["error"] = str(e)
    return state


def _speaking_feedback(state: SpeakingState) -> SpeakingState:
    score = state["score_result"]
    llm = get_llm(temperature=0.7)
    history_context = ""
    if state.get("chat_history"):
        last = state["chat_history"][-1]
        history_context = f"用户上次说：{last}\n"
    prompt = (
        f"你是一位温暖的口语教练。用户刚刚完成了英语跟读练习。\n"
        f"{history_context}"
        f"原台词是：{state['original_text'][:200]}\n"
        f"评测得分为：总分{score.get('total_score', 70)}，"
        f"准确度{score.get('accuracy', 70)}，流畅度{score.get('fluency', 70)}。\n"
        "请写一段鼓励性的中文反馈（80字以内），先肯定努力，再给1个具体改进建议，"
        "最后以一个问题结尾引导用户继续练习。"
    )
    try:
        response = llm.invoke(prompt)
        state["coach_feedback"] = response.content.strip()
    except Exception as e:
        logger.error(f"反馈生成失败: {e}")
        state["coach_feedback"] = "发音不错！试着放慢速度，让每个音节都清晰。想再练一次吗？"
    state.setdefault("chat_history", [])
    state["chat_history"].append(state["coach_feedback"])
    return state


def _parse_speaking_score(result_str: str) -> dict:
    score = {"total_score": 70, "accuracy": 70, "fluency": 70, "integrity": 70}
    try:
        parts = result_str.replace("，", ",").split(",")
        for part in parts:
            for key in ["总分", "准确度", "流畅度", "完整度"]:
                if key in part:
                    value = "".join(filter(lambda x: x.isdigit() or x == ".", part))
                    if key == "总分":
                        score["total_score"] = float(value)
                    elif key == "准确度":
                        score["accuracy"] = float(value)
                    elif key == "流畅度":
                        score["fluency"] = float(value)
                    elif key == "完整度":
                        score["integrity"] = float(value)
    except (ValueError, AttributeError):
        pass
    return score


speaking_graph = StateGraph(SpeakingState)
speaking_graph.add_node("evaluate", _speaking_evaluate)
speaking_graph.add_node("feedback", _speaking_feedback)
speaking_graph.set_entry_point("evaluate")
speaking_graph.add_edge("evaluate", "feedback")
speaking_graph.add_edge("feedback", END)
speaking_app = speaking_graph.compile(checkpointer=MemorySaver())


# ══════════════════════════════════════════════
# Report Agent
# ══════════════════════════════════════════════
class ReportState(TypedDict):
    student_id: str
    stats: str
    mistakes: str
    activity_trend: str
    narrative_report: str


def _report_fetch(state: ReportState) -> ReportState:
    try:
        state["stats"] = get_user_learning_stats.invoke({"user_id": state["student_id"]})
    except Exception as e:
        logger.warning("获取学习统计失败: %s", e)
        state["stats"] = "暂无学习数据"
    try:
        state["mistakes"] = get_top_mistakes.invoke({"user_id": state["student_id"], "limit": 3})
    except Exception as e:
        logger.warning("获取错题失败: %s", e)
        state["mistakes"] = "暂无错题数据"
    try:
        state["activity_trend"] = get_activity_trend.invoke({"user_id": state["student_id"]})
    except Exception as e:
        logger.warning("获取活跃趋势失败: %s", e)
        state["activity_trend"] = "暂无活跃数据"
    return state


def _report_write(state: ReportState) -> ReportState:
    try:
        llm = get_llm(temperature=0.5)
        prompt = f"""你是一位善于激励的学习分析师，正在为一位英语学习者撰写个性化的学习报告。

请根据以下学习数据，用中文写一段"英雄之旅"风格的鼓励式学习报告（200字左右）：

- 学习统计：{state['stats']}
- 常见错题：{state['mistakes']}
- 学习活跃：{state['activity_trend']}

报告要求：
1. 以温暖的语气开头，肯定学生的努力和进步
2. 识别当前学习中的挑战（结合错题数据）
3. 给出2-3条具体的、可操作的下一步学习建议
4. 以一段鼓舞人心的话语结尾，激发学习动力

直接输出报告内容，不要加任何前缀说明。"""
        response = llm.invoke(prompt)
        state["narrative_report"] = response.content.strip()
    except Exception as e:
        logger.error("生成叙事报告失败: %s", e)
        state["narrative_report"] = "同学你好！根据你的学习数据，我们看到了你的努力。建议继续保持每日练习，重点关注错题本中的薄弱环节。持续进步，你一定可以突破自己！"
    return state


report_graph = StateGraph(ReportState)
report_graph.add_node("fetch", _report_fetch)
report_graph.add_node("write", _report_write)
report_graph.set_entry_point("fetch")
report_graph.add_edge("fetch", "write")
report_graph.add_edge("write", END)
report_app = report_graph.compile()


# ══════════════════════════════════════════════
# Interest Agent
# ══════════════════════════════════════════════
class InterestState(TypedDict):
    user_preference: str
    recommended_clips: list[str]


def _interest_retrieve(state: InterestState) -> InterestState:
    from app.models import VideoClipModel
    db = SessionLocal()
    try:
        clips = db.query(VideoClipModel).all()
        if not clips:
            state["recommended_clips"] = []
            return state
        texts = []
        clip_ids = []
        for clip in clips:
            text = (clip.summary or "") + " " + (clip.dialogue_text or "")[:200]
            texts.append(text)
            clip_ids.append(str(clip.id))
        embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key, openai_api_base=settings.deepseek_api_base)
        vectorstore = FAISS.from_texts(texts, embeddings)
        docs = vectorstore.similarity_search(state["user_preference"], k=3)
        state["recommended_clips"] = [clip_ids[texts.index(doc.page_content)] for doc in docs]
    except Exception:
        state["recommended_clips"] = []
    finally:
        db.close()
    return state


interest_graph = StateGraph(InterestState)
interest_graph.add_node("retrieve", _interest_retrieve)
interest_graph.set_entry_point("retrieve")
interest_graph.add_edge("retrieve", END)
interest_app = interest_graph.compile()


# ══════════════════════════════════════════════
# Student Agent Tools
# ══════════════════════════════════════════════
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool as lc_tool


@lc_tool
def get_current_time(config: RunnableConfig) -> str:
    """获取当前的准确日期和时间（北京时间）。"""
    from datetime import datetime, timezone, timedelta
    beijing = timezone(timedelta(hours=8))
    now = datetime.now(beijing)
    return now.strftime("%Y年%m月%d日 %H:%M (北京时间，周%w") \
        .replace("周0", "周日").replace("周1", "周一").replace("周2", "周二") \
        .replace("周3", "周三").replace("周4", "周四").replace("周5", "周五").replace("周6", "周六") \
        + "）"


@lc_tool
def get_my_stats(config: RunnableConfig) -> str:
    """获取当前登录学生的学习统计：总练习题数、正确率、各难度正确率。"""
    user_id = config.get("configurable", {}).get("user_id", "")
    from app.models import PracticeRecordModel, QuestionModel
    db = SessionLocal()
    try:
        records = db.query(PracticeRecordModel).filter(
            PracticeRecordModel.user_id == user_id
        ).all()
        if not records:
            return "你还没有任何练习记录，快去影视片段库开始学习吧！"
        total = len(records)
        correct = sum(1 for r in records if r.is_correct)
        accuracy = round(correct / total * 100, 1) if total > 0 else 0

        # 各难度统计
        diff_stats = {}
        for r in records:
            q = db.query(QuestionModel).filter(QuestionModel.id == r.question_id).first()
            d = q.difficulty if q else "未知"
            if d not in diff_stats:
                diff_stats[d] = {"total": 0, "correct": 0}
            diff_stats[d]["total"] += 1
            if r.is_correct:
                diff_stats[d]["correct"] += 1

        parts = [f"共练习 {total} 次，总正确率 {accuracy}%"]
        for d, s in sorted(diff_stats.items()):
            da = round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else 0
            parts.append(f"{d}级：{s['total']}题，正确率{da}%")
        return "；".join(parts)
    finally:
        db.close()


@lc_tool
def get_my_mistakes(config: RunnableConfig) -> str:
    """获取当前学生的最近错题记录，包含题目内容和正确答案。"""
    user_id = config.get("configurable", {}).get("user_id", "")
    from app.models import PracticeRecordModel, QuestionModel
    db = SessionLocal()
    try:
        records = db.query(PracticeRecordModel).filter(
            PracticeRecordModel.user_id == user_id
        ).order_by(PracticeRecordModel.answered_at.desc()).limit(20).all()
        mistakes = [r for r in records if not r.is_correct]
        if not mistakes:
            return "不错！你目前没有答错的题目。"
        recent = mistakes[:5]
        lines = []
        for r in recent:
            q = db.query(QuestionModel).filter(QuestionModel.id == r.question_id).first()
            if q and q.content:
                question_text = q.content.get("question", "")[:60]
                correct_idx = q.content.get("answer", -1)
                correct_text = q.content.get("options", [])[correct_idx] if 0 <= correct_idx < len(q.content.get("options", [])) else ""
                lines.append(f"题目：{question_text}... 正确答案：{correct_text}")
        return "\n".join(lines) if lines else "暂无错题记录详情"
    finally:
        db.close()


@lc_tool
def get_my_activity(config: RunnableConfig) -> str:
    """获取当前学生近14天的学习活跃趋势。"""
    user_id = config.get("configurable", {}).get("user_id", "")
    from app.models import PracticeRecordModel, SpeakingRecordModel
    db = SessionLocal()
    try:
        since = beijing_now() - timedelta(days=14)
        practice_days = set()
        speaking_days = set()
        for r in db.query(PracticeRecordModel.answered_at).filter(
            PracticeRecordModel.user_id == user_id,
            PracticeRecordModel.answered_at >= since,
        ).all():
            if r.answered_at:
                practice_days.add(r.answered_at.strftime("%Y-%m-%d"))
        for r in db.query(SpeakingRecordModel.created_at).filter(
            SpeakingRecordModel.user_id == user_id,
            SpeakingRecordModel.created_at >= since,
        ).all():
            if r.created_at:
                speaking_days.add(r.created_at.strftime("%Y-%m-%d"))
        active_days = practice_days | speaking_days
        if not active_days:
            return "近14天你还未开始学习，快去练习吧！"
        return f"近14天活跃 {len(active_days)} 天（练习 {len(practice_days)} 天，口语 {len(speaking_days)} 天）"
    finally:
        db.close()


@lc_tool
def search_clips(query: str, config: RunnableConfig) -> str:
    """搜索影视片段。query 为中文或英文关键词（如"动画""家庭""职场""friends"），用空格分隔多个词。
    返回 JSON 数组，每项含 id/title/category/difficulty/summary/match_score 字段。
    请用宽泛关键词搜索，不要用精确标题。"""
    from app.models import VideoClipModel
    import re
    db = SessionLocal()
    try:
        clips = db.query(VideoClipModel).all()
        if not clips:
            return "暂无可用影视片段"

        # 将 query 拆分为多个关键词
        keywords = [kw.strip().lower() for kw in re.split(r'[\s,，、]+', query) if kw.strip()]
        if not keywords:
            keywords = [query.lower().strip()]

        scored = []
        for clip in clips:
            # 搜索四个字段
            search_text = " ".join([
                clip.title or "",
                clip.summary or "",
                (clip.dialogue_text or "")[:500],
                clip.category or "",
            ]).lower()

            score = 0
            for kw in keywords:
                if kw in search_text:
                    score += 1
                # 额外加分：category 精确匹配
                if kw == (clip.category or "").lower():
                    score += 2

            if score > 0:
                scored.append((score, clip))

        # 按匹配分数降序排列，返回前 5 条
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:5]

        if not top:
            # 无结果时给出提示
            cats = list(set(clip.category for clip in clips if clip.category))
            return f"未找到匹配 '{query}' 的片段。可用的分类有：{', '.join(cats)}。请尝试用更宽泛的关键词搜索。"

        results = []
        for score, c in top:
            results.append({
                "id": str(c.id),
                "title": c.title,
                "category": c.category or "未分类",
                "difficulty": c.difficulty or "未知",
                "summary": (c.summary or "无简介")[:80],
                "match_score": min(score, 5),  # 1-5 分
            })
        return json.dumps(results, ensure_ascii=False)
    finally:
        db.close()


@lc_tool
def get_clip_info(clip_title: str, config: RunnableConfig) -> str:
    """根据片段标题获取影视片段的详细信息（难度、类别、对话摘要、字幕来源）。"""
    from app.models import VideoClipModel
    db = SessionLocal()
    try:
        clip = db.query(VideoClipModel).filter(
            VideoClipModel.title.contains(clip_title)
        ).first()
        if not clip:
            return f"未找到标题包含 '{clip_title}' 的片段"
        dialogue_preview = (clip.dialogue_text or "")[:200]
        return (
            f"标题：{clip.title}\n难度：{clip.difficulty}级\n类别：{clip.category or '未知'}\n"
            f"摘要：{clip.summary or '暂无'}\n对话预览：{dialogue_preview}..."
        )
    finally:
        db.close()


# ══════════════════════════════════════════════
# Teacher Advanced Tools
# ══════════════════════════════════════════════
@lc_tool
def compare_students(student_names: str, config: RunnableConfig) -> str:
    """横向对比 2-3 个学生的学习数据。student_names 为逗号分隔的用户名，如"zhangsan,lisi"。"""
    from app.models import UserModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    names = [n.strip() for n in student_names.split(",") if n.strip()]
    if len(names) < 2 or len(names) > 3:
        return "请指定 2-3 个学生用户名（逗号分隔）"

    db = SessionLocal()
    try:
        results = []
        for name in names:
            student = db.query(UserModel).filter(
                UserModel.username == name, UserModel.role == "student",
                UserModel.teacher_id == teacher_id,
            ).first()
            if not student:
                results.append(f"❌ {name}: 未找到")
                continue
            stats = get_user_learning_stats.invoke({"user_id": str(student.id)})
            activity = get_activity_trend.invoke({"user_id": str(student.id)})
            results.append(f"**{name}**（{student.level or '未定级'}级）\n  {stats}\n  活跃：{activity}")

        header = f"**学生对比分析**（{len(names)}人）\n"
        return header + "\n---\n".join(results)
    finally:
        db.close()


@lc_tool
def get_weekly_digest(config: RunnableConfig) -> str:
    """生成本周班级摘要：活跃人数、练习总量、口语次数、预警名单、进步与退步学生。"""
    from app.models import UserModel, PracticeRecordModel, SpeakingRecordModel, TeacherGroupModel
    from datetime import timedelta
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""

    db = SessionLocal()
    try:
        now = beijing_now()
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        students = db.query(UserModel).filter(
            UserModel.teacher_id == teacher_id, UserModel.role == "student"
        ).all()
        if not students:
            return "本周暂无学生数据"

        total_students = len(students)
        active = 0
        total_practice = 0
        total_speaking = 0
        student_stats = []

        for s in students:
            sid = str(s.id)
            p_count = db.query(PracticeRecordModel).filter(
                PracticeRecordModel.user_id == sid,
                PracticeRecordModel.answered_at >= week_start,
            ).count()
            s_count = db.query(SpeakingRecordModel).filter(
                SpeakingRecordModel.user_id == sid,
                SpeakingRecordModel.created_at >= week_start,
            ).count()
            if p_count + s_count > 0:
                active += 1
            total_practice += p_count
            total_speaking += s_count
            student_stats.append((s.username or "未命名", s.level or "未定级", p_count, s_count))

        student_stats.sort(key=lambda x: x[2] + x[3], reverse=True)

        lines = [
            f"## 本周班级摘要（{now.strftime('%m月%d日')}）\n",
            f"- 学生总数：{total_students} 人，本周活跃：{active} 人",
            f"- 本周练习：{total_practice} 次，口语练习：{total_speaking} 次",
        ]
        if student_stats:
            top = student_stats[0]
            bottom = student_stats[-1]
            lines.append(f"- 最活跃：{top[0]}（{top[3]}次口语 + {top[2]}次练习）")
            if len(student_stats) > 1:
                lines.append(f"- 需关注：{bottom[0]}（本周仅 {bottom[2] + bottom[3]} 次活动）")

        return "\n".join(lines)
    finally:
        db.close()


# ══════════════════════════════════════════════
# Teacher Agent Tools
# ══════════════════════════════════════════════
@lc_tool
def list_my_students(keyword: str = "", config: RunnableConfig = None) -> str:
    """列出当前教师的学生列表。可选 keyword 参数按用户名或邮箱搜索。"""
    from app.models import UserModel, TeacherGroupModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        query = db.query(UserModel).filter(
            UserModel.role == "student"
        )
        if teacher_id:
            group_ids = db.query(TeacherGroupModel.id).filter(
                TeacherGroupModel.teacher_id == teacher_id
            ).all()
            group_ids = [g[0] for g in group_ids]
            if group_ids:
                query = query.filter(UserModel.group_id.in_(group_ids))
            else:
                return "暂无学生记录"
        if keyword:
            query = query.filter(
                (UserModel.username.contains(keyword)) |
                (UserModel.email.contains(keyword))
            )
        students = query.limit(30).all()
        if not students:
            return "暂无学生记录"
        lines = []
        for s in students:
            name = s.username or "匿名学生"
            level = s.level or "未定级"
            lines.append(f"- {name}（{level}级）{s.email or ''}")
        return "\n".join(lines)
    finally:
        db.close()


@lc_tool
def get_student_level_distribution(config: RunnableConfig) -> str:
    """获取当前教师关联学生的等级分布统计（A/B/C/未定级 各多少人）。"""
    from app.models import UserModel, TeacherGroupModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        group_ids = db.query(TeacherGroupModel.id).filter(
            TeacherGroupModel.teacher_id == teacher_id
        ).all()
        group_ids = [g[0] for g in group_ids]
        query = db.query(UserModel).filter(UserModel.role == "student")
        if group_ids:
            query = query.filter(UserModel.group_id.in_(group_ids))
        else:
            return "暂无学生记录"
        students = query.all()
        dist = {"A": 0, "B": 0, "C": 0, "未定级": 0}
        for s in students:
            key = s.level if s.level in ("A", "B", "C") else "未定级"
            dist[key] += 1
        return f"A级 {dist['A']} 人，B级 {dist['B']} 人，C级 {dist['C']} 人，未定级 {dist['未定级']} 人（共 {len(students)} 人）"
    finally:
        db.close()


@lc_tool
def get_student_learning_detail(student_name: str, config: RunnableConfig) -> str:
    """获取指定学生的详细学情，包含练习统计、难度正确率、口语统计和最近错题。参数 student_name 为学生用户名。"""
    from app.models import UserModel, PracticeRecordModel, SpeakingRecordModel, QuestionModel
    db = SessionLocal()
    try:
        student = db.query(UserModel).filter(
            UserModel.username == student_name, UserModel.role == "student"
        ).first()
        if not student:
            return f"未找到学生 '{student_name}'"

        records = db.query(PracticeRecordModel).filter(
            PracticeRecordModel.user_id == student.id
        ).all()
        total = len(records)
        correct = sum(1 for r in records if r.is_correct)
        accuracy = round(correct / total * 100, 1) if total > 0 else 0

        diff_stats = {}
        for r in records:
            q = db.query(QuestionModel).filter(QuestionModel.id == r.question_id).first()
            d = q.difficulty if q else "未知"
            if d not in diff_stats:
                diff_stats[d] = {"total": 0, "correct": 0}
            diff_stats[d]["total"] += 1
            if r.is_correct:
                diff_stats[d]["correct"] += 1

        speaking_count = db.query(SpeakingRecordModel).filter(
            SpeakingRecordModel.user_id == student.id
        ).count()

        mistakes = [r for r in records if not r.is_correct][:3]
        mistake_lines = []
        for r in mistakes:
            q = db.query(QuestionModel).filter(QuestionModel.id == r.question_id).first()
            if q and q.content:
                mistake_lines.append(f"  - {q.content.get('question', '')[:50]}...")

        level_info = student.level or "未定级"
        parts = [
            f"学生：{student.username}（{level_info}级）",
            f"练习 {total} 次，正确率 {accuracy}%",
            f"口语练习 {speaking_count} 次",
        ]
        for d, s in sorted(diff_stats.items()):
            da = round(s["correct"] / s["total"] * 100, 1) if s["total"] > 0 else 0
            parts.append(f"{d}级正确率：{da}%（{s['total']}题）")
        if mistake_lines:
            parts.append("最近错题：\n" + "\n".join(mistake_lines))
        return "\n".join(parts)
    finally:
        db.close()


@lc_tool
def generate_learning_report(student_name: str, config: RunnableConfig) -> str:
    """为指定学生生成一份"英雄之旅"风格的叙事学习报告。参数 student_name 为学生用户名。"""
    from app.models import UserModel
    db = SessionLocal()
    try:
        student = db.query(UserModel).filter(
            UserModel.username == student_name, UserModel.role == "student"
        ).first()
        if not student:
            return f"未找到学生 '{student_name}'"

        result = report_app.invoke({
            "student_id": str(student.id),
            "stats": "", "mistakes": "", "activity_trend": "", "narrative_report": ""
        })
        return result.get("narrative_report", "报告生成失败，请稍后重试")
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        return f"报告生成出错：{str(e)}"
    finally:
        db.close()


@lc_tool
def generate_group_report(group_name: str, config: RunnableConfig) -> str:
    """为指定分组的全体学生生成一份统一的班级学情报告。
    参数 group_name 为分组名称（如"公选1班"）。
    注意：当教师要求分析某个班级/分组的整体情况时，直接调用此工具，
    不要对每个学生单独调用 generate_learning_report 再拼接。"""
    from app.models import UserModel, TeacherGroupModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        group = db.query(TeacherGroupModel).filter(
            TeacherGroupModel.name == group_name,
            TeacherGroupModel.teacher_id == teacher_id,
        ).first()
        if not group:
            return f"未找到分组 '{group_name}'"

        students = db.query(UserModel).filter(
            UserModel.group_id == group.id, UserModel.role == "student"
        ).all()
        if not students:
            return f"分组 '{group_name}' 中没有学生"

        # 收集每位学生的数据摘要
        student_summaries = []
        for s in students:
            uid = str(s.id)
            stats_text = get_user_learning_stats.invoke({"user_id": uid})
            mistakes_text = get_top_mistakes.invoke({"user_id": uid, "limit": 3})
            activity_text = get_activity_trend.invoke({"user_id": uid})
            student_summaries.append({
                "name": s.username or "未命名",
                "level": s.level or "未定级",
                "stats": stats_text,
                "mistakes": mistakes_text,
                "activity": activity_text,
            })

        # 构建一份整体报告
        lines = [f"## {group.name} 学情报告\n"]
        lines.append(f"共 {len(students)} 名学生：")
        for s in student_summaries:
            lines.append(f"- {s['name']}（{s['level']}级）")
            lines.append(f"  {s['stats']}")
            lines.append(f"  活跃：{s['activity']}")
            if s["mistakes"]:
                lines.append(f"  高频错题：{s['mistakes']}")

        data_text = "\n".join(lines)

        llm = get_llm(temperature=0.5)
        prompt = f"""你是一位专业的教学分析师。请根据以下班级数据，撰写一份清晰、结构化的学情报告。

{data_text}

报告要求：
1. 班级整体概况（总人数、等级分布、整体正确率与口语均分估算）
2. 逐个学生分析（姓名、等级、亮点与薄弱点、建议）
3. 班级共性问题和教学建议（2-3条）
4. 语气专业、客观，避免过于花哨的比喻

直接输出报告内容，用 Markdown 组织格式。"""

        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        logger.error(f"生成班级报告失败: {e}")
        return f"班级报告生成出错：{str(e)}"
    finally:
        db.close()


@lc_tool
def list_my_groups(config: RunnableConfig) -> str:
    """列出当前教师创建的所有分组及每组人数。"""
    from app.models import TeacherGroupModel, UserModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        groups = db.query(TeacherGroupModel).filter(
            TeacherGroupModel.teacher_id == teacher_id
        ).all()
        if not groups:
            return "你还没有创建任何分组，可以在分组管理页面创建。"
        lines = []
        for g in groups:
            count = db.query(UserModel).filter(UserModel.group_id == g.id).count()
            lines.append(f"- {g.name}（{count}人）{'— ' + g.description if g.description else ''}")
        return "\n".join(lines)
    finally:
        db.close()


@lc_tool
def get_group_students_detail(group_name: str, config: RunnableConfig) -> str:
    """获取指定分组内所有学生的列表和基本信息。参数 group_name 为分组名称。"""
    from app.models import TeacherGroupModel, UserModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        group = db.query(TeacherGroupModel).filter(
            TeacherGroupModel.teacher_id == teacher_id,
            TeacherGroupModel.name == group_name,
        ).first()
        if not group:
            return f"未找到分组 '{group_name}'"
        students = db.query(UserModel).filter(UserModel.group_id == group.id).all()
        if not students:
            return f"分组 '{group_name}' 暂无学生"
        lines = [f"分组 {group_name}（{len(students)}人）："]
        for s in students:
            name = s.username or "匿名学生"
            level = s.level or "未定级"
            lines.append(f"- {name}（{level}级）")
        return "\n".join(lines)
    finally:
        db.close()


# ══════════════════════════════════════════════
# Student Agent — New Tools (Phase 4)
# ══════════════════════════════════════════════
@lc_tool
def get_my_tasks(config: RunnableConfig) -> str:
    """获取当前学生的任务列表和各项完成进度。在制定学习计划时调用。"""
    from app.crud import get_student_tasks
    user_id = config.get("configurable", {}).get("user_id", "")
    db = SessionLocal()
    try:
        tasks = get_student_tasks(db, user_id)
        if not tasks:
            return "你目前没有学习任务。去互动中心查看教师是否布置了新任务。"
        lines = []
        for t in tasks:
            pct = 0
            total = (t.get("practice_goal", 0) + t.get("speaking_goal", 0) +
                     t.get("free_talk_goal", 0) + t.get("clip_goal", 0))
            done = (t.get("practice_done", 0) + t.get("speaking_done", 0) +
                    t.get("free_talk_done", 0) + t.get("clips_done", 0))
            if total > 0:
                pct = round(done / total * 100)
            status = "已完成" if t.get("is_completed") else "进行中"
            deadline = f"，截止{t['deadline']}" if t.get("deadline") else ""
            lines.append(
                f"- {t['title']}（{status}，{pct}%{deadline}）："
                f"练习{t.get('practice_done',0)}/{t.get('practice_goal',0)}，"
                f"口语{t.get('speaking_done',0)}/{t.get('speaking_goal',0)}，"
                f"对话{t.get('free_talk_done',0)}/{t.get('free_talk_goal',0)}，"
                f"片段{t.get('clips_done',0)}/{t.get('clip_goal',0)}"
            )
        return "\n".join(lines)
    finally:
        db.close()


@lc_tool
def generate_my_report(config: RunnableConfig) -> str:
    """为学生生成"英雄之旅"风格的学情叙事报告。"""
    user_id = config.get("configurable", {}).get("user_id", "")
    from app.models import UserModel
    db = SessionLocal()
    try:
        student = db.query(UserModel).filter(UserModel.id == user_id).first()
        student_name = student.username if student else "同学"
        result = report_app.invoke({
            "student_id": user_id,
            "stats": "", "mistakes": "", "activity_trend": "", "narrative_report": ""
        })
        return f"以下是 {student_name} 的学习报告：\n\n{result.get('narrative_report', '报告生成失败')}"
    except Exception as e:
        logger.error(f"生成学生报告失败: {e}")
        return f"报告生成出错：{str(e)}"
    finally:
        db.close()


# ══════════════════════════════════════════════
# 单词本工具
# ══════════════════════════════════════════════
@lc_tool
def get_my_vocabulary_stats(config: RunnableConfig) -> str:
    """获取当前用户的单词本统计：总单词数、已掌握数与未掌握数、最近添加的单词。"""
    from app.models import UserVocabularyModel
    uid = config.get("configurable", {}).get("user_id", "") if config else ""
    if not uid:
        return "无法获取用户信息"
    db = SessionLocal()
    try:
        total = db.query(UserVocabularyModel).filter(UserVocabularyModel.user_id == uid).count()
        mastered = db.query(UserVocabularyModel).filter(
            UserVocabularyModel.user_id == uid, UserVocabularyModel.mastered.is_(True)
        ).count()
        recent = db.query(UserVocabularyModel).filter(
            UserVocabularyModel.user_id == uid
        ).order_by(UserVocabularyModel.created_at.desc()).limit(5).all()
        lines = [f"单词本共 {total} 个单词，已掌握 {mastered} 个，未掌握 {total - mastered} 个"]
        if recent:
            lines.append("最近添加：")
            for w in recent:
                tag = "✓" if w.mastered else "○"
                lines.append(f"  {tag} {w.word}")
        return "\n".join(lines)
    finally:
        db.close()


@lc_tool
def get_my_weak_words(config: RunnableConfig) -> str:
    """获取用户单词本中未掌握的单词列表，用于复习建议。"""
    from app.models import UserVocabularyModel
    uid = config.get("configurable", {}).get("user_id", "") if config else ""
    if not uid:
        return "无法获取用户信息"
    db = SessionLocal()
    try:
        words = db.query(UserVocabularyModel).filter(
            UserVocabularyModel.user_id == uid, UserVocabularyModel.mastered.is_(False)
        ).order_by(UserVocabularyModel.created_at.desc()).limit(10).all()
        if not words:
            return "太棒了！你的单词本中所有单词都已掌握。"
        lines = ["以下单词尚未掌握，建议复习："]
        for w in words:
            lines.append(f"- {w.word}: {w.definition or '点击查看释义'}")
        return "\n".join(lines)
    finally:
        db.close()


@lc_tool
def get_speaking_trend(config: RunnableConfig) -> str:
    """分析用户口语进步趋势，返回近30天口语总分/准确度/流畅度变化摘要。"""
    from app.models import SpeakingRecordModel
    uid = config.get("configurable", {}).get("user_id", "") if config else ""
    if not uid:
        return "无法获取用户信息"
    db = SessionLocal()
    try:
        from datetime import timedelta
        since = beijing_now() - timedelta(days=30)
        records = db.query(SpeakingRecordModel).filter(
            SpeakingRecordModel.user_id == uid,
            SpeakingRecordModel.created_at >= since,
        ).order_by(SpeakingRecordModel.created_at.asc()).all()
        if not records:
            return "最近30天没有口语练习记录，快去练习吧！"
        total = len(records)
        scores = [r.score_json.get("total_score") for r in records if r.score_json and r.score_json.get("total_score")]
        accs = [r.score_json.get("accuracy") for r in records if r.score_json and r.score_json.get("accuracy")]
        flus = [r.score_json.get("fluency") for r in records if r.score_json and r.score_json.get("fluency")]
        if not scores:
            return f"共有 {total} 条口语记录，但暂无有效评分数据"

        first_half = scores[:len(scores)//2] if len(scores) >= 4 else scores[:1]
        second_half = scores[len(scores)//2:] if len(scores) >= 4 else scores[-1:]
        avg_first = round(sum(first_half) / len(first_half), 1)
        avg_second = round(sum(second_half) / len(second_half), 1)
        trend = "上升" if avg_second > avg_first else ("下降" if avg_second < avg_first else "持平")

        return (
            f"口语练习共 {total} 次（近30天）。\n"
            f"总分趋势：{trend}（前期均分 {avg_first} → 近期均分 {avg_second}）\n"
            f"最佳总分：{max(scores)}，最低总分：{min(scores)}\n"
            f"平均准确度：{round(sum(accs)/len(accs),1) if accs else '-'}，"
            f"平均流畅度：{round(sum(flus)/len(flus),1) if flus else '-'}"
        )
    finally:
        db.close()


@lc_tool
def get_smart_review_plan(config: RunnableConfig) -> str:
    """生成个性化复习计划：综合单词本薄弱词、高频错题和当前任务，给出今日复习建议。"""
    uid = config.get("configurable", {}).get("user_id", "") if config else ""
    if not uid:
        return "无法获取用户信息"
    db = SessionLocal()
    try:
        # 薄弱单词
        from app.models import UserVocabularyModel
        weak_words = db.query(UserVocabularyModel).filter(
            UserVocabularyModel.user_id == uid, UserVocabularyModel.mastered.is_(False)
        ).limit(5).all()
        # 高频错题
        mistakes = get_top_mistakes.invoke({"user_id": uid, "limit": 3})
        # 当前任务
        tasks = get_my_tasks.invoke({})

        lines = ["📋 **今日复习计划**\n"]
        if weak_words:
            lines.append("**单词复习**（以下词汇尚未掌握）：")
            for w in weak_words:
                lines.append(f"- {w.word}: {w.definition or '查看释义'}")
        if mistakes and "暂无" not in mistakes:
            lines.append(f"\n**错题回顾**：{mistakes}")
        if tasks and "没有" not in tasks:
            lines.append(f"\n**任务进度**：{tasks}")
        if not weak_words and ("暂无" in mistakes) and ("没有" in tasks):
            lines.append("暂无需要复习的内容，继续保持！")

        return "\n".join(lines)
    finally:
        db.close()


# ══════════════════════════════════════════════
# Teacher Agent — New Tools (Phase 4)
# ══════════════════════════════════════════════
@lc_tool
def create_task_tool(
    title: str,
    practice_goal: int = 10,
    speaking_goal: int = 5,
    free_talk_goal: int = 2,
    clip_goal: int = 3,
    accuracy_goal: float = 0.0,
    target_group_name: str = "",
    deadline_str: str = "",
    config: RunnableConfig = None,
) -> str:
    """根据学情创建学习任务。参数：title(必填), practice_goal(练习次数), speaking_goal(口语次数),
    free_talk_goal(对话次数), clip_goal(片段数), accuracy_goal(目标正确率%),
    target_group_name(目标分组名，空=全部), deadline_str(截止日期YYYY-MM-DD)。"""
    from app.models import TeacherGroupModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        target_group_id = None
        target_type = "all"
        if target_group_name:
            group = db.query(TeacherGroupModel).filter(
                TeacherGroupModel.teacher_id == teacher_id,
                TeacherGroupModel.name == target_group_name,
            ).first()
            if group:
                target_group_id = str(group.id)
                target_type = "group"

        from datetime import datetime as dt
        deadline = None
        if deadline_str:
            try:
                deadline = dt.fromisoformat(deadline_str)
            except ValueError:
                pass

        kwargs = {
            "description": f"AI 自动创建：练习{title}", "target_type": target_type,
            "target_group_id": target_group_id,
            "practice_goal": practice_goal, "speaking_goal": speaking_goal,
            "free_talk_goal": free_talk_goal, "clip_goal": clip_goal,
            "accuracy_goal": accuracy_goal if accuracy_goal > 0 else None,
            "deadline": deadline,
        }
        from app.crud import create_task_crud
        task = create_task_crud(db, teacher_id, title, **kwargs)
        return f"任务「{title}」创建成功！目标：练习{practice_goal}次/口语{speaking_goal}次/对话{free_talk_goal}次/片段{clip_goal}个。"
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        return f"创建任务失败：{str(e)}"
    finally:
        db.close()


@lc_tool
def send_announcement_tool(
    title: str,
    content: str,
    target_type: str = "all",
    target_group_name: str = "",
    config: RunnableConfig = None,
) -> str:
    """发布公告。参数：title(标题), content(内容), target_type(all|group), target_group_name(分组名)。"""
    from app.models import TeacherGroupModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        target_group_id = None
        if target_type == "group" and target_group_name:
            group = db.query(TeacherGroupModel).filter(
                TeacherGroupModel.teacher_id == teacher_id,
                TeacherGroupModel.name == target_group_name,
            ).first()
            if group:
                target_group_id = str(group.id)
        from app.crud import create_announcement_crud
        ann = create_announcement_crud(db, teacher_id, title, content, target_type, target_group_id)
        return f"公告「{title}」已发布。"
    except Exception as e:
        return f"发布公告失败：{str(e)}"
    finally:
        db.close()


@lc_tool
def send_group_message_tool(
    content: str,
    student_name: str = "",
    group_name: str = "",
    config: RunnableConfig = None,
) -> str:
    """发送私信（单发或群发）。参数：content(消息内容), student_name(学生用户名，优先级高于group_name),
    group_name(分组名，发给该组全部学生)。"""
    from app.models import TeacherGroupModel, UserModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        receiver_id = None
        gid = None
        if student_name:
            student = db.query(UserModel).filter(
                UserModel.username == student_name, UserModel.role == "student"
            ).first()
            if student:
                receiver_id = str(student.id)
        if not receiver_id and group_name:
            groups = db.query(TeacherGroupModel).filter(
                TeacherGroupModel.teacher_id == teacher_id,
                TeacherGroupModel.name == group_name,
            ).all()
            if groups:
                gid = str(groups[0].id)
        from app.crud import send_message_crud
        msg = send_message_crud(db, teacher_id, content, receiver_id, gid)
        target = student_name or group_name or "全部"
        return f"消息已发送给 {target}。"
    except Exception as e:
        return f"发送消息失败：{str(e)}"
    finally:
        db.close()


@lc_tool
def get_task_progress_tool(
    task_title: str = "",
    group_name: str = "",
    config: RunnableConfig = None,
) -> str:
    """查看任务完成进度（接收"分析学习情况"请求时调用）。参数：task_title(任务标题关键词), group_name(分组名)。"""
    from app.models import TeacherGroupModel, TaskModel, TaskProgressModel, UserModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        q = db.query(TaskModel).filter(TaskModel.teacher_id == teacher_id)
        if task_title:
            q = q.filter(TaskModel.title.contains(task_title))
        if group_name:
            group = db.query(TeacherGroupModel).filter(
                TeacherGroupModel.teacher_id == teacher_id,
                TeacherGroupModel.name == group_name,
            ).first()
            if group:
                q = q.filter(TaskModel.target_group_id == str(group.id))
        tasks = q.order_by(TaskModel.created_at.desc()).limit(10).all()
        if not tasks:
            return "暂无任务记录。"
        lines = []
        for t in tasks:
            completed = db.query(func.count(TaskProgressModel.id)).filter(
                TaskProgressModel.task_id == t.id, TaskProgressModel.is_completed.is_(True)
            ).scalar() or 0
            total = db.query(func.count(TaskProgressModel.id)).filter(
                TaskProgressModel.task_id == t.id
            ).scalar() or 0
            deadline = f"，截止{t.deadline.strftime('%Y-%m-%d')}" if t.deadline else ""
            lines.append(f"- {t.title}：{completed}/{total}人完成{deadline}")
        return "\n".join(lines)
    except Exception as e:
        return f"查询任务进度失败：{str(e)}"
    finally:
        db.close()


# ══════════════════════════════════════════════
# Teacher Agent — Group Management Tools
# ══════════════════════════════════════════════
@lc_tool
def get_group_stats_tool(
    group_name: str = "",
    config: RunnableConfig = None,
) -> str:
    """获取分组的详细统计信息（成员数/正确率/口语均分/活跃度）。参数 group_name 为分组名，留空则返回所有分组的对比。"""
    from app.models import TeacherGroupModel, UserModel, PracticeRecordModel, SpeakingRecordModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        if group_name:
            group = db.query(TeacherGroupModel).filter(
                TeacherGroupModel.teacher_id == teacher_id,
                TeacherGroupModel.name == group_name,
            ).first()
            if not group:
                return f"未找到分组「{group_name}」"
            from app.crud import get_group_detail
            detail = get_group_detail(db, str(group.id), teacher_id)
            if not detail:
                return "加载分组详情失败"
            stats = detail.get("stats", {})
            return (
                f"分组「{group_name}」：{stats.get('total_students',0)}人，"
                f"平均正确率{stats.get('avg_accuracy',0)}%，"
                f"口语均分{stats.get('avg_speaking_score',0)}，"
                f"近14天活跃{stats.get('active_14d',0)}人。"
            )
        else:
            from app.crud import get_groups_comparison
            groups = get_groups_comparison(db, teacher_id)
            if not groups:
                return "暂无分组数据"
            lines = ["所有分组对比："]
            for g in groups:
                lines.append(
                    f"- {g['group_name']}：{g['student_count']}人，"
                    f"正确率{g['avg_accuracy']}%，活跃率{g['active_rate']}%"
                )
            return "\n".join(lines)
    finally:
        db.close()


@lc_tool
def create_group_tool(
    name: str,
    description: str = "",
    config: RunnableConfig = None,
) -> str:
    """创建新的学生分组。参数 name 为分组名称（必填），description 为分组说明（可选）。"""
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        from app.models import TeacherGroupModel
        existing = db.query(TeacherGroupModel).filter(
            TeacherGroupModel.teacher_id == teacher_id,
            TeacherGroupModel.name == name,
        ).first()
        if existing:
            return f"分组「{name}」已存在，请使用其他名称。"
        group = TeacherGroupModel(teacher_id=teacher_id, name=name, description=description or None)
        db.add(group)
        db.commit()
        return f"分组「{name}」创建成功。"
    except Exception as e:
        return f"创建分组失败：{str(e)}"
    finally:
        db.close()


@lc_tool
def update_student_level_tool(
    student_name: str,
    new_level: str,
    config: RunnableConfig = None,
) -> str:
    """更新学生等级（A=高级/B=中级/C=初级）。当分析发现学生学习情况显著改善时调用。
    参数 student_name 为学生用户名，new_level 为目标等级(A/B/C)。"""
    from app.models import UserModel
    if new_level not in ("A", "B", "C"):
        return f"无效的等级: {new_level}，等级必须是 A、B 或 C"
    db = SessionLocal()
    try:
        student = db.query(UserModel).filter(
            UserModel.username == student_name, UserModel.role == "student"
        ).first()
        if not student:
            return f"未找到学生「{student_name}」"
        old_level = student.level or "未定级"
        student.level = new_level
        db.commit()
        return f"已将 {student_name} 的等级从 {old_level} 更新为 {new_level}。"
    except Exception as e:
        return f"更新等级失败：{str(e)}"
    finally:
        db.close()


@lc_tool
def assign_student_to_group_tool(
    student_name: str,
    group_name: str,
    config: RunnableConfig = None,
) -> str:
    """将指定学生分配到指定分组。参数 student_name 为学生用户名，group_name 为目标分组名。"""
    from app.models import TeacherGroupModel, UserModel
    teacher_id = config.get("configurable", {}).get("user_id", "") if config else ""
    db = SessionLocal()
    try:
        student = db.query(UserModel).filter(
            UserModel.username == student_name, UserModel.role == "student"
        ).first()
        if not student:
            return f"未找到学生「{student_name}」"
        group = db.query(TeacherGroupModel).filter(
            TeacherGroupModel.teacher_id == teacher_id,
            TeacherGroupModel.name == group_name,
        ).first()
        if not group:
            return f"未找到分组「{group_name}」"
        student.group_id = str(group.id)
        db.commit()
        return f"已将 {student_name} 分配到分组「{group_name}」"
    except Exception as e:
        return f"分配失败：{str(e)}"
    finally:
        db.close()


# ══════════════════════════════════════════════
# Agent Builders
# ══════════════════════════════════════════════
from langchain.agents import create_agent

STUDENT_AGENT_SYSTEM_PROMPT = """你是 RealEnglish 学生学习助手，帮助英语学习者高效使用本平台。

你的能力：
- 获取当前日期和时间（调用 get_current_time）
- 查看学生的学习统计和进度（A=高级/B=中级/C=初级，调用 get_my_stats）
- 分析错题和薄弱环节（调用 get_my_mistakes）
- 查看近14天学习活跃度（调用 get_my_activity）
- 推荐适合的影视片段（调用 search_clips）
- 获取影视片段详情（调用 get_clip_info）
- 查看学习任务和完成进度（调用 get_my_tasks，在制定学习计划时调用）
- 生成个人学情报告（调用 generate_my_report，英雄之旅风格）
- 查看单词本统计（调用 get_my_vocabulary_stats，了解词汇量和掌握情况）
- 查看未掌握的薄弱单词（调用 get_my_weak_words，获取待复习清单）
- 分析口语进步趋势（调用 get_speaking_trend，查看近30天评分变化）
- 生成个性化复习计划（调用 get_smart_review_plan，综合单词/错题/任务给出今日建议）

使用规则：
1. 当用户询问学习情况、统计数据、进度时，主动调用工具获取真实数据
2. 当用户需要推荐片段时，先了解用户偏好再调用 search_clips。search_clips 返回 JSON 数组，请将其转换为 Markdown 表格呈现给用户，表格列必须包含：
   - **推荐指数**：根据 match_score 转换为 ⭐ 数（1分=1星，最多5星）
   - **片段名称**：使用 Markdown 链接格式 `[标题](clip://{id})` ，让用户可以点击跳转
   - **分类**
   - **难度**
   - **简介**
3. 调用 search_clips 时使用宽泛关键词（如"动画""家庭""职场"），不要用精确标题
4. 用中文回复，语气温暖、鼓励
5. 基于工具返回的实际数据给出具体建议，不要编造数据
6. 如果工具返回空数据，鼓励用户开始学习
7. 当用户说"制定学习计划"时，主动调用 get_my_tasks 了解现有任务，再结合 get_my_stats 和 get_my_mistakes 给出针对性建议"""

TEACHER_AGENT_SYSTEM_PROMPT = """你是 RealEnglish 教师管理助手，帮助教师高效管理学生和教学。

你的能力：
- 获取当前日期和时间（调用 get_current_time）
- 列出学生名单（调用 list_my_students，支持关键词搜索）
- 查看学生等级分布（A=高级/B=中级/C=初级，调用 get_student_level_distribution）
- 查看学生详细学情（调用 get_student_learning_detail，需提供学生用户名）
- 生成单个学生学习报告（调用 generate_learning_report，需提供学生用户名）
- **生成分组/班级整体学情报告（调用 generate_group_report，需提供分组名称）**
- 列出分组信息（调用 list_my_groups）
- 查看分组内学生（调用 get_group_students_detail，需提供分组名）
- 创建学习任务（调用 create_task，根据学情科学设计练习/口语/对话/片段目标）
- 发布公告（调用 send_announcement）
- 发送消息（调用 send_group_message，支持单发和群发）
- 查看任务进度（调用 get_task_progress，接收"分析学习情况"请求时调用）
- 查看分组统计（调用 get_group_stats_tool，支持全部对比或指定分组）
- 分配学生到分组（调用 assign_student_to_group_tool，需学生用户名和分组名）
- 创建学生分组（调用 create_group_tool，需分组名称）
- 更新学生等级（调用 update_student_level_tool，当学情显著改善时可升级：C→B, B→A）
- 横向对比学生（调用 compare_students，需逗号分隔的 2-3 个用户名）
- 查看班级周报（调用 get_weekly_digest，自动汇总本周练习与口语数据）

使用规则：
0. 处理任何需要时间上下文的任务前，先调用 get_current_time 确认当前北京时间
1. 当教师询问学生情况时，主动调用工具获取真实数据
2. 当教师提到具体学生名字时，调用 get_student_learning_detail 获取详情
3. **当教师要求生成某个分组/班级的整体报告时，必须调用 generate_group_report，不要对每个学生单独调用 generate_learning_report 再拼接**
4. 当教师要求生成单个学生的报告时，调用 generate_learning_report
5. 用中文回复，语气专业、简洁
6. 基于工具返回的实际数据给出分析和建议，不要编造数据
7. 可以在一次回复中调用多个工具来获取全面信息
8. 当教师问"这周怎么样"或"本周汇总"时，调用 get_weekly_digest 生成周报
9. 当教师想对比学生时，直接调用 compare_students，不要逐个查详情"""


from langgraph.checkpoint.memory import MemorySaver

_checkpointer = MemorySaver()

_student_agent = None
_teacher_agent = None


# 会话消息持久化：写入项目 SQLite 数据库（thread_messages 表由 models.py 定义）
def save_message_to_db(user_id: str, thread_id: str, role: str, content: str):
    """将一条对话消息持久化到数据库。"""
    from app.db import SessionLocal
    from app.models import ThreadMessageModel
    db = SessionLocal()
    try:
        msg = ThreadMessageModel(user_id=user_id, thread_id=thread_id, role=role, content=content)
        db.add(msg)
        db.commit()
    except Exception as e:
        logger.warning(f"保存消息失败: {e}")
    finally:
        db.close()


async def get_thread_messages(user_id: str, thread_id: str) -> list[dict]:
    """从 thread_messages 表读取对话历史。"""
    from app.db import SessionLocal
    from app.models import ThreadMessageModel
    db = SessionLocal()
    try:
        rows = db.query(ThreadMessageModel).filter(
            ThreadMessageModel.thread_id == thread_id
        ).order_by(ThreadMessageModel.created_at.asc()).all()
        return [{"role": r.role, "content": r.content} for r in rows]
    finally:
        db.close()


def get_student_agent():
    """获取学生助手 Agent（单例）。checkpointer 由 init_checkpointer() 初始化。"""
    global _student_agent
    if _student_agent is None:
        llm = get_llm(temperature=0.7)
        _student_agent = create_agent(
            model=llm,
            tools=[get_current_time, get_my_stats, get_my_mistakes, get_my_activity, search_clips, get_clip_info, get_my_tasks, generate_my_report, get_my_vocabulary_stats, get_my_weak_words, get_speaking_trend, get_smart_review_plan],
            system_prompt=STUDENT_AGENT_SYSTEM_PROMPT,
            checkpointer=_checkpointer,
        )
    return _student_agent


def get_teacher_agent():
    """获取教师助手 Agent（单例）。checkpointer 由 init_checkpointer() 初始化。"""
    global _teacher_agent
    if _teacher_agent is None:
        llm = get_llm(temperature=0.6)
        _teacher_agent = create_agent(
            model=llm,
            tools=[
                get_current_time,
                list_my_students,
                get_student_level_distribution,
                get_student_learning_detail,
                generate_learning_report,
                generate_group_report,
                list_my_groups,
                get_group_students_detail,
                create_task_tool,
                send_announcement_tool,
                send_group_message_tool,
                get_task_progress_tool,
                get_group_stats_tool,
                assign_student_to_group_tool,
                create_group_tool,
                update_student_level_tool,
                compare_students,
                get_weekly_digest,
            ],
            system_prompt=TEACHER_AGENT_SYSTEM_PROMPT,
            checkpointer=_checkpointer,
        )
    return _teacher_agent


# ══════════════════════════════════════════════
# 手动 ReAct 流式循环（替代 astream_events）
# ══════════════════════════════════════════════

async def stream_agent_response(
    llm: ChatOpenAI,
    tools: list,
    system_prompt: str,
    user_message: str,
    history: list[dict],
    user_id: str,
):
    """手动实现 ReAct 循环，直接流式输出 LLM token 并处理工具调用。

    替代 agent.astream_events() 方案，因为 create_agent 内部使用
    trace=False 创建 RunnableCallable，导致 Python 3.10 上无法将
    回调上下文传递给模型，on_chat_model_stream 事件永远不会触发。

    Yields:
        dict: {"type": "content", "content": "..."}
        dict: {"type": "tool_start", "tool": "..."}
        dict: {"type": "tool_end", "tool": "...", "output": "..."}
        dict: {"type": "done"}
    """
    from langchain_core.messages import AIMessage, ToolMessage

    tool_config: RunnableConfig = {"configurable": {"user_id": user_id}}
    tool_map: dict[str, any] = {}
    for t in tools:
        name = getattr(t, "name", None)
        if name:
            tool_map[name] = t

    messages: list = [{"role": "system", "content": system_prompt}]
    for h in history[-20:]:
        role = h.get("role", "")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    llm_with_tools = llm.bind_tools(tools)
    full_reply: list[str] = []
    max_iterations = 10

    for _iteration in range(max_iterations):
        accumulated: AIMessage | None = None
        chunk_count = 0

        async for chunk in llm_with_tools.astream(messages):
            chunk_count += 1
            if chunk.content:
                full_reply.append(chunk.content)
                yield {"type": "content", "content": chunk.content}
            if accumulated is None:
                accumulated = chunk
            else:
                accumulated += chunk

        if accumulated is None or not accumulated.tool_calls:
            break

        # 有工具调用 — 将 AI 消息加入历史
        tool_call_msgs = []
        for tc in accumulated.tool_calls:
            name = tc.get("name", "")
            args = tc.get("args", {})
            tc_id = tc.get("id", "")
            yield {"type": "tool_start", "tool": name}
            tool_fn = tool_map.get(name)
            if tool_fn:
                try:
                    result = tool_fn.invoke(args, tool_config)
                    output = str(result)
                except Exception as exc:
                    output = f"工具执行失败: {exc}"
            else:
                output = f"未找到工具: {name}"
            yield {"type": "tool_end", "tool": name, "output": output[:200]}
            tool_call_msgs.append(ToolMessage(content=output, tool_call_id=tc_id))
        messages.append(accumulated)
        messages.extend(tool_call_msgs)

    yield {"type": "done"}
