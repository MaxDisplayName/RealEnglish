# RealEnglish 多智能体（Multi-Agent）实现指南

> 本文档为 AI 编码助手提供使用 LangChain / LangGraph 在 RealEnglish 项目中构建多智能体系统的详细指导。适用场景：AI 出题、口语教练反馈、教师端学情报告、兴趣引导推荐。

## 1.为什么需要多智能体？

单一的大模型调用无法自主决策、无法使用外部工具、也无法记忆多轮对话。通过构建 Agent，我们可以：

让系统 自动选择合适的工具（如查询数据库、调用讯飞 API、读取 Excel）。

实现 长期记忆：记住学生上一次的练习偏好、错题高频点。

完成 复杂任务编排：例如从“选择影视片段” → “生成题目” → “评测口语” → “生成报告” 的全流程自动化。

本项目将使用 LangGraph（LangChain 的子项目）构建一个有状态的多智能体工作流，因为它天然支持循环、条件分支和状态持久化。

## 2.整体架构（多智能体协作图）

```graph TD
    U[用户请求] --> Router{路由}
    Router --> |口语练习| SpeakingAgent[口语教练Agent]
    Router --> |生成新题| QuizAgent[出题Agent]
    Router --> |教师端| ReportAgent[学情报告Agent]
    Router --> |推荐片段| InterestAgent[兴趣引导Agent]

    SpeakingAgent --> Tools1[(讯飞评测 + DeepSeek)]
    QuizAgent --> Tools2[(DeepSeek + 数据库)]
    ReportAgent --> Tools3[(数据库 + 统计分析)]
    InterestAgent --> Tools4[(向量检索 + 用户画像)]

    SpeakingAgent --> Response[返回鼓励+评分]
    QuizAgent --> Response[返回新题目]
    ReportAgent --> Response[返回叙事报告]
    InterestAgent --> Response[返回推荐片段]
```

## 3.环境准备

在 requirements.txt 中添加：

```text
langchain>=0.1.0
langgraph>=0.0.20
langchain-openai  # 兼容 DeepSeek
```

安装：

```bash
pip install langchain langgraph langchain-openai
```

## 4.通用配置（LangChain 与 DeepSeek 集成）

core/llm_factory.py – 统一的大模型工厂（兼容 OpenAI API）：

```py
from langchain_openai import ChatOpenAI
from app.config import settings

def get_llm(temperature: float = 0.3):
    return ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=settings.DEEPSEEK_API_KEY,
        openai_api_base="https://api.deepseek.com/v1",
        temperature=temperature,
        timeout=30,
        max_retries=2
    )
```

## 5.定义代理工具（Tools）

每个 Agent 需要一组工具。以下示例展示最常用的三个工具。

### 5.1 数据库查询工具（供报告 Agent、推荐 Agent 使用）

tools/db_tools.py：

```py
from langchain.tools import tool
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud.user import get_user_stats
from app.crud.practice_record import get_recent_mistakes

@tool
def get_user_learning_stats(user_id: str) -> str:
    """获取指定用户的学习统计数据（练习次数、正确率趋势）。"""
    db: Session = next(get_db())
    stats = get_user_stats(db, user_id)
    return f"近7天练习{stats['practice_count']}次，正确率从{stats['prev_accuracy']}%提升到{stats['curr_accuracy']}%。"

@tool
def get_top_mistakes(user_id: str, limit: int = 3) -> str:
    """获取用户最常见的错题类型。"""
    db = next(get_db())
    mistakes = get_recent_mistakes(db, user_id, limit)
    if not mistakes:
        return "暂无错题记录"
    return "、".join([f"{m['question_type']}（{m['wrong_times']}次）" for m in mistakes])
```

### 5.2 DeepSeek 出题工具（供出题 Agent 使用）

tools/quiz_tools.py：

```py
from langchain.tools import tool
from app.core.question_generator import generate_questions_via_api
import json

@tool
def generate_questions_from_dialogue(dialogue_text: str, difficulty: str) -> str:
    """
    根据影视对话生成托业风格听力题。
    输入：对话文本、难度级别（A/B/C）。
    输出：JSON 格式的题目列表。
    """
    try:
        questions = generate_questions_via_api(dialogue_text, difficulty)
        return json.dumps(questions, ensure_ascii=False)
    except Exception as e:
        return f"出题失败：{str(e)}"
```

### 5.3 讯飞语音评测工具（供口语 Agent 使用）

tools/speech_tools.py：

```py
from langchain.tools import tool
from app.core.speech_eval import evaluate_audio_bytes

@tool
def evaluate_pronunciation(audio_base64: str, reference_text: str) -> str:
    """调用讯飞语音评测返回评分（总分、准确度、流畅度）。"""
    result = evaluate_audio_bytes(audio_base64, reference_text)
    return f"总分{result['total_score']}，准确度{result['accuracy']}，流畅度{result['fluency']}"
```

## 6.定义各 Agent（使用 LangGraph）

LangGraph 允许我们定义状态图，每个节点是一个 Agent 或工具调用，边表示流转。

### 6.1 出题 Agent（一次性任务）

agents/quiz_agent.py：

```py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from app.core.llm_factory import get_llm
from tools.quiz_tools import generate_questions_from_dialogue

class QuizState(TypedDict):
    clip_id: str
    dialogue_text: str
    difficulty: str
    generated_questions: List[dict]
    error: str

def call_llm_to_format(state: QuizState):
    """使用 LLM 将原始题目整理成标准 JSON（可选）"""
    llm = get_llm(temperature=0.4)
    prompt = f"将以下对话生成的题目列表整理为 [{ 'question': '...', 'options': [...], 'answer': 0, 'explanation': '...' }] 格式。原始数据：{state['generated_questions']}"
    response = llm.invoke(prompt)
    state['generated_questions'] = json.loads(response.content)
    return state

def generate(state: QuizState):
    tools_result = generate_questions_from_dialogue(state['dialogue_text'], state['difficulty'])
    if tools_result.startswith("出题失败"):
        state['error'] = tools_result
    else:
        state['generated_questions'] = json.loads(tools_result)
    return state

# 构建图
quiz_graph = StateGraph(QuizState)
quiz_graph.add_node("generate", generate)
quiz_graph.add_node("format", call_llm_to_format)
quiz_graph.set_entry_point("generate")
quiz_graph.add_edge("generate", "format")
quiz_graph.add_edge("format", END)
quiz_app = quiz_graph.compile()
```

### 6.2 口语教练 Agent（带记忆的对话式）

agents/speaking_agent.py：

```py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver
from app.core.llm_factory import get_llm
from tools.speech_tools import evaluate_pronunciation

class SpeakingState(TypedDict):
    user_id: str
    clip_id: str
    original_text: str       # 参考台词
    audio_base64: str
    score_result: dict
    coach_feedback: str
    chat_history: list       # 多轮对话记忆

def evaluate(state: SpeakingState):
    result_str = evaluate_pronunciation(state['audio_base64'], state['original_text'])
    # 解析结果字符串
    state['score_result'] = {"total_score": 85, "accuracy": 80, "fluency": 90}  # 示例
    return state

def generate_feedback(state: SpeakingState):
    llm = get_llm(temperature=0.7)
    prompt = f"""
    你是一位温暖的口语教练。用户刚刚完成了跟读练习，原台词是：{state['original_text']}
    讯飞评测得分为：总分{state['score_result']['total_score']}，准确度{state['score_result']['accuracy']}，流畅度{state['score_result']['fluency']}。
    请写一段鼓励性的中文反馈（100字以内），先肯定努力，再给1个具体改进建议，最后以一个问题结尾。
    """
    response = llm.invoke(prompt)
    state['coach_feedback'] = response.content
    return state

speaking_graph = StateGraph(SpeakingState)
speaking_graph.add_node("evaluate", evaluate)
speaking_graph.add_node("feedback", generate_feedback)
speaking_graph.set_entry_point("evaluate")
speaking_graph.add_edge("evaluate", "feedback")
speaking_graph.add_edge("feedback", END)

# 启用内存记忆（支持多轮对话）
speaking_app = speaking_graph.compile(checkpointer=MemorySaver())
```

### 6.3 学情报告 Agent（教师端，自动分析 + 叙事生成）

agents/report_agent.py：

```py
from langgraph.graph import StateGraph, END
from app.core.llm_factory import get_llm
from tools.db_tools import get_user_learning_stats, get_top_mistakes

class ReportState(TypedDict):
    user_id: str
    stats: str
    mistakes: str
    narrative_report: str

def fetch_data(state: ReportState):
    state['stats'] = get_user_learning_stats(state['user_id'])
    state['mistakes'] = get_top_mistakes(state['user_id'])
    return state

def write_narrative(state: ReportState):
    llm = get_llm(temperature=0.5)
    prompt = f"""
    你是一位善于激励的学习分析师。请根据以下数据，为用户写一段“英雄之旅”风格的学习报告（200字左右）：
    - 学习统计：{state['stats']}
    - 常见错题：{state['mistakes']}
    报告中要包含：进步肯定、挑战识别、下一步行动建议。
    """
    response = llm.invoke(prompt)
    state['narrative_report'] = response.content
    return state

report_graph = StateGraph(ReportState)
report_graph.add_node("fetch", fetch_data)
report_graph.add_node("write", write_narrative)
report_graph.set_entry_point("fetch")
report_graph.add_edge("fetch", "write")
report_graph.add_edge("write", END)
report_app = report_graph.compile()
```

### 6.4 兴趣引导 Agent（基于向量检索推荐片段）

agents/interest_agent.py：

```py
from langgraph.graph import StateGraph, END
from langchain.embeddings import OpenAIEmbeddings  # 使用 DeepSeek 兼容的 embeddings
from langchain.vectorstores import FAISS
from app.core.llm_factory import get_llm
from app.crud.clip import get_all_clips

class InterestState(TypedDict):
    user_preference: str   # 用户最近偏好的话题，如 "office meeting"
    recommended_clips: list

def retrieve_by_similarity(state: InterestState):
    # 所有片段简介向量化（可缓存）
    clips = get_all_clips()  # 返回列表 [{id, title, summary, dialogue_text}]
    # 使用 FAISS 构建索引（首次构建，后续增量更新）
    embeddings = OpenAIEmbeddings(openai_api_key=settings.DEEPSEEK_API_KEY)
    texts = [c['summary'] + c['dialogue_text'][:200] for c in clips]
    vectorstore = FAISS.from_texts(texts, embeddings)
    docs = vectorstore.similarity_search(state['user_preference'], k=3)
    state['recommended_clips'] = [doc.metadata['id'] for doc in docs]
    return state

interest_graph = StateGraph(InterestState)
interest_graph.add_node("retrieve", retrieve_by_similarity)
interest_graph.set_entry_point("retrieve")
interest_graph.add_edge("retrieve", END)
interest_app = interest_graph.compile()
```

## 7.在 FastAPI 中集成 Agent

api/v1/agents.py – 提供 HTTP 端点调用各 Agent：

```py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.agents.speaking_agent import speaking_app
from app.agents.quiz_agent import quiz_app
from app.agents.report_agent import report_app
from app.agents.interest_agent import interest_app
import uuid

router = APIRouter()

class SpeakingRequest(BaseModel):
    clip_id: str
    original_text: str
    audio_base64: str

class QuizRequest(BaseModel):
    clip_id: str
    dialogue_text: str
    difficulty: str

class ReportRequest(BaseModel):
    user_id: str

class InterestRequest(BaseModel):
    user_preference: str

@router.post("/speaking/coach")
async def speaking_coach(req: SpeakingRequest):
    state = {
        "user_id": "device123",
        "clip_id": req.clip_id,
        "original_text": req.original_text,
        "audio_base64": req.audio_base64,
        "score_result": {},
        "coach_feedback": "",
        "chat_history": []
    }
    final_state = await speaking_app.ainvoke(state)
    return {"feedback": final_state["coach_feedback"], "score": final_state["score_result"]}

@router.post("/quiz/generate")
async def generate_quiz(req: QuizRequest):
    state = {
        "clip_id": req.clip_id,
        "dialogue_text": req.dialogue_text,
        "difficulty": req.difficulty,
        "generated_questions": [],
        "error": ""
    }
    final_state = await quiz_app.ainvoke(state)
    if final_state.get("error"):
        raise HTTPException(status_code=500, detail=final_state["error"])
    return {"questions": final_state["generated_questions"]}

@router.get("/report/{user_id}")
async def get_learning_report(user_id: str):
    state = {"user_id": user_id, "stats": "", "mistakes": "", "narrative_report": ""}
    final_state = await report_app.ainvoke(state)
    return {"report": final_state["narrative_report"]}

@router.post("/interest/recommend")
async def recommend_clips(req: InterestRequest):
    state = {"user_preference": req.user_preference, "recommended_clips": []}
    final_state = await interest_app.ainvoke(state)
    return {"clip_ids": final_state["recommended_clips"]}
```

## 8. 状态持久化与记忆

对于口语教练这种支持多轮对话的 Agent，我们使用 MemorySaver 将会话状态存储在 Redis 中：

```py
from langgraph.checkpoint import RedisSaver

checkpointer = RedisSaver(redis_url=settings.REDIS_URL)
speaking_app = speaking_graph.compile(checkpointer=checkpointer)

# 调用时传入 thread_id
config = {"configurable": {"thread_id": f"user_{user_id}_clip_{clip_id}"}}
final_state = await speaking_app.ainvoke(state, config=config)
```

## 9.部署与监控

我们使用LangGraph的先进监控工具，LangSmith进行在线监控。

安装依赖：

```bash
pip install -U langchain langchain_openai langgraph
```

配置环境：

```ini
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2_xxx
LANGSMITH_PROJECT="RealEnglish"

OPENAI_API_KEY=sk-xxxxx
```

完成。随后每当用户调用智能体，可以在LangSmith网站上看到agent生成和调用工具的情况！

## 10.开发与测试建议

单元测试：对每个工具函数（Tool）编写独立测试。

集成测试：使用测试用户 ID 调用 quiz_app 并断言输出 JSON 结构。

## 11.注意事项

超时控制：LangGraph 节点内调用外部 API 时必须设置超时（asyncio.wait_for）。

错误传播：节点中捕获异常，将错误信息存入 state 并跳转到错误处理节点。

Token 消耗：口语教练的 prompt 中包含评测分数，注意避免重复发送长对话历史。

开发调试：使用 graph.get_graph().print_ascii() 打印图结构。

通过本文档，AI 编码助手可以清晰地实现本项目所有多智能体场景，提升代码的可维护性和智能性。

文档版本: v1.0
最后更新: 2026-05-03
维护者: RealEnglish 开发团队
