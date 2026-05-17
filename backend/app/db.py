import asyncio
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.time_utils import beijing_now

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Seed / Init DB ──
FALLBACK_QUESTIONS = [
    {"question": "What is the main topic of the conversation?", "options": ["Travel plans", "Family matters", "Work schedules"], "answer": 1, "explanation": "对话围绕家庭成员间的日常交流展开。"},
    {"question": "Where does this conversation most likely take place?", "options": ["At a restaurant", "At home", "In an office"], "answer": 1, "explanation": "从对话的语气和内容可以推断发生在家庭场景。"},
    {"question": "How does the speaker feel about the situation?", "options": ["Excited", "Concerned", "Indifferent"], "answer": 1, "explanation": "说话者的语气透露出对当前情况的关切。"},
]


def _get_csv_path() -> Path:
    """查找 video_clips.csv，优先 backend/res/ 目录"""
    candidates = [
        Path("res/video_clips.csv"),
        Path("../res/video_clips.csv"),
        Path("../../res/video_clips.csv"),
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("找不到 res/video_clips.csv，已搜索: " + ", ".join(str(p) for p in candidates))


def sync_clips_from_csv(db: Session) -> list:
    """从 CSV 同步片段到数据库（upsert：存在则更新，不存在则新增）。返回新增+更新的片段列表。"""
    from app.models import VideoClipModel
    import json as _json
    from datetime import datetime

    csv_path = _get_csv_path()
    logger.info(f"从 CSV 同步片段: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    updated = 0
    inserted = 0
    all_clips = []

    for _, row in df.iterrows():
        bvid = str(row["BV号"]).strip()
        page = int(row["分P"])
        start_sec = int(row["起始时间(秒)"])

        # 解析角色性别 JSON
        cg_raw = row.get("角色性别")
        character_genders = None
        if pd.notna(cg_raw) and str(cg_raw).strip():
            try:
                cg_str = str(cg_raw)
                character_genders = _json.loads(cg_str) if cg_str.startswith("{") else {}
            except (_json.JSONDecodeError, TypeError):
                logger.warning(f"角色性别格式错误: {cg_raw}")

        # 查找已存在的片段（按 bvid + page + start_sec 组合键）
        existing = db.query(VideoClipModel).filter(
            VideoClipModel.bvid == bvid,
            VideoClipModel.page == page,
            VideoClipModel.start_sec == start_sec,
        ).first()

        if existing:
            # 更新已存在的片段
            existing.end_sec = int(row.get("结束时间(秒)", existing.end_sec))
            existing.iframe_url = str(row.get("iframe链接", "")) or None
            existing.title = str(row.get("剧集名称", "")) or None
            existing.category = str(row.get("对话类别", "")) or None
            existing.difficulty = str(row.get("难度", existing.difficulty))
            existing.dialogue_text = str(row.get("对话文本", "")) or None
            existing.summary = str(row.get("片段剧情描述", "")) or None
            existing.subtitle_source = str(row.get("字幕来源", "")) or None
            existing.character_genders = character_genders
            existing.imported_at = beijing_now()
            all_clips.append(existing)
            updated += 1
        else:
            clip = VideoClipModel(
                bvid=bvid, page=page,
                start_sec=start_sec, end_sec=int(row.get("结束时间(秒)", 0)),
                iframe_url=str(row.get("iframe链接", "")), title=str(row.get("剧集名称", "")),
                category=str(row.get("对话类别", "")), difficulty=str(row.get("难度", "")),
                dialogue_text=str(row.get("对话文本", "")), summary=str(row.get("片段剧情描述", "")),
                subtitle_source=str(row.get("字幕来源", "")), character_genders=character_genders,
            )
            db.add(clip)
            all_clips.append(clip)
            inserted += 1

    db.commit()
    logger.info(f"CSV 同步完成：新增 {inserted} 条，更新 {updated} 条")
    return all_clips


async def _generate_questions_for_clip(clip, sem: asyncio.Semaphore) -> list[dict]:
    from app.models import VideoClipModel
    from app.agents import quiz_app

    async with sem:
        if not clip.dialogue_text:
            return []
        state = {"clip_id": str(clip.id), "dialogue_text": clip.dialogue_text, "difficulty": clip.difficulty, "generated_questions": [], "error": ""}
        try:
            final_state = await quiz_app.ainvoke(state)
            if final_state.get("error"):
                logger.warning(f"片段 {clip.id} 出题失败: {final_state['error']}")
                return []
            return final_state["generated_questions"][:2]
        except Exception as e:
            logger.warning(f"片段 {clip.id} 出题异常: {e}")
            return []


async def _pre_generate_questions(db: Session, clips: list):
    from app.models import QuestionModel

    sem = asyncio.Semaphore(5)
    tasks = [_generate_questions_for_clip(clip, sem) for clip in clips]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_created = 0
    for clip, questions in zip(clips, results):
        if isinstance(questions, Exception):
            logger.warning(f"片段 {clip.id} AI 出题出错: {questions}")
            continue
        if not questions:
            continue
        for q_data in questions:
            try:
                question = QuestionModel(clip_id=clip.id, type="part2", difficulty=clip.difficulty, content={"question": q_data["question"], "options": q_data["options"], "answer": q_data["answer"], "explanation": q_data.get("explanation", "")})
                db.add(question)
                total_created += 1
            except (KeyError, TypeError) as e:
                logger.warning(f"题目数据格式错误: {e}")
                continue
    db.commit()
    logger.info(f"AI 预生成题目完成，共创建 {total_created} 道")


def _seed_fallback_questions(db: Session, clips: list):
    from app.models import QuestionModel

    difficulties = ["A", "B", "C"]
    counts = {"A": 0, "B": 0, "C": 0}
    targets = {"A": 3, "B": 4, "C": 3}
    for difficulty in difficulties:
        clips_of_level = [c for c in clips if c.difficulty == difficulty]
        while counts[difficulty] < targets[difficulty]:
            for clip in clips_of_level:
                if counts[difficulty] >= targets[difficulty]:
                    break
                for fq in FALLBACK_QUESTIONS:
                    if counts[difficulty] >= targets[difficulty]:
                        break
                    question = QuestionModel(clip_id=clip.id, type="part2", difficulty=difficulty, content=fq)
                    db.add(question)
                    counts[difficulty] += 1
        if counts[difficulty] < targets[difficulty] and clips_of_level:
            remaining = targets[difficulty] - counts[difficulty]
            for i in range(min(remaining, len(FALLBACK_QUESTIONS))):
                question = QuestionModel(clip_id=clips_of_level[0].id, type="part2", difficulty=difficulty, content=FALLBACK_QUESTIONS[i])
                db.add(question)
                counts[difficulty] += 1
    db.commit()
    logger.info(f"Fallback 题目已加载: A={counts['A']}, B={counts['B']}, C={counts['C']}")


async def seed_database():
    """启动时从 CSV 同步片段到数据库，题目不足时自动预生成。"""
    from app.crud import get_clip_count, get_question_count

    db = SessionLocal()
    try:
        clips = sync_clips_from_csv(db)
        if not clips:
            logger.warning("CSV 无任何片段，跳过题目生成")
            return

        question_count = get_question_count(db)
        logger.info(f"当前题库共 {question_count} 道题目，对应 {len(clips)} 个片段")

        # 如果题目数量少于片段数 × 2，为缺少题目的片段预生成
        if question_count < len(clips) * 2:
            # 只给尚无题目的片段生成
            from app.models import QuestionModel
            clips_without_questions = []
            for c in clips:
                q_count = db.query(QuestionModel).filter(QuestionModel.clip_id == c.id).count()
                if q_count == 0:
                    clips_without_questions.append(c)
            if clips_without_questions:
                logger.info(f"为 {len(clips_without_questions)} 个新片段预生成题目...")
                await _pre_generate_questions(db, clips_without_questions)

        question_count = get_question_count(db)
        if question_count < 12:
            logger.warning(f"题目仅 {question_count} 道，加载 fallback 题目")
            _seed_fallback_questions(db, clips)
    finally:
        db.close()
