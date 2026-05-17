import asyncio
import json
import logging
from app.schemas import MarkReadRequest
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.agents import get_student_agent, get_teacher_agent, get_thread_messages, save_message_to_db, interest_app, quiz_app, report_app, get_llm
from app.agents import stream_agent_response, STUDENT_AGENT_SYSTEM_PROMPT, TEACHER_AGENT_SYSTEM_PROMPT
from app.agents import get_current_time, get_my_stats, get_my_mistakes, get_my_activity, search_clips, get_clip_info, get_my_tasks, generate_my_report, get_my_vocabulary_stats, get_my_weak_words, get_speaking_trend, get_smart_review_plan
from app.agents import list_my_students, get_student_level_distribution, get_student_learning_detail, generate_learning_report, generate_group_report, list_my_groups, get_group_students_detail
from app.agents import create_task_tool, send_announcement_tool, send_group_message_tool, get_task_progress_tool, get_group_stats_tool, assign_student_to_group_tool, create_group_tool, update_student_level_tool, compare_students, get_weekly_digest
from app.ai import call_deepseek, stream_deepseek_messages, DEFAULT_SCORE, evaluate_audio, TTSEngine, synthesize_tts, recognize_speech
from app.bilibili import BILI_HEADERS, resolve_video_url, get_video_info, get_dash_play_url
from app.config import settings
from app.crud import (
    assign_user_group,
    create_question,
    create_record,
    create_teacher_group,
    create_user,
    get_clip_by_id,
    get_clips,
    get_clips_by_ids,
    get_level_distribution,
    get_or_create_user,
    get_placement_questions,
    get_practice_stats,
    get_question_by_id,
    get_questions_by_clip,
    get_student_detail,
    get_students,
    get_teacher_group,
    get_user_by_device_id,
    get_user_by_email,
    get_user_by_id,
    get_user_by_login,
    get_user_by_username,
    get_wrong_note_count,
    get_wrong_notes,
    list_teacher_groups_with_counts,
    merge_device_records,
    update_teacher_group,
    update_user_level,
    add_vocabulary,
    remove_vocabulary,
    list_vocabulary,
    toggle_vocabulary_mastered,
    lookup_word_definition,
)
from app.db import get_db
from app.models import AssistantThreadModel, FreeConversationModel, ConversationMessageModel, PracticeRecordModel, SpeakingRecordModel, TeacherGroupModel, UserModel, UserVocabularyModel, VideoClipModel
from app.schemas import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnswerSubmitRequest,
    BatchAssignRequest,
    GenerateQuestionRequest,
    MessageSend,
    TaskCreate,
    TaskUpdate,
    ThreadRenameRequest,
    LoginRequest,
    MergeDeviceRequest,
    PlacementSubmitRequest,
    RegisterRequest,
    StudentGroupAssignRequest,
    TeacherGroupCreate,
    TeacherGroupUpdate,
    TokenResponse,
    UnifiedResponse,
    UserOut,
    UserRegisterRequest,
    VideoUrlResponse,
)
from app.time_utils import beijing_now
from app.utils import (
    assign_level,
    create_access_token,
    decode_access_token,
    get_current_user,
    get_optional_user,
    hash_password,
    require_bound_student,
    require_student_role,
    require_teacher_role,
    upload_to_oss,
    verify_password,
)

logger = logging.getLogger(__name__)

api_router = APIRouter()

# ══════════════════════════════════════════════
# Auth routes
# ══════════════════════════════════════════════
auth_router = APIRouter()


def _user_to_out(user) -> UserOut:
    return UserOut(
        id=str(user.id), username=user.username, email=user.email,
        avatar=user.avatar, role=user.role, level=user.level,
        teacher_id=str(user.teacher_id) if user.teacher_id else None,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@auth_router.post("/register", response_model=UnifiedResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if get_user_by_username(db, req.username):
        raise HTTPException(status_code=400, detail="用户名已被注册")
    if get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    if req.role not in ("student", "teacher"):
        raise HTTPException(status_code=400, detail="角色只能是 student 或 teacher")

    teacher_id = None
    group_id = None
    if req.invite_code and req.role == "student":
        teacher = db.query(UserModel).filter(
            UserModel.invite_code == req.invite_code.upper().strip(),
            UserModel.role == "teacher",
        ).first()
        if teacher:
            teacher_id = str(teacher.id)
            grp = db.query(TeacherGroupModel).filter(TeacherGroupModel.teacher_id == teacher_id).first()
            if grp:
                group_id = str(grp.id)

    user = create_user(db, username=req.username, email=req.email,
                       hashed_password=hash_password(req.password), role=req.role,
                       teacher_id=teacher_id, group_id=group_id)
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return UnifiedResponse(data=TokenResponse(access_token=token, user=_user_to_out(user)).model_dump())


@auth_router.post("/login", response_model=UnifiedResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_login(db, req.login, role=req.role)
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="用户名/邮箱或密码错误")
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名/邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return UnifiedResponse(data=TokenResponse(access_token=token, user=_user_to_out(user)).model_dump())


@auth_router.get("/me", response_model=UnifiedResponse)
def get_me(
    authorization: str = Header(None),
    x_device_id: str = Header(None, alias="X-Device-Id"),
    db: Session = Depends(get_db),
):
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization[7:])
        if payload and payload.get("sub"):
            user = get_user_by_id(db, payload["sub"])
            if user:
                return UnifiedResponse(data=_user_to_out(user).model_dump())
    if x_device_id:
        user = get_user_by_device_id(db, x_device_id)
        if user:
            return UnifiedResponse(data=_user_to_out(user).model_dump())
    raise HTTPException(status_code=401, detail="未登录或 token 已过期")


@auth_router.post("/merge-device", response_model=UnifiedResponse)
def merge_device(req: MergeDeviceRequest, authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="需要登录")
    payload = decode_access_token(authorization[7:])
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token 无效")
    success = merge_device_records(db, payload["sub"], req.device_id)
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UnifiedResponse(data={"status": "merged"})


# ══════════════════════════════════════════════
# System routes
# ══════════════════════════════════════════════
system_router = APIRouter()


@system_router.post("/users/register", response_model=UnifiedResponse)
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    user = get_or_create_user(db, req.device_id)
    return UnifiedResponse(data={"id": str(user.id), "device_id": user.device_id, "level": user.level, "created_at": user.created_at.isoformat() if user.created_at else None})


@system_router.get("/users/me", response_model=UnifiedResponse)
def get_me_legacy(x_device_id: str = Header(None, alias="X-Device-Id"), db: Session = Depends(get_db)):
    if not x_device_id:
        raise HTTPException(status_code=400, detail="缺少 X-Device-Id 请求头")
    user = get_user_by_device_id(db, x_device_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UnifiedResponse(data={"id": str(user.id), "device_id": user.device_id, "level": user.level, "created_at": user.created_at.isoformat() if user.created_at else None})


@system_router.post("/logs/frontend", response_model=UnifiedResponse)
async def collect_frontend_log(data: dict):
    level = data.get("level", "info").upper()
    message = data.get("message", "")
    detail = data.get("detail", "")
    url = data.get("url", "")
    user_agent = data.get("userAgent", "")
    log_line = f"[Frontend] URL={url} UA={user_agent} - {message}"
    if detail:
        log_line += f" | detail={detail}"
    if level == "ERROR":
        logger.error(log_line)
    elif level == "WARNING":
        logger.warning(log_line)
    else:
        logger.info(log_line)
    return UnifiedResponse(data={"status": "ok"})


# ══════════════════════════════════════════════
# Clip routes
# ══════════════════════════════════════════════
clip_router = APIRouter()

_dash_cache: dict[str, tuple[float, dict]] = {}
DASH_CACHE_TTL = 600
CHUNK_SIZE = 1024 * 1024
MAX_CONCURRENT = 6


async def _get_file_size(url: str) -> int:
    async with httpx.AsyncClient(headers=BILI_HEADERS, timeout=30.0) as client:
        resp = await client.get(url, headers={**BILI_HEADERS, "Range": "bytes=0-0"})
        resp.raise_for_status()
        cr = resp.headers.get("content-range", "")
        if cr and "/" in cr:
            return int(cr.split("/")[-1])
        raise RuntimeError(f"Cannot determine file size, content-range={cr!r}")


async def _parallel_chunk_stream(url: str, total_size: int):
    total_chunks = (total_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    results: dict[int, bytes] = {}
    next_idx = 0
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def _download(idx: int) -> tuple[int, bytes]:
        start = idx * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, total_size) - 1
        async with sem:
            async with httpx.AsyncClient(headers=BILI_HEADERS, timeout=30.0) as client:
                resp = await client.get(url, headers={**BILI_HEADERS, "Range": f"bytes={start}-{end}"})
                resp.raise_for_status()
                return idx, await resp.aread()

    pending = {asyncio.create_task(_download(i)) for i in range(min(MAX_CONCURRENT, total_chunks))}
    next_to_submit = MAX_CONCURRENT
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            idx, data = task.result()
            results[idx] = data
        while next_idx in results:
            yield results.pop(next_idx)
            next_idx += 1
            if next_to_submit < total_chunks:
                pending.add(asyncio.create_task(_download(next_to_submit)))
                next_to_submit += 1


async def _proxy_stream(url: str, range_header: str | None = None) -> StreamingResponse:
    bili_headers = {**BILI_HEADERS}
    if range_header:
        bili_headers["Range"] = range_header
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, headers=bili_headers)
        resp.raise_for_status()
        return StreamingResponse(
            resp.aiter_bytes(), status_code=resp.status_code,
            headers={
                "content-type": resp.headers.get("content-type", "application/octet-stream"),
                "content-length": resp.headers.get("content-length", "0"),
                "content-range": resp.headers.get("content-range", ""),
                "accept-ranges": "bytes",
                "access-control-allow-origin": "*",
            },
        )


async def _resolve_cid(bvid: str, page: int) -> int:
    info = await get_video_info(bvid)
    pages = info.get("pages", [])
    if not pages or page < 1 or page > len(pages):
        raise ValueError(f"Invalid page {page} for bvid {bvid}")
    return pages[page - 1]["cid"]


async def _get_dash_data(bvid: str, cid: int, clip_id: str) -> dict:
    now = time.time()
    cached = _dash_cache.get(clip_id)
    if cached and cached[0] > now:
        return cached[1]
    data = await get_dash_play_url(bvid, cid)
    _dash_cache[clip_id] = (now + DASH_CACHE_TTL, data)
    return data


@clip_router.get("", response_model=UnifiedResponse)
def list_clips(
    difficulty: str | None = Query(None), category: str | None = Query(None),
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    clips = get_clips(db, difficulty=difficulty, category=category, skip=skip, limit=limit)
    return UnifiedResponse(data=[{
        "id": str(c.id), "bvid": c.bvid, "page": c.page, "start_sec": c.start_sec,
        "end_sec": c.end_sec, "iframe_url": c.iframe_url, "title": c.title,
        "category": c.category, "difficulty": c.difficulty, "summary": c.summary,
        "subtitle_source": c.subtitle_source, "character_genders": c.character_genders,
        "remark": c.remark,
    } for c in clips])


@clip_router.get("/{clip_id}", response_model=UnifiedResponse)
async def get_clip(clip_id: str, db: Session = Depends(get_db)):
    clip = get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    dialogue_zh = ""
    if clip.dialogue_text:
        from app.ai import translate_dialogue
        dialogue_zh = await translate_dialogue(clip.dialogue_text)
    return UnifiedResponse(data={
        "id": str(clip.id), "bvid": clip.bvid, "page": clip.page, "start_sec": clip.start_sec,
        "end_sec": clip.end_sec, "iframe_url": clip.iframe_url, "title": clip.title,
        "category": clip.category, "difficulty": clip.difficulty, "dialogue_text": clip.dialogue_text,
        "dialogue_zh": dialogue_zh,
        "summary": clip.summary, "subtitle_source": clip.subtitle_source,
        "character_genders": clip.character_genders, "remark": clip.remark,
        "imported_at": clip.imported_at.isoformat() if clip.imported_at else None,
    })


@clip_router.post("/{clip_id}/translate/stream")
async def stream_translate_clip(clip_id: str, db: Session = Depends(get_db)):
    """流式翻译片段对话为中文，SSE JSON 行输出。"""
    clip = get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    if not clip.dialogue_text:
        raise HTTPException(status_code=400, detail="该片段没有对话文本")

    prompt = (
        "将以下英文影视对话翻译为自然的中文口语。保持原文的 [角色名] 格式，"
        "每个角色说的话单独一行。只输出译文，不要任何解释：\n\n" + clip.dialogue_text
    )

    llm = get_llm(temperature=0.3)
    messages = [{"role": "user", "content": prompt}]

    async def event_generator():
        try:
            import asyncio as _asyncio
            async for chunk in llm.astream(messages):
                if chunk.content:
                    yield json.dumps({"type": "content", "content": chunk.content}) + "\n"
                    await _asyncio.sleep(0.01)
            yield json.dumps({"type": "done"}) + "\n"
        except Exception as error:
            logger.error(f"片段翻译流式失败: {error}")
            yield json.dumps({"type": "error", "message": "AI 翻译服务暂时不可用，请稍后重试。"}) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@clip_router.get("/{clip_id}/video-url", response_model=UnifiedResponse)
async def get_clip_video_url(clip_id: str, db: Session = Depends(get_db)):
    clip = get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    try:
        result = await resolve_video_url(clip.bvid, clip.page)
        return UnifiedResponse(data=VideoUrlResponse(url=result["url"], format=result.get("format", "mp4"), quality=result.get("quality", 32), expires_at=result["expires_at"]))
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))


@clip_router.get("/{clip_id}/stream")
async def stream_clip_video(clip_id: str, request: Request, db: Session = Depends(get_db)):
    clip = get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    t0 = time.time()
    try:
        video_info = await resolve_video_url(clip.bvid, clip.page)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    t1 = time.time()
    logger.info("[stream] resolve_video_url took %.2fs for bvid=%s", t1 - t0, clip.bvid)
    video_url = video_info["url"]
    range_header = request.headers.get("range")
    trimmed = range_header.strip() if range_header else ""
    if range_header and not trimmed.startswith("bytes=0-"):
        async with httpx.AsyncClient(timeout=60.0) as client:
            bili_headers = {**BILI_HEADERS, "Range": trimmed}
            resp = await client.get(video_url, headers=bili_headers)
            resp.raise_for_status()
            return StreamingResponse(resp.aiter_bytes(), status_code=206, headers={
                "accept-ranges": "bytes",
                "content-type": resp.headers.get("content-type", "video/mp4"),
                "content-length": resp.headers.get("content-length", "0"),
                "content-range": resp.headers.get("content-range", ""),
                "content-disposition": "inline",
            })
    needs_parallel = trimmed in ("", "bytes=0-")
    if not needs_parallel:
        async with httpx.AsyncClient(timeout=60.0) as client:
            bili_headers = {**BILI_HEADERS}
            if range_header:
                bili_headers["Range"] = trimmed
            resp = await client.get(video_url, headers=bili_headers)
            resp.raise_for_status()
            return StreamingResponse(resp.aiter_bytes(), status_code=206 if range_header else resp.status_code, headers={
                "accept-ranges": "bytes",
                "content-type": resp.headers.get("content-type", "video/mp4"),
                "content-length": resp.headers.get("content-length", "0"),
                "content-disposition": "inline",
            })
    try:
        total_size = await _get_file_size(video_url)
    except Exception as e:
        logger.warning("[stream] _get_file_size failed (%s), falling back to direct GET", e)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(video_url, headers=BILI_HEADERS)
            resp.raise_for_status()
            return StreamingResponse(resp.aiter_bytes(), status_code=resp.status_code, headers={
                "content-type": resp.headers.get("content-type", "video/mp4"),
                "content-length": resp.headers.get("content-length", "0"),
                "content-disposition": "inline",
            })
    status = 206 if range_header else 200
    headers = {"accept-ranges": "bytes", "content-type": "video/mp4", "content-length": str(total_size), "content-disposition": "inline"}
    if range_header:
        headers["content-range"] = f"bytes 0-{total_size - 1}/{total_size}"
    return StreamingResponse(_parallel_chunk_stream(video_url, total_size), status_code=status, headers=headers)


@clip_router.get("/{clip_id}/dash")
async def get_clip_dash(clip_id: str, db: Session = Depends(get_db)):
    clip = get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    try:
        cid = await _resolve_cid(clip.bvid, clip.page)
        dash_data = await _get_dash_data(clip.bvid, cid, clip_id)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    dash = dash_data.get("dash", {})
    video_streams = dash.get("video", [])
    audio_streams = dash.get("audio", [])
    if not video_streams or not audio_streams:
        raise HTTPException(status_code=502, detail="No DASH streams available")
    best_video = None
    for v in video_streams:
        if v.get("codecid") == 7:
            best_video = v
            break
    if not best_video:
        best_video = video_streams[0]
    stream_options = [{"codecid": v["codecid"], "codecs": v["codecs"], "width": v.get("width", 0), "height": v.get("height", 0)} for v in video_streams]
    best_audio = audio_streams[0]
    return UnifiedResponse(data={
        "video": {
            "codecid": best_video["codecid"], "codecs": best_video["codecs"],
            "mime_type": best_video["mime_type"], "width": best_video.get("width", 0),
            "height": best_video.get("height", 0),
            "init_range": best_video["segment_base"]["initialization"],
            "proxy_url": f"/api/v1/clips/{clip_id}/dash/video?codecid={best_video['codecid']}",
        },
        "audio": {
            "codecs": best_audio["codecs"], "mime_type": best_audio["mime_type"],
            "init_range": best_audio["segment_base"]["initialization"],
            "proxy_url": f"/api/v1/clips/{clip_id}/dash/audio",
        },
        "stream_options": stream_options,
        "duration": dash.get("duration", 0),
    })


@clip_router.get("/{clip_id}/dash/video")
async def proxy_dash_video(clip_id: str, request: Request, codecid: int = Query(7), db: Session = Depends(get_db)):
    clip = get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    try:
        cid = await _resolve_cid(clip.bvid, clip.page)
        dash_data = await _get_dash_data(clip.bvid, cid, clip_id)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    for v in dash_data.get("dash", {}).get("video", []):
        if v.get("codecid") == codecid:
            stream_url = v["base_url"]
            break
    else:
        raise HTTPException(status_code=502, detail=f"Video stream (codecid={codecid}) not found")
    return await _proxy_stream(stream_url, request.headers.get("range"))


@clip_router.get("/{clip_id}/dash/audio")
async def proxy_dash_audio(clip_id: str, request: Request, db: Session = Depends(get_db)):
    clip = get_clip_by_id(db, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    try:
        cid = await _resolve_cid(clip.bvid, clip.page)
        dash_data = await _get_dash_data(clip.bvid, cid, clip_id)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    audio_streams = dash_data.get("dash", {}).get("audio", [])
    if not audio_streams:
        raise HTTPException(status_code=502, detail="No audio streams available")
    return await _proxy_stream(audio_streams[0]["base_url"], request.headers.get("range"))


# ══════════════════════════════════════════════
# Chat routes
# ══════════════════════════════════════════════
chat_router = APIRouter()

CHAT_SYSTEM_PROMPT = (
    "你是一位专业的英语学习教练，名叫 RealEnglish Coach。你的角色是：\n"
    "1. 用英语回答用户的问题，必要时用中文解释\n"
    "2. 纠正用户的语法错误，给出改进建议\n"
    "3. 帮助用户理解英语影视对话中的地道表达\n"
    "4. 鼓励用户多使用英语交流\n"
    "5. 保持友好、耐心的语气\n\n"
    "当用户用英语提问时，先用英语回答，然后可以补充中文说明。"
    "当用户提到影视片段或对话内容时，主动提供相关的语言点分析。"
)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@chat_router.post("/chat", response_model=UnifiedResponse)
async def chat_with_ai(
    req: ChatRequest, db: Session = Depends(get_db),
    x_device_id: str = Header(None, alias="X-Device-Id"),
    authorization: str = Header(None),
):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    if len(req.message) > 1000:
        raise HTTPException(status_code=400, detail="消息过长（最多 1000 字符）")
    user = None
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization[7:])
        if payload and payload.get("sub"):
            user = get_user_by_id(db, payload["sub"])
    if not user:
        if not x_device_id:
            raise HTTPException(status_code=400, detail="缺少 X-Device-Id 请求头")
        user = get_or_create_user(db, x_device_id)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可访问此对话接口")
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    for msg in req.history[-10:]:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": req.message})
    try:
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        reply = await call_deepseek(prompt, temperature=0.7)
    except Exception as e:
        logger.error(f"AI 对话调用失败: {e}")
        raise HTTPException(status_code=500, detail="AI 服务暂时不可用，请稍后重试")
    return UnifiedResponse(data={"reply": reply.strip(), "user_id": str(user.id)})


@chat_router.post("/stream")
async def chat_with_ai_stream(
    req: ChatRequest, db: Session = Depends(get_db),
    x_device_id: str = Header(None, alias="X-Device-Id"),
    authorization: str = Header(None),
):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    if len(req.message) > 1000:
        raise HTTPException(status_code=400, detail="消息过长（最多 1000 字符）")
    user = None
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization[7:])
        if payload and payload.get("sub"):
            user = get_user_by_id(db, payload["sub"])
    if not user:
        if not x_device_id:
            raise HTTPException(status_code=400, detail="缺少 X-Device-Id 请求头")
        user = get_or_create_user(db, x_device_id)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可访问此对话接口")
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    for msg in req.history[-10:]:
        if msg.get("role") in ("user", "assistant") and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": req.message})

    async def event_generator():
        try:
            async for chunk in stream_deepseek_messages(messages, temperature=0.7):
                yield chunk
        except Exception as error:
            logger.error(f"AI 流式对话调用失败: {error}")
            yield "AI 服务暂时不可用，请稍后重试。"

    return StreamingResponse(event_generator(), media_type="text/plain; charset=utf-8")


# ══════════════════════════════════════════════
# Speaking routes
# ══════════════════════════════════════════════
speaking_router = APIRouter()


async def _generate_encouraging_feedback(score: dict, ref_text: str) -> str:
    prompt = (
        f"你是一位温暖的口语教练。用户完成了英语跟读练习，原台词是：{ref_text[:200]}\n"
        f"评分（满分5分）：总分{score['total_score']}，准确度{score['accuracy']}，流畅度{score['fluency']}。\n"
        "请写一段鼓励性中文反馈（50-100字），先肯定努力，再给1个具体改进建议，以问题结尾。"
    )
    try:
        return await call_deepseek(prompt, temperature=0.7)
    except Exception:
        logger.warning("AI 反馈生成失败，使用默认反馈")
        return "太棒了，继续加油！试着更注意单词的连读，会让发音更地道哦。下次想挑战哪句台词？"


def _convert_webm_to_pcm(webm_bytes: bytes) -> bytes:
    tmp_in = tmp_out = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(webm_bytes)
            tmp_in = f.name
        tmp_out = tempfile.mktemp(suffix=".pcm")
        ffmpeg_path = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
        subprocess.run([ffmpeg_path, "-y", "-i", tmp_in, "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", "-f", "s16le", tmp_out], capture_output=True, check=True, timeout=30)
        with open(tmp_out, "rb") as f:
            return f.read()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"音频转码失败: {e.stderr.decode(errors='replace')}") from e
    finally:
        if tmp_in and os.path.exists(tmp_in):
            os.unlink(tmp_in)
        if tmp_out and os.path.exists(tmp_out):
            os.unlink(tmp_out)


async def _speech_eval_degraded(audio_data: bytes, ref_text: str) -> dict:
    api_key = getattr(settings, "xf_api_key", None)
    api_secret = getattr(settings, "xf_api_secret", None)
    app_id = getattr(settings, "xf_appid", None)
    if not all([api_key, api_secret, app_id]):
        logger.warning("讯飞 API 凭证未配置，使用默认评分")
        return dict(DEFAULT_SCORE)
    try:
        pcm_data = _convert_webm_to_pcm(audio_data)
        result = await evaluate_audio(pcm_data, ref_text, app_id, api_key, api_secret)
        return result
    except Exception as e:
        logger.error("讯飞评测调用失败: %s，使用降级评分", e, exc_info=True)
        return dict(DEFAULT_SCORE)


@speaking_router.post("/evaluate", response_model=UnifiedResponse)
async def evaluate_speaking(
    audio: UploadFile = File(...), reference_text: str = Form(""),
    mode: str = Form("repeat"), clip_id: str = Form(None),
    duration_sec: str = Form("0"),
    db: Session = Depends(get_db),
    x_device_id: str = Header(None, alias="X-Device-Id"),
    authorization: str = Header(None),
):
    if reference_text and len(reference_text) > 500:
        reference_text = reference_text[:500]
    user = None
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization[7:])
        if payload and payload.get("sub"):
            user = get_user_by_id(db, payload["sub"])
    if not user and x_device_id:
        user = get_or_create_user(db, x_device_id)
    if not user:
        raise HTTPException(status_code=401, detail="未登录，请先登录或提供设备 ID")
    if user.role != "student":
        raise HTTPException(status_code=403, detail="仅学生可使用口语练习")
    audio_data = await audio.read()

    # ── 自由应答模式：语音识别 → AI 评分 ──
    if mode == "free":
        pcm_data = _convert_webm_to_pcm(audio_data)
        api_key = getattr(settings, "xf_api_key", "")
        api_secret = getattr(settings, "xf_api_secret", "")
        app_id = getattr(settings, "xf_appid", "")
        transcript = ""
        if all([api_key, api_secret, app_id]):
            transcript = await recognize_speech(pcm_data, app_id, api_key, api_secret)

        from app.ai import evaluate_free_response
        result = await evaluate_free_response(reference_text, transcript)
        score = {
            "total_score": result["score"],
            "content_score": result["content_score"],
            "grammar_score": result["grammar_score"],
            "fluency_score": result["fluency_score"],
            "vocabulary_score": result["vocabulary_score"],
        }
        feedback = result["feedback"]

        audio_url = None
        try:
            filename = f"speaking/{user.id}/{uuid.uuid4().hex}.webm"
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            audio_url = await upload_to_oss(tmp_path, filename)
        except Exception as e:
            logger.error(f"音频保存失败: {e}")

        try:
            dur = int(duration_sec) if duration_sec and duration_sec.isdigit() else 0
            record = SpeakingRecordModel(
                user_id=str(user.id), clip_id=clip_id, mode=mode,
                reference_text=transcript or reference_text,
                audio_url=audio_url, score_json=score, feedback=feedback,
                duration_sec=dur,
            )
            db.add(record)
            db.commit()
        except Exception as e:
            logger.error(f"保存口语记录失败: {e}")

        return UnifiedResponse(data={
            "score": score, "feedback": feedback, "audio_url": audio_url,
            "transcript": transcript,
        })

    # ── 跟读模式：讯飞语音评测 ──
    score = await _speech_eval_degraded(audio_data, reference_text)
    feedback = await _generate_encouraging_feedback(score, reference_text)
    audio_url = None
    try:
        filename = f"speaking/{user.id}/{uuid.uuid4().hex}.webm"
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        audio_url = await upload_to_oss(tmp_path, filename)
    except Exception as e:
        logger.error(f"音频保存失败: {e}")
    try:
        dur = int(duration_sec) if duration_sec and duration_sec.isdigit() else 0
        record = SpeakingRecordModel(user_id=str(user.id), clip_id=clip_id, mode=mode, reference_text=reference_text, audio_url=audio_url, score_json=score, feedback=feedback, duration_sec=dur)
        db.add(record)
        db.commit()
    except Exception as e:
        logger.error(f"保存口语记录失败: {e}")
    return UnifiedResponse(data={"score": score, "feedback": feedback, "audio_url": audio_url})


@speaking_router.post("/generate-question", response_model=UnifiedResponse)
async def generate_speaking_question(summary: str = Form(...)):
    prompt = (
        f"根据以下影视片段剧情，生成一个开放性的英语口试问题，鼓励用户表达个人观点。\n"
        f"剧情：{summary}\n"
        "要求问题与剧情相关，没有标准答案。只输出JSON，不要多余文字。\n"
        '输出格式：{"question": "..."}'
    )
    try:
        raw = await call_deepseek(prompt, temperature=0.7)
        content = raw.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        result = json.loads(content)
        question = result.get("question", raw[:200])
    except Exception:
        question = raw[:200] if raw else "What do you think about this scene?"
    return UnifiedResponse(data={"question": question})


@speaking_router.get("/history", response_model=UnifiedResponse)
def get_speaking_history(user: UserModel = Depends(require_student_role), db: Session = Depends(get_db)):
    """返回学生最近 30 天口语记录（最多 50 条）用于趋势图。"""
    from datetime import timedelta
    since = beijing_now() - timedelta(days=30)
    records = db.query(SpeakingRecordModel).filter(
        SpeakingRecordModel.user_id == str(user.id),
        SpeakingRecordModel.created_at >= since,
    ).order_by(SpeakingRecordModel.created_at.asc()).limit(50).all()
    return UnifiedResponse(data=[{
        "id": str(r.id), "mode": r.mode, "duration_sec": r.duration_sec,
        "total_score": r.score_json.get("total_score") if r.score_json else None,
        "accuracy": r.score_json.get("accuracy") if r.score_json else None,
        "fluency": r.score_json.get("fluency") if r.score_json else None,
        "integrity": r.score_json.get("integrity") if r.score_json else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in records])


# 口语音频回放（教师端）
@speaking_router.get("/{record_id}/audio")
def get_speaking_audio(record_id: str, db: Session = Depends(get_db)):
    record = db.query(SpeakingRecordModel).filter(SpeakingRecordModel.id == record_id).first()
    if not record or not record.audio_url:
        raise HTTPException(status_code=404, detail="音频不存在")
    import os as _os
    path = record.audio_url
    if not _os.path.isabs(path):
        path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), path.lstrip("/"))
    if not _os.path.isfile(path):
        raise HTTPException(status_code=404, detail="音频文件不存在")
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type="audio/mpeg")


# ══════════════════════════════════════════════
# TTS routes
# ══════════════════════════════════════════════
tts_router = APIRouter()
_tts_engine = None


def _get_tts_engine():
    global _tts_engine
    if _tts_engine is None:
        app_id = getattr(settings, "xf_appid", "")
        api_key = getattr(settings, "xf_api_key", "")
        api_secret = getattr(settings, "xf_api_secret", "")
        if all([app_id, api_key, api_secret]):
            _tts_engine = TTSEngine(app_id, api_key, api_secret)
    return _tts_engine


class TTSRequest(BaseModel):
    text: str
    voice: str = "x4_xiaoyan"
    speed: int = 50


@tts_router.post("/synthesize")
async def synthesize_speech(req: TTSRequest):
    if len(req.text) > 2000:
        raise HTTPException(status_code=400, detail="文本过长（最多 2000 字）")
    engine = _get_tts_engine()
    if not engine:
        raise HTTPException(status_code=501, detail="TTS 服务未配置")
    audio_bytes = await engine.synthesize(req.text, voice=req.voice, speed=req.speed)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="TTS 合成失败")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        filename = f"tts/{uuid.uuid4()}.mp3"
        audio_url = await upload_to_oss(tmp_path, filename)
        if not audio_url:
            raise HTTPException(status_code=500, detail="音频上传失败")
        return {"audio_url": audio_url}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ══════════════════════════════════════════════
# Student Learning routes
# ══════════════════════════════════════════════
student_router = APIRouter()


class BindInviteCodeRequest(BaseModel):
    invite_code: str


@student_router.post("/bind-invite", response_model=UnifiedResponse)
def student_bind_invite(req: BindInviteCodeRequest, db: Session = Depends(get_db),
                         current_user: UserModel = Depends(require_student_role)):
    """学生通过邀请码绑定教师。"""
    if current_user.teacher_id:
        return UnifiedResponse(data={"bound": True, "message": "已绑定教师"})
    teacher = db.query(UserModel).filter(
        UserModel.invite_code == req.invite_code.upper().strip(),
        UserModel.role == "teacher",
    ).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="无效的邀请码")
    student = db.query(UserModel).filter(UserModel.id == str(current_user.id)).first()
    student.teacher_id = str(teacher.id)
    grp = db.query(TeacherGroupModel).filter(TeacherGroupModel.teacher_id == str(teacher.id)).first()
    if grp:
        student.group_id = str(grp.id)
    db.commit()
    return UnifiedResponse(data={"bound": True, "teacher": teacher.username})


class StudentAssistantRequest(BaseModel):
    message: str
    history: list[dict] = []
    thread_id: str | None = None


class StudentRecommendationRequest(BaseModel):
    user_preference: str


class ClipAssistantRequest(BaseModel):
    message: str
    clip_id: str
    history: list[dict] = []


class StudentSuggestionRequest(BaseModel):
    pass


class ClipSuggestionRequest(BaseModel):
    clip_id: str



@student_router.get("/questions/placement", response_model=UnifiedResponse)
def get_placement_test(db: Session = Depends(get_db)):
    questions = get_placement_questions(db)
    if len(questions) < 10:
        raise HTTPException(status_code=503, detail=f"题库不足，当前仅 {len(questions)} 题可用，请稍后重试")
    clip_ids = list({str(q.clip_id) for q in questions if q.clip_id})
    clip_map = get_clips_by_ids(db, clip_ids)
    return UnifiedResponse(data=[{
        "id": str(q.id), "clip_id": str(q.clip_id), "type": q.type,
        "difficulty": q.difficulty,
        "content": {"question": q.content["question"], "options": q.content["options"]},
        "video": (
            {"bvid": clip_map[str(q.clip_id)].bvid, "page": clip_map[str(q.clip_id)].page, "start_sec": clip_map[str(q.clip_id)].start_sec, "end_sec": clip_map[str(q.clip_id)].end_sec}
            if q.clip_id and str(q.clip_id) in clip_map else None
        ),
    } for q in questions])


@student_router.post("/questions/generate", response_model=UnifiedResponse)
async def generate_questions(req: GenerateQuestionRequest, db: Session = Depends(get_db), _: UserModel = Depends(require_student_role)):
    clip = get_clip_by_id(db, req.clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    existing = get_questions_by_clip(db, req.clip_id)
    cached = [q for q in existing if q.difficulty == req.difficulty]
    if cached:
        return UnifiedResponse(data=[{"id": str(q.id), "type": q.type, "difficulty": q.difficulty, "content": {"question": q.content["question"], "options": q.content["options"]}} for q in cached])
    state = {"clip_id": req.clip_id, "dialogue_text": clip.dialogue_text or "", "difficulty": req.difficulty, "generated_questions": [], "error": ""}
    final_state = await quiz_app.ainvoke(state)
    if final_state.get("error"):
        raise HTTPException(status_code=500, detail=final_state["error"])
    generated = final_state["generated_questions"]
    if not generated:
        raise HTTPException(status_code=500, detail="AI 出题返回空结果")
    saved = []
    for qd in generated:
        q = create_question(db, {"clip_id": req.clip_id, "type": "part2", "difficulty": req.difficulty, "content": {"question": qd["question"], "options": qd["options"], "answer": qd["answer"], "explanation": qd.get("explanation", "")}})
        saved.append(q)
    return UnifiedResponse(data=[{"id": str(q.id), "type": q.type, "difficulty": q.difficulty, "content": {"question": q.content["question"], "options": q.content["options"]}} for q in saved])


@student_router.post("/answers/submit", response_model=UnifiedResponse)
def submit_answer(
    req: AnswerSubmitRequest,
    db: Session = Depends(get_db),
    authorization: str = Header(None),
    x_device_id: str = Header(None, alias="X-Device-Id"),
):
    question = get_question_by_id(db, req.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    is_correct = req.selected_option == question.content["answer"]

    # 尝试获取用户并保存答题记录
    user = None
    if authorization and authorization.startswith("Bearer "):
        payload = decode_access_token(authorization[7:])
        if payload and payload.get("sub"):
            user = get_user_by_id(db, payload["sub"])
    if not user and x_device_id:
        user = get_or_create_user(db, x_device_id)
    if user:
        create_record(db, user_id=str(user.id), question_id=req.question_id,
                       selected_option=req.selected_option, is_correct=is_correct)
        # 更新该学生的任务进度快照
        from app.crud import update_task_progress_for_student
        update_task_progress_for_student(db, str(user.id))

    return UnifiedResponse(data={"is_correct": is_correct, "correct_answer": question.content["answer"], "explanation": question.content.get("explanation", "")})


@student_router.post("/answers/submit-placement", response_model=UnifiedResponse)
def submit_placement(req: PlacementSubmitRequest, user: UserModel = Depends(require_student_role), db: Session = Depends(get_db)):
    if len(req.answers) != 10:
        raise HTTPException(status_code=400, detail=f"需要提交10题答案，当前提交 {len(req.answers)} 题")
    correct_count = 0
    details = []
    for answer in req.answers:
        question = get_question_by_id(db, answer.question_id)
        if not question:
            continue
        is_correct = answer.selected_option == question.content["answer"]
        if is_correct:
            correct_count += 1
        create_record(db, user_id=str(user.id), question_id=answer.question_id, selected_option=answer.selected_option, is_correct=is_correct)
        details.append({"question_id": answer.question_id, "is_correct": is_correct, "correct_answer": question.content["answer"], "explanation": question.content.get("explanation", "")})
    level = assign_level(correct_count, len(req.answers))
    update_user_level(db, str(user.id), level)
    return UnifiedResponse(data={"score": correct_count, "total": len(req.answers), "level": level, "details": details})


@student_router.get("/answers/wrong-notes", response_model=UnifiedResponse)
def get_wrong_notes_api(user: UserModel = Depends(require_student_role), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    notes = get_wrong_notes(db, str(user.id), skip=skip, limit=limit)
    total = get_wrong_note_count(db, str(user.id))
    return UnifiedResponse(data={"items": notes, "total": total})


@student_router.get("/answers/stats", response_model=UnifiedResponse)
def get_practice_stats_api(user: UserModel | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if not user or user.role != "student":
        return UnifiedResponse(data={"total": 0, "correct": 0, "accuracy": 0, "difficulty_stats": {}})
    return UnifiedResponse(data=get_practice_stats(db, str(user.id)))


# ── Vocabulary ──
class VocabLookupRequest(BaseModel):
    word: str
    clip_id: str | None = None

class VocabSaveRequest(BaseModel):
    word: str
    clip_id: str | None = None
    definition: str | None = None

class VocabListParams(BaseModel):
    page: int = 1
    page_size: int = 50
    sort: str = "newest"


@student_router.post("/vocabulary/lookup", response_model=UnifiedResponse)
async def api_lookup_word(req: VocabLookupRequest, db: Session = Depends(get_db),
                           user: UserModel = Depends(require_student_role)):
    """查询单词释义（DeepSeek + 缓存）。"""
    word = req.word.strip().lower()
    if not word or len(word) < 2:
        raise HTTPException(status_code=400, detail="单词太短")
    cached = lookup_word_definition(db, word)
    if cached:
        return UnifiedResponse(data={"word": word, "definition": cached, "cached": True})
    try:
        from app.ai import call_deepseek
        prompt = f"请用中文解释英文单词「{word}」，包含：音标、词性、中文释义、一个英文例句及中文翻译。用简洁的格式输出，不要多余解释。"
        definition = await call_deepseek(prompt, temperature=0.3)
        return UnifiedResponse(data={"word": word, "definition": definition.strip(), "cached": False})
    except Exception:
        raise HTTPException(status_code=500, detail="AI 服务暂不可用")


@student_router.post("/vocabulary/save", response_model=UnifiedResponse)
def api_save_vocab(req: VocabSaveRequest, db: Session = Depends(get_db),
                   user: UserModel = Depends(require_student_role)):
    """收藏单词到个人单词本。若已存在则更新。"""
    word = req.word.strip().lower()
    if not word:
        raise HTTPException(status_code=400, detail="单词不能为空")
    v = add_vocabulary(db, str(user.id), word, definition=req.definition or "", clip_id=req.clip_id)
    return UnifiedResponse(data={"id": v.id, "word": v.word, "mastered": v.mastered})


@student_router.delete("/vocabulary/{vocab_id}", response_model=UnifiedResponse)
def api_delete_vocab(vocab_id: str, db: Session = Depends(get_db),
                     user: UserModel = Depends(require_student_role)):
    if not remove_vocabulary(db, str(user.id), vocab_id):
        raise HTTPException(status_code=404, detail="单词不存在")
    return UnifiedResponse(data={"deleted": True})


@student_router.get("/vocabulary", response_model=UnifiedResponse)
def api_list_vocab(page: int = 1, page_size: int = 50, sort: str = "newest",
                   db: Session = Depends(get_db),
                   user: UserModel = Depends(require_student_role)):
    items, total = list_vocabulary(db, str(user.id), page=page, page_size=page_size, sort=sort)
    return UnifiedResponse(data={
        "items": [{"id": v.id, "word": v.word, "definition": v.definition, "mastered": v.mastered, "clip_id": v.clip_id, "created_at": v.created_at.isoformat() if v.created_at else None} for v in items],
        "total": total,
    })


@student_router.patch("/vocabulary/{vocab_id}/mastered", response_model=UnifiedResponse)
def api_toggle_mastered(vocab_id: str, db: Session = Depends(get_db),
                        user: UserModel = Depends(require_student_role)):
    v = toggle_vocabulary_mastered(db, str(user.id), vocab_id)
    if not v:
        raise HTTPException(status_code=404, detail="单词不存在")
    return UnifiedResponse(data={"id": v.id, "mastered": v.mastered})


class VocabQuizSubmitRequest(BaseModel):
    answers: list[dict]  # [{ word: str, selected: int, correct: int }]

@student_router.post("/vocabulary/quiz/generate", response_model=UnifiedResponse)
async def api_vocab_quiz_generate(count: int = 5, db: Session = Depends(get_db),
                                   user: UserModel = Depends(require_student_role)):
    """从单词本随机抽取单词，调用 DeepSeek 生成选择题。"""
    words, _ = list_vocabulary(db, str(user.id), page=1, page_size=200, sort="newest")
    if len(words) < 4:
        raise HTTPException(status_code=400, detail="单词本至少需要 4 个单词才能检测")
    import random
    picked = random.sample(words, min(count, len(words)))

    word_list = "\n".join([f"- {w.word}: {w.definition or '无释义'}" for w in picked])
    prompt = f"""根据以下单词列表，生成 {len(picked)} 道英语词汇选择题。
每道题测试一个目标单词，题干为一段英文描述或例句（包含空格____），选项为 4 个英文单词（A/B/C/D），其中一个为正确答案。

单词列表：
{word_list}

要求：
1. 每道题的题干用英文描述或例句，空白处____填入目标单词
2. 四个选项中只有一个是正确答案（目标单词）
3. 给出正确答案的索引（0=第一选项即A, 1=B, 2=C, 3=D）和简短中文解析
4. 输出纯 JSON 数组，不要任何解释：

[{{"word":"目标单词","question":"题干含____","options":["选项A","选项B","选项C","选项D"],"answer":0,"explanation":"简短解析"}}]
"""
    try:
        raw = await call_deepseek(prompt, temperature=0.6)
        questions = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        if not isinstance(questions, list) or len(questions) == 0:
            raise ValueError("AI 返回格式异常")
        return UnifiedResponse(data={"questions": questions})
    except Exception as e:
        logger.error(f"词汇检测出题失败: {e}")
        raise HTTPException(status_code=500, detail="AI 出题失败，请稍后重试")


@student_router.post("/vocabulary/quiz/submit", response_model=UnifiedResponse)
def api_vocab_quiz_submit(req: VocabQuizSubmitRequest, db: Session = Depends(get_db),
                           user: UserModel = Depends(require_student_role)):
    """提交词汇检测答案，错题记录到 practice_records。"""
    correct = 0
    total = len(req.answers)
    uid = str(user.id)

    for a in req.answers:
        word = a.get("word", "").strip().lower()
        selected = a.get("selected", -1)
        is_correct = selected == a.get("correct", -1)
        if is_correct:
            correct += 1

        # 记录到错题表（如有对应question_id就用，没有就创建临时记录）
        record = PracticeRecordModel(
            user_id=uid,
            question_id="",  # 词汇检测题目不存 questions 表，用空字符串占位
            selected_option=selected,
            is_correct=is_correct,
        )
        db.add(record)

        # 答错则将该单词标记为未掌握
        if not is_correct and word:
            existing = db.query(UserVocabularyModel).filter(
                UserVocabularyModel.user_id == uid,
                UserVocabularyModel.word == word,
            ).first()
            if existing:
                existing.mastered = False

    db.commit()

    return UnifiedResponse(data={
        "total": total, "correct": correct,
        "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
    })


@student_router.get("/student/dashboard", response_model=UnifiedResponse)
def get_student_dashboard(user: UserModel = Depends(require_student_role), db: Session = Depends(get_db)):
    """学生端学习概览页——聚合今日统计 + 周趋势 + 热力图 + 推荐片段"""
    from app.crud import get_student_dashboard_data
    data = get_student_dashboard_data(db, str(user.id))
    return UnifiedResponse(data=data)


@student_router.post("/student/recommendations", response_model=UnifiedResponse)
async def interest_recommendation_endpoint(req: StudentRecommendationRequest, _: UserModel = Depends(require_student_role)):
    final_state = await interest_app.ainvoke({"user_preference": req.user_preference, "recommended_clips": []})
    return UnifiedResponse(data={"clip_ids": final_state["recommended_clips"]})


def _ensure_thread(db: Session, thread_id: str | None, user_id: str, role: str) -> str:
    """确保线程存在，不存在则创建。返回 thread_id。"""
    if thread_id:
        existing = db.query(AssistantThreadModel).filter(
            AssistantThreadModel.id == thread_id,
            AssistantThreadModel.user_id == user_id,
        ).first()
        if existing:
            return thread_id
    thread = AssistantThreadModel(user_id=user_id, role=role)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread.id


def _update_thread_title(db: Session, thread_id: str, content: str):
    """用首条用户消息的前 30 字更新线程标题。"""
    thread = db.query(AssistantThreadModel).filter(AssistantThreadModel.id == thread_id).first()
    if thread and thread.title == "新对话":
        title = content.strip()[:30]
        if len(content.strip()) > 30:
            title += "..."
        thread.title = title
        db.commit()


@student_router.post("/assistants/student/suggestions", response_model=UnifiedResponse)
async def student_assistant_suggestions(
    _: StudentSuggestionRequest,
    current_user: UserModel = Depends(require_student_role),
    db: Session = Depends(get_db),
):
    """为学生学习助手生成个性化建议提示词。"""
    from app.agents import get_my_stats, get_my_mistakes, get_my_activity

    user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    cfg = {"configurable": {"user_id": str(current_user.id)}}

    stats_text = "暂无学习数据"
    mistakes_text = "暂无错题数据"
    activity_text = "暂无活跃数据"
    try:
        stats_text = await get_my_stats.ainvoke({}, config=cfg)
    except Exception as e:
        logger.warning(f"获取学习统计失败: {e}")
    try:
        mistakes_text = await get_my_mistakes.ainvoke({}, config=cfg)
    except Exception as e:
        logger.warning(f"获取错题失败: {e}")
    try:
        activity_text = await get_my_activity.ainvoke({}, config=cfg)
    except Exception as e:
        logger.warning(f"获取活跃度失败: {e}")

    prompt = (
        "你是一位 RealEnglish 学生学习助手。请根据以下学生情况，生成 4 条不同的提示词建议。\n\n"
        f"学生等级：{user.level if user else '未定级'}\n"
        f"学习统计：{stats_text}\n"
        f"错题信息：{mistakes_text}\n"
        f"活跃情况：{activity_text}\n\n"
        "要求：\n"
        "1. 每条建议必须是一个完整的、可直接发送给学习助手的问题，用中文\n"
        "2. 覆盖不同类型：查统计、分析错题、制定计划、推荐片段\n"
        "3. 使用第一人称（\"我\"），语气亲切\n"
        "4. 每条建议不超过 30 字\n\n"
        "请严格按 JSON 格式输出，只输出一个字符串数组，不要任何额外内容：\n"
        '["建议1", "建议2", "建议3", "建议4"]'
    )

    try:
        raw = await call_deepseek(prompt, temperature=0.7)
        content = raw.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        suggestions = json.loads(content)
        if not isinstance(suggestions, list):
            suggestions = []
        suggestions = [str(s) for s in suggestions][:5]
    except Exception as e:
        logger.warning(f"生成学生建议失败: {e}")
        suggestions = []

    return UnifiedResponse(data={"suggestions": suggestions})


@student_router.post("/assistants/student/chat", response_model=UnifiedResponse)
async def student_assistant_chat(req: StudentAssistantRequest, current_user: UserModel = Depends(require_student_role), db: Session = Depends(get_db)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    thread_id = _ensure_thread(db, req.thread_id, str(current_user.id), "student")
    _update_thread_title(db, thread_id, req.message)
    agent = get_student_agent()
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": req.message}]},
        config={
            "configurable": {
                "user_id": str(current_user.id),
                "thread_id": thread_id,
            }
        },
    )
    reply = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.type == "ai":
            reply = msg.content
            break
    # 持久化用户消息和 AI 回复
    save_message_to_db(str(current_user.id), thread_id, "user", req.message)
    if reply:
        save_message_to_db(str(current_user.id), thread_id, "assistant", reply)
    return UnifiedResponse(data={"reply": reply, "thread_id": thread_id})


@student_router.post("/assistants/student/chat/stream")
async def student_assistant_chat_stream(req: StudentAssistantRequest, current_user: UserModel = Depends(require_student_role), db: Session = Depends(get_db)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    thread_id = _ensure_thread(db, req.thread_id, str(current_user.id), "student")
    _update_thread_title(db, thread_id, req.message)
    llm = get_llm(temperature=0.7)
    history = await get_thread_messages(str(current_user.id), thread_id)
    full_reply = []
    student_tools = [get_current_time, get_my_stats, get_my_mistakes, get_my_activity, search_clips, get_clip_info, get_my_tasks, generate_my_report, get_my_vocabulary_stats, get_my_weak_words, get_speaking_trend, get_smart_review_plan]

    async def event_generator():
        try:
            nonlocal full_reply
            yield json.dumps({"type": "thread_id", "thread_id": thread_id}) + "\n"
            async for evt in stream_agent_response(
                llm=llm,
                tools=student_tools,
                system_prompt=STUDENT_AGENT_SYSTEM_PROMPT,
                user_message=req.message,
                history=history,
                user_id=str(current_user.id),
            ):
                if evt.get("type") == "content":
                    full_reply.append(evt["content"])
                yield json.dumps(evt) + "\n"
            save_message_to_db(str(current_user.id), thread_id, "user", req.message)
            ai_text = "".join(full_reply)
            if ai_text:
                save_message_to_db(str(current_user.id), thread_id, "assistant", ai_text)
        except Exception as error:
            logger.error(f"学生助手流式调用失败: {error}")
            yield json.dumps({"type": "error", "message": "AI 服务暂时不可用，请稍后重试。"}) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@student_router.post("/assistants/student/clip-chat/stream")
async def clip_assistant_stream(
    req: ClipAssistantRequest,
    current_user: UserModel = Depends(require_student_role),
    db: Session = Depends(get_db),
):
    """片段学习助手 — 将当前片段上下文注入 system prompt 后流式返回"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 读取片段信息
    from app.models import VideoClipModel
    clip = db.query(VideoClipModel).filter(VideoClipModel.id == req.clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="片段不存在")

    clip_context = (
        f"【剧名】{clip.title or '未知'}\n"
        f"【类别】{clip.category or '未知'}\n"
        f"【剧情】{clip.summary or '暂无'}\n"
        f"【对话文本】\n{clip.dialogue_text or '暂无'}"
    )

    system_prompt = (
        "你是一位影视英语学习导师。学生正在观看以下片段：\n\n"
        f"{clip_context}\n\n"
        "请根据以上片段内容，解答学生关于词汇用法、语法结构、文化背景、角色对话含义等方面的问题。\n"
        "要求：用中文回答，语气温暖鼓励，回答简洁（不超过200字）。如果学生问的内容与当前片段无关，也可以简要回答。"
    )

    # thread_id: clip_{clip_id}_{user_id}，确保同一片段同一用户的对话持久化
    thread_id = f"clip_{req.clip_id}_{str(current_user.id)[:8]}"

    messages = [{"role": "system", "content": system_prompt}]
    for h in req.history[-10:]:  # 最近 10 轮
        messages.append(h)
    messages.append({"role": "user", "content": req.message})

    llm = get_llm(temperature=0.7)
    full_reply = []

    async def event_generator():
        nonlocal full_reply
        try:
            import asyncio as _asyncio
            async for chunk in llm.astream(messages):
                if chunk.content:
                    full_reply.append(chunk.content)
                    yield json.dumps({"type": "content", "content": chunk.content}) + "\n"
                    await _asyncio.sleep(0.01)  # 确保每个 token 作为独立 SSE 块发送
            save_message_to_db(str(current_user.id), thread_id, "user", req.message)
            ai_text = "".join(full_reply)
            if ai_text:
                save_message_to_db(str(current_user.id), thread_id, "assistant", ai_text)
            yield json.dumps({"type": "done"}) + "\n"
        except Exception as error:
            logger.error(f"片段助手流式失败: {error}")
            yield json.dumps({"type": "error", "message": "AI 服务暂时不可用，请稍后重试。"}) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@student_router.post("/assistants/student/clip-chat/suggestions", response_model=UnifiedResponse)
async def clip_assistant_suggestions(
    req: ClipSuggestionRequest,
    current_user: UserModel = Depends(require_student_role),
    db: Session = Depends(get_db),
):
    """根据当前片段内容生成引导性问题。"""
    clip = db.query(VideoClipModel).filter(VideoClipModel.id == req.clip_id).first()
    if not clip:
        return UnifiedResponse(data={"suggestions": []})

    clip_dialogue = (clip.dialogue_text or "")[:500]
    clip_summary = clip.summary or "暂无简介"

    prompt = (
        "你是一位影视英语学习导师。学生正在观看以下片段，请针对该片段生成 4 条引导性提问。\n\n"
        f"标题：{clip.title or '未知'}\n"
        f"类别：{clip.category or '未知'}\n"
        f"难度：{clip.difficulty or '未知'}\n"
        f"剧情：{clip_summary}\n"
        f"对话文本：\n{clip_dialogue}\n\n"
        "要求：\n"
        "1. 问题必须基于当前片段的具体内容（词汇、语法、文化背景、剧情理解）\n"
        "2. 用中文提问，语气亲切\n"
        "3. 每条不超过 25 字\n\n"
        "请严格按 JSON 格式输出，只输出一个字符串数组：\n"
        '["问题1", "问题2", "问题3", "问题4"]'
    )

    try:
        raw = await call_deepseek(prompt, temperature=0.7)
        content = raw.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        suggestions = json.loads(content)
        if not isinstance(suggestions, list):
            suggestions = []
        suggestions = [str(s) for s in suggestions][:5]
    except Exception as e:
        logger.warning(f"生成片段建议失败: {e}")
        suggestions = []

    return UnifiedResponse(data={"suggestions": suggestions})


# ══════════════════════════════════════════════
# Teacher routes
# ══════════════════════════════════════════════
teacher_router = APIRouter(dependencies=[Depends(require_teacher_role)])


@teacher_router.get("/invite-code", response_model=UnifiedResponse)
def get_invite_code(db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    """返回教师的邀请码，不存在则自动生成。"""
    teacher = db.query(UserModel).filter(UserModel.id == str(current_user.id)).first()
    if not teacher.invite_code:
        import string, random
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            if not db.query(UserModel).filter(UserModel.invite_code == code).first():
                break
        teacher.invite_code = code
        db.commit()
    return UnifiedResponse(data={"invite_code": teacher.invite_code})


@teacher_router.post("/invite-code/regenerate", response_model=UnifiedResponse)
def regenerate_invite_code(db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    """重新生成邀请码。"""
    import string, random
    teacher = db.query(UserModel).filter(UserModel.id == str(current_user.id)).first()
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if not db.query(UserModel).filter(UserModel.invite_code == code).first():
            break
    teacher.invite_code = code
    db.commit()
    return UnifiedResponse(data={"invite_code": code})


@teacher_router.get("/dashboard", response_model=UnifiedResponse)
def get_teacher_dashboard_endpoint(
    group_id: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_teacher_role),
):
    """教师看板——聚合统计卡片、近14天趋势、等级分布。"""
    from app.crud import get_teacher_dashboard_stats
    data = get_teacher_dashboard_stats(db, teacher_id=str(current_user.id), group_id=group_id)
    return UnifiedResponse(data=data)


@teacher_router.get("/students", response_model=UnifiedResponse)
def list_students(
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None), group_id: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_teacher_role),
):
    items, total = get_students(db, teacher_id=str(current_user.id), skip=skip, limit=limit, keyword=keyword, group_id=group_id)
    return UnifiedResponse(data={"items": items, "total": total})


@teacher_router.get("/students/level-distribution", response_model=UnifiedResponse)
def level_distribution(group_id: str | None = Query(None), db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    return UnifiedResponse(data=get_level_distribution(db, teacher_id=str(current_user.id), group_id=group_id))


class BatchLevelRequest(BaseModel):
    student_ids: list[str]
    level: str


@teacher_router.post("/students/batch-level", response_model=UnifiedResponse)
def batch_level_endpoint(req: BatchLevelRequest, db: Session = Depends(get_db),
                          current_user: UserModel = Depends(require_teacher_role)):
    """批量设置学生等级。"""
    if not req.student_ids or req.level not in ("A", "B", "C"):
        raise HTTPException(status_code=400, detail="参数错误")
    changed = db.query(UserModel).filter(
        UserModel.id.in_(req.student_ids), UserModel.role == "student"
    ).update({UserModel.level: req.level}, synchronize_session=False)
    db.commit()
    return UnifiedResponse(data={"changed": changed})


@teacher_router.get("/students/all", response_model=UnifiedResponse)
def all_students_simple(db: Session = Depends(get_db),
                         current_user: UserModel = Depends(require_teacher_role)):
    """返回教师管辖的所有学生简要信息（供分级管理等使用）。"""
    from app.crud import _teacher_student_query
    rows = _teacher_student_query(db, str(current_user.id)).all()
    data = []
    for user, gname in rows:
        data.append({"id": str(user.id), "username": user.username, "level": user.level,
                     "group_name": gname or "未分组"})
    return UnifiedResponse(data=data)


@teacher_router.get("/students/{student_id}", response_model=UnifiedResponse)
def student_detail(student_id: str, db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    data = get_student_detail(db, str(current_user.id), student_id)
    if not data:
        raise HTTPException(status_code=404, detail="学生不存在")
    return UnifiedResponse(data=data)


@teacher_router.get("/students/alerts/list", response_model=UnifiedResponse)
def teacher_alerts(db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    """学习预警：不活跃 / 正确率骤降 / 未定级"""
    from datetime import timedelta
    now = beijing_now()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    students = db.query(UserModel).filter(
        UserModel.teacher_id == str(current_user.id),
        UserModel.role == "student"
    ).all()

    alerts = []
    for student in students:
        sid = str(student.id)
        name = student.username or "未命名"

        # 1. 未定级
        if not student.level:
            alerts.append({"student_id": sid, "username": name, "type": "unset_level", "description": "尚未完成定级测试"})
            continue

        # 2. 近7天活跃
        recent_count = db.query(PracticeRecordModel).filter(
            PracticeRecordModel.user_id == sid,
            PracticeRecordModel.answered_at >= week_ago
        ).count()
        recent_speaking = db.query(SpeakingRecordModel).filter(
            SpeakingRecordModel.user_id == sid,
            SpeakingRecordModel.created_at >= week_ago
        ).count()
        if recent_count == 0 and recent_speaking == 0:
            alerts.append({"student_id": sid, "username": name, "type": "inactive", "description": "最近 7 天无练习记录"})
            continue

        # 3. 正确率骤降（本周 vs 上周）
        def _accuracy_since(since_dt):
            records = db.query(PracticeRecordModel).filter(
                PracticeRecordModel.user_id == sid,
                PracticeRecordModel.answered_at >= since_dt
            ).all()
            if not records:
                return None
            return sum(1 for r in records if r.is_correct) / len(records)

        this_week = _accuracy_since(week_ago)
        last_week = _accuracy_since(two_weeks_ago)
        if this_week is not None and last_week is not None and last_week > 0:
            drop = (last_week - this_week) / last_week
            if drop >= 0.3:
                alerts.append({
                    "student_id": sid, "username": name, "type": "accuracy_drop",
                    "description": f"正确率从 {round(last_week*100)}% 降至 {round(this_week*100)}%（降幅 {round(drop*100)}%）"
                })

    return UnifiedResponse(data={"alerts": alerts, "total": len(alerts)})


@teacher_router.get("/groups", response_model=UnifiedResponse)
def list_groups(db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    return UnifiedResponse(data=list_teacher_groups_with_counts(db, str(current_user.id)))


@teacher_router.post("/groups", response_model=UnifiedResponse)
def create_group(req: TeacherGroupCreate, db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    group = create_teacher_group(db, str(current_user.id), req.name, req.description)
    return UnifiedResponse(data={"id": group.id, "name": group.name, "description": group.description, "student_count": 0})


@teacher_router.put("/groups/{group_id}", response_model=UnifiedResponse)
def edit_group(group_id: str, req: TeacherGroupUpdate, db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    group = get_teacher_group(db, group_id, str(current_user.id))
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    group = update_teacher_group(db, group, req.name, req.description)
    return UnifiedResponse(data={"id": group.id, "name": group.name, "description": group.description})


@teacher_router.post("/students/assign-group", response_model=UnifiedResponse)
def assign_group(req: StudentGroupAssignRequest, db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    if req.group_id:
        group = get_teacher_group(db, req.group_id, str(current_user.id))
        if not group:
            raise HTTPException(status_code=404, detail="分组不存在")
    user = assign_user_group(db, req.student_id, req.group_id)
    if not user or user.role != "student":
        raise HTTPException(status_code=404, detail="学生不存在")
    return UnifiedResponse(data={"student_id": req.student_id, "group_id": req.group_id})


@teacher_router.get("/groups/{group_id}", response_model=UnifiedResponse)
def get_group_detail_endpoint(group_id: str, db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    """获取分组详情——成员列表 + 组内统计。"""
    from app.crud import get_group_detail
    data = get_group_detail(db, group_id, str(current_user.id))
    if not data:
        raise HTTPException(status_code=404, detail="分组不存在")
    return UnifiedResponse(data=data)


@teacher_router.delete("/groups/{group_id}", response_model=UnifiedResponse)
def delete_group_endpoint(group_id: str, db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    """删除分组，组成员自动取消分组。"""
    from app.crud import delete_teacher_group
    ok = delete_teacher_group(db, group_id, str(current_user.id))
    if not ok:
        raise HTTPException(status_code=404, detail="分组不存在")
    return UnifiedResponse(data={"deleted": True})


@teacher_router.post("/students/batch-assign", response_model=UnifiedResponse)
def batch_assign_endpoint(req: BatchAssignRequest, db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    """批量分配学生到分组。"""
    from app.crud import batch_assign_groups
    if not req.student_ids:
        raise HTTPException(status_code=400, detail="请选择至少一名学生")
    changed = batch_assign_groups(db, req.student_ids, str(current_user.id), req.group_id)
    return UnifiedResponse(data={"changed": changed})


@teacher_router.get("/groups-comparison", response_model=UnifiedResponse)
def groups_comparison_endpoint(db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    """获取所有分组的对比数据（正确率/口语/活跃度）。"""
    from app.crud import get_groups_comparison
    data = get_groups_comparison(db, str(current_user.id))
    return UnifiedResponse(data=data)


# ══════════════════════════════════════════════
# Teacher AI routes
# ══════════════════════════════════════════════
teacher_ai_router = APIRouter()


class TeacherAssistantRequest(BaseModel):
    message: str
    history: list[dict] = []
    student_id: str | None = None
    group_id: str | None = None
    thread_id: str | None = None


class TeacherSuggestionRequest(BaseModel):
    pass


class ReportRequest(BaseModel):
    student_id: str


@teacher_ai_router.post("/assistants/teacher/chat", response_model=UnifiedResponse)
async def teacher_assistant_chat(req: TeacherAssistantRequest, current_user: UserModel = Depends(require_teacher_role), db: Session = Depends(get_db)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    thread_id = _ensure_thread(db, req.thread_id, str(current_user.id), "teacher")
    _update_thread_title(db, thread_id, req.message)
    agent = get_teacher_agent()
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": req.message}]},
        config={
            "configurable": {
                "user_id": str(current_user.id),
                "thread_id": thread_id,
            }
        },
    )
    reply = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.type == "ai":
            reply = msg.content
            break
    save_message_to_db(str(current_user.id), thread_id, "user", req.message)
    if reply:
        save_message_to_db(str(current_user.id), thread_id, "assistant", reply)
    return UnifiedResponse(data={"reply": reply, "thread_id": thread_id})


@teacher_ai_router.post("/assistants/teacher/suggestions", response_model=UnifiedResponse)
async def teacher_assistant_suggestions(
    _: TeacherSuggestionRequest,
    current_user: UserModel = Depends(require_teacher_role),
    db: Session = Depends(get_db),
):
    """根据教师当前学情生成建议提示词。"""
    from app.agents import list_my_students, get_student_level_distribution, list_my_groups

    cfg = {"configurable": {"user_id": str(current_user.id)}}

    students_text = "暂无学生"
    level_dist_text = "暂无数据"
    groups_text = "暂无分组"

    try:
        students_text = await list_my_students.ainvoke({}, config=cfg)
    except Exception:
        pass
    try:
        level_dist_text = await get_student_level_distribution.ainvoke({}, config=cfg)
    except Exception:
        pass
    try:
        groups_text = await list_my_groups.ainvoke({}, config=cfg)
    except Exception:
        pass

    prompt = (
        "你是一位 RealEnglish 教师管理助手。请根据以下教师视角的学情数据，生成 4 条建议提示词。\n\n"
        f"学生概况：\n{students_text}\n\n"
        f"等级分布：\n{level_dist_text}\n\n"
        f"分组情况：\n{groups_text}\n\n"
        "要求：\n"
        "1. 覆盖查看学生列表、分析学情、生成报告、分组管理\n"
        "2. 每条建议是一个可直接发送给教师助手的问题，用中文\n"
        "3. 语气专业简洁，每条不超过 30 字\n\n"
        "请严格按 JSON 格式输出，只输出一个字符串数组：\n"
        '["建议1", "建议2", "建议3", "建议4"]'
    )

    try:
        raw = await call_deepseek(prompt, temperature=0.7)
        content = raw.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        suggestions = json.loads(content)
        if not isinstance(suggestions, list):
            suggestions = []
        suggestions = [str(s) for s in suggestions][:5]
    except Exception as e:
        logger.warning(f"生成教师建议失败: {e}")
        suggestions = []

    return UnifiedResponse(data={"suggestions": suggestions})


@teacher_ai_router.post("/assistants/teacher/chat/stream")
async def teacher_assistant_chat_stream(req: TeacherAssistantRequest, current_user: UserModel = Depends(require_teacher_role), db: Session = Depends(get_db)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    thread_id = _ensure_thread(db, req.thread_id, str(current_user.id), "teacher")
    _update_thread_title(db, thread_id, req.message)
    llm = get_llm(temperature=0.6)
    history = await get_thread_messages(str(current_user.id), thread_id)
    full_reply = []
    teacher_tools = [
        get_current_time, list_my_students, get_student_level_distribution,
        get_student_learning_detail, generate_learning_report, generate_group_report,
        list_my_groups, get_group_students_detail, create_task_tool,
        send_announcement_tool, send_group_message_tool, get_task_progress_tool,
        get_group_stats_tool, assign_student_to_group_tool, create_group_tool,
        update_student_level_tool, compare_students, get_weekly_digest,
    ]

    async def event_generator():
        try:
            nonlocal full_reply
            yield json.dumps({"type": "thread_id", "thread_id": thread_id}) + "\n"
            async for evt in stream_agent_response(
                llm=llm,
                tools=teacher_tools,
                system_prompt=TEACHER_AGENT_SYSTEM_PROMPT,
                user_message=req.message,
                history=history,
                user_id=str(current_user.id),
            ):
                if evt.get("type") == "content":
                    full_reply.append(evt["content"])
                yield json.dumps(evt) + "\n"
            save_message_to_db(str(current_user.id), thread_id, "user", req.message)
            ai_text = "".join(full_reply)
            if ai_text:
                save_message_to_db(str(current_user.id), thread_id, "assistant", ai_text)
        except Exception as error:
            logger.error(f"教师助手流式调用失败: {error}")
            yield json.dumps({"type": "error", "message": "AI 服务暂时不可用，请稍后重试。"}) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@teacher_ai_router.post("/teacher/reports/generate", response_model=UnifiedResponse)
async def report_agent_endpoint(req: ReportRequest, _: UserModel = Depends(require_teacher_role)):
    final_state = await report_app.ainvoke({"student_id": req.student_id, "stats": "", "mistakes": "", "activity_trend": "", "narrative_report": ""})
    return UnifiedResponse(data={"student_id": req.student_id, "report": final_state["narrative_report"]})


# ══════════════════════════════════════════════
# Assistant Thread routes — 助手会话管理
# ══════════════════════════════════════════════
assistant_thread_router = APIRouter()


@assistant_thread_router.get("/threads/{thread_id}/messages", response_model=UnifiedResponse)
async def get_thread_history(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """获取指定线程的对话历史（从 SqliteSaver checkpoint 恢复）。"""
    thread = db.query(AssistantThreadModel).filter(
        AssistantThreadModel.id == thread_id,
        AssistantThreadModel.user_id == str(current_user.id),
    ).first()
    if not thread:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = await get_thread_messages(str(current_user.id), thread_id)
    return UnifiedResponse(data={"messages": messages, "thread_title": thread.title})


@assistant_thread_router.get("/threads", response_model=UnifiedResponse)
def list_threads(
    role: str = Query("student"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    threads = db.query(AssistantThreadModel).filter(
        AssistantThreadModel.user_id == str(current_user.id),
        AssistantThreadModel.role == role,
    ).order_by(AssistantThreadModel.updated_at.desc()).all()
    return UnifiedResponse(data={
        "threads": [
            {
                "id": t.id,
                "title": t.title,
                "role": t.role,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in threads
        ]
    })


@assistant_thread_router.post("/threads", response_model=UnifiedResponse)
def create_thread(
    role: str = Query("student"),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    thread = AssistantThreadModel(user_id=str(current_user.id), role=role)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return UnifiedResponse(data={"id": thread.id, "title": thread.title})


@assistant_thread_router.patch("/threads/{thread_id}", response_model=UnifiedResponse)
def rename_thread(
    thread_id: str,
    req: ThreadRenameRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    thread = db.query(AssistantThreadModel).filter(
        AssistantThreadModel.id == thread_id,
        AssistantThreadModel.user_id == str(current_user.id),
    ).first()
    if not thread:
        raise HTTPException(status_code=404, detail="会话不存在")
    thread.title = req.title[:100]
    db.commit()
    return UnifiedResponse(data={"id": thread.id, "title": thread.title})


@assistant_thread_router.delete("/threads/{thread_id}", response_model=UnifiedResponse)
def delete_thread(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    thread = db.query(AssistantThreadModel).filter(
        AssistantThreadModel.id == thread_id,
        AssistantThreadModel.user_id == str(current_user.id),
    ).first()
    if not thread:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete(thread)
    db.commit()
    return UnifiedResponse(data={"deleted": thread_id})


# ══════════════════════════════════════════════
# Free Talk routes — 情景式自由对话
# ══════════════════════════════════════════════
free_talk_router = APIRouter()

FREE_TALK_TOPIC_PROMPT = """你是一位英语教学情景设计师。请为英语学习者设计一个日常生活场景的双人对话练习。

要求：
1. 选择一个真实的日常生活场景（如：餐厅点餐、酒店预订、机场值机、看病、购物退货、问路、面试等）
2. 用中文描述场景背景（30-50字）
3. 设计两个角色：AI 扮演一个角色，学生扮演另一个角色
4. AI 角色先说第一句话，用英语，1-3句即可

请严格按以下 JSON 格式输出，不要任何额外内容：
{
  "topic": "在餐厅点餐",
  "scenario": "你走进一家西餐厅，服务员 Alice 过来迎接你，你需要点餐。",
  "ai_role": "Alice",
  "user_role": "Customer",
  "first_message": "Good evening! Welcome to Bella Italia. I'm Alice, I'll be your server tonight. How many guests are joining us?"
}"""

FREE_TALK_RESPOND_PROMPT = """你正在与一个英语学习者进行情景对话练习。

【场景】
{scenario}

【角色】
- 你：{ai_role}
- 学生：{user_role}

【对话规则】
1. 只用英语回复，保持自然对话节奏
2. 每次回复 1-3 句话，不要过长
3. 如果学生表达有误，在后续回复中自然地使用正确表达方式，不要直接纠错
4. 给学生说话的机会（适当提问）
5. 保持角色身份一致，符合场景设定

【对话历史】
{history}

现在轮到你以 {ai_role} 的身份回复："""

FREE_TALK_EVAL_PROMPT = """你是一位专业的英语口语考官。请评估以下情景对话中学生的表现。

对话场景：{scenario}
学生扮演的角色：{user_role}

学生的所有发言（按时间顺序）：
{utterances}

请从以下维度评分（每项 1-10 分）：
1. participation（参与完成度）：学生是否积极参与对话，完成角色任务
2. grammar（语法准确性）：语法结构是否正确
3. vocabulary（词汇丰富度）：用词是否丰富恰当
4. fluency（表达流畅度）：表达是否自然流畅

请严格按以下 JSON 格式输出，不要任何额外内容：
{{
  "participation": 8,
  "grammar": 7,
  "vocabulary": 6,
  "fluency": 7,
  "summary": "这里写一段 80-120 字的中文总结，描述学生的整体表现、优点和需要改进的地方",
  "suggestions": ["建议1", "建议2", "建议3"]
}}"""


@free_talk_router.post("/start", response_model=UnifiedResponse)
async def start_free_talk(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_student_role),
):
    raw = await call_deepseek(FREE_TALK_TOPIC_PROMPT, temperature=0.7)
    try:
        content = raw.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(content)
    except json.JSONDecodeError:
        data = {
            "topic": "日常英语对话",
            "scenario": "你正在与一位英语母语者进行日常对话。",
            "ai_role": "Sarah",
            "user_role": "You",
            "first_message": "Hi there! How's your day going so far?",
        }

    topic = data.get("topic", "日常英语对话")
    scenario = data.get("scenario", "")
    ai_role = data.get("ai_role", "Sarah")
    user_role = data.get("user_role", "You")
    first_message = data.get("first_message", "Hi! How are you today?")

    conv = FreeConversationModel(
        user_id=str(current_user.id),
        topic=topic,
        scenario=scenario,
        ai_role_name=ai_role,
        user_role_name=user_role,
        status="active",
    )
    db.add(conv)
    db.flush()

    ai_msg = ConversationMessageModel(
        conversation_id=conv.id, role="ai", content=first_message,
    )
    db.add(ai_msg)
    db.commit()
    db.refresh(conv)

    return UnifiedResponse(data={
        "conversation_id": conv.id,
        "topic": conv.topic,
        "scenario": conv.scenario,
        "ai_role_name": conv.ai_role_name,
        "user_role_name": conv.user_role_name,
        "first_message": first_message,
        "created_at": conv.created_at.isoformat(),
    })


@free_talk_router.post("/{conversation_id}/respond", response_model=UnifiedResponse)
async def respond_free_talk(
    conversation_id: str,
    text: str = Form(None),
    audio: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_student_role),
):
    conv = db.query(FreeConversationModel).filter(
        FreeConversationModel.id == conversation_id,
        FreeConversationModel.user_id == str(current_user.id),
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    if conv.status != "active":
        raise HTTPException(status_code=400, detail="对话已结束")

    user_content = ""
    transcript = None
    audio_url = None

    # 语音输入
    if audio and audio.filename:
        audio_data = await audio.read()
        pcm_data = _convert_webm_to_pcm(audio_data)
        api_key = getattr(settings, "xf_api_key", "")
        api_secret = getattr(settings, "xf_api_secret", "")
        app_id = getattr(settings, "xf_appid", "")
        if all([api_key, api_secret, app_id]):
            transcript = await recognize_speech(pcm_data, app_id, api_key, api_secret)
            user_content = transcript
        else:
            user_content = ""
        if not user_content:
            return UnifiedResponse(code=400, message="未识别到有效语音，请重试", data=None)

        conv.voice_used = True
        try:
            filename = f"speaking/{current_user.id}/{uuid.uuid4().hex}.webm"
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            audio_url = await upload_to_oss(tmp_path, filename)
        except Exception as e:
            logger.error(f"音频保存失败: {e}")

    # 文本输入
    elif text:
        user_content = text.strip()
        if not user_content:
            raise HTTPException(status_code=400, detail="输入内容不能为空")
    else:
        raise HTTPException(status_code=400, detail="请提供文字或语音输入")

    # 保存用户消息
    user_msg = ConversationMessageModel(
        conversation_id=conv.id,
        role="user",
        content=user_content,
        audio_url=audio_url,
    )
    db.add(user_msg)
    db.flush()

    # 组装对话历史
    messages = db.query(ConversationMessageModel).filter(
        ConversationMessageModel.conversation_id == conv.id
    ).order_by(ConversationMessageModel.created_at.asc()).all()

    history_lines = []
    for m in messages:
        name = conv.ai_role_name if m.role == "ai" else conv.user_role_name
        history_lines.append(f"{name}: {m.content}")

    prompt = FREE_TALK_RESPOND_PROMPT.format(
        scenario=conv.scenario or "",
        ai_role=conv.ai_role_name or "AI",
        user_role=conv.user_role_name or "You",
        history="\n".join(history_lines[-20:]),
    )

    try:
        reply = await call_deepseek(prompt, temperature=0.6)
    except Exception as e:
        logger.error(f"自由对话 AI 回复失败: {e}")
        reply = "Sorry, I didn't catch that. Could you say it again?"

    ai_msg = ConversationMessageModel(
        conversation_id=conv.id, role="ai", content=reply,
    )
    db.add(ai_msg)
    db.commit()

    return UnifiedResponse(data={
        "reply": reply,
        "transcript": transcript,
        "audio_url": audio_url,
    })


@free_talk_router.post("/{conversation_id}/end", response_model=UnifiedResponse)
async def end_free_talk(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_student_role),
):
    conv = db.query(FreeConversationModel).filter(
        FreeConversationModel.id == conversation_id,
        FreeConversationModel.user_id == str(current_user.id),
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    if conv.status != "active":
        raise HTTPException(status_code=400, detail="对话已结束")

    user_messages = db.query(ConversationMessageModel).filter(
        ConversationMessageModel.conversation_id == conv.id,
        ConversationMessageModel.role == "user",
    ).order_by(ConversationMessageModel.created_at.asc()).all()

    if not user_messages:
        raise HTTPException(status_code=400, detail="没有学生发言，无法评测")

    utterances = []
    for i, m in enumerate(user_messages, 1):
        utterances.append(f'{i}. "{m.content}"')

    eval_prompt = FREE_TALK_EVAL_PROMPT.format(
        scenario=conv.scenario or "",
        user_role=conv.user_role_name or "You",
        utterances="\n".join(utterances),
    )

    try:
        raw = await call_deepseek(eval_prompt, temperature=0.3)
        content = raw.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        result = json.loads(content)
    except Exception as e:
        logger.error(f"评测解析失败: {e}")
        result = {
            "participation": 5, "grammar": 5, "vocabulary": 5, "fluency": 5,
            "summary": "评测服务暂时不可用，请稍后重试。",
            "suggestions": ["多参与口语练习", "关注语法准确性", "尝试使用更丰富的词汇"],
        }

    scores = [
        float(result.get("participation", 0)),
        float(result.get("grammar", 0)),
        float(result.get("vocabulary", 0)),
        float(result.get("fluency", 0)),
    ]
    overall = round(sum(scores) / len(scores), 1)

    evaluation = {
        "participation": scores[0],
        "grammar": scores[1],
        "vocabulary": scores[2],
        "fluency": scores[3],
        "overall": overall,
        "summary": result.get("summary", ""),
        "suggestions": result.get("suggestions", []),
    }

    conv.status = "completed"
    conv.completed_at = beijing_now()
    conv.evaluation_json = evaluation
    conv.feedback = result.get("summary", "")
    db.commit()

    return UnifiedResponse(data={
        "evaluation": evaluation,
        "voice_used": conv.voice_used,
        "message_count": len(user_messages) + len(
            db.query(ConversationMessageModel).filter(
                ConversationMessageModel.conversation_id == conv.id,
                ConversationMessageModel.role == "ai",
            ).all()
        ),
        "user_turn_count": len(user_messages),
    })


@free_talk_router.get("/{conversation_id}", response_model=UnifiedResponse)
async def get_free_talk(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_student_role),
):
    conv = db.query(FreeConversationModel).filter(
        FreeConversationModel.id == conversation_id,
        FreeConversationModel.user_id == str(current_user.id),
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = db.query(ConversationMessageModel).filter(
        ConversationMessageModel.conversation_id == conv.id,
    ).order_by(ConversationMessageModel.created_at.asc()).all()

    return UnifiedResponse(data={
        "conversation": {
            "id": conv.id,
            "topic": conv.topic,
            "scenario": conv.scenario,
            "ai_role_name": conv.ai_role_name,
            "user_role_name": conv.user_role_name,
            "status": conv.status,
            "voice_used": conv.voice_used,
            "evaluation_json": conv.evaluation_json,
            "feedback": conv.feedback,
            "created_at": conv.created_at.isoformat(),
            "completed_at": conv.completed_at.isoformat() if conv.completed_at else None,
        },
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "audio_url": m.audio_url,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    })


# ══════════════════════════════════════════════
# Router aggregation
# ══════════════════════════════════════════════
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(system_router, tags=["System"])
api_router.include_router(clip_router, prefix="/clips", tags=["Clips"])
# ══════════════════════════════════════════════
# Communication routers
# ══════════════════════════════════════════════
comm_router = APIRouter(dependencies=[Depends(require_teacher_role)])


@comm_router.get("/announcements", response_model=UnifiedResponse)
def list_announcements(db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import get_teacher_announcements
    items, total = get_teacher_announcements(db, str(current_user.id))
    data = [{"id": a.id, "teacher_id": a.teacher_id, "title": a.title, "content": a.content,
             "target_type": a.target_type, "target_group_id": a.target_group_id,
             "is_pinned": a.is_pinned,
             "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else None} for a in items]
    return UnifiedResponse(data={"items": data, "total": total})


@comm_router.post("/announcements", response_model=UnifiedResponse)
def create_announcement(req: AnnouncementCreate, db: Session = Depends(get_db),
                        current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import create_announcement_crud
    ann = create_announcement_crud(db, str(current_user.id), req.title, req.content,
                                   req.target_type, req.target_group_id, req.is_pinned)
    return UnifiedResponse(data={"id": ann.id, "title": ann.title})


@comm_router.put("/announcements/{ann_id}", response_model=UnifiedResponse)
def edit_announcement(ann_id: str, req: AnnouncementUpdate, db: Session = Depends(get_db),
                      current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import update_announcement_crud
    ann = update_announcement_crud(db, ann_id, str(current_user.id), title=req.title,
                                   content=req.content, target_type=req.target_type,
                                   target_group_id=req.target_group_id)
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    return UnifiedResponse(data={"id": ann.id})


@comm_router.delete("/announcements/{ann_id}", response_model=UnifiedResponse)
def delete_announcement(ann_id: str, db: Session = Depends(get_db),
                        current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import delete_announcement_crud
    ok = delete_announcement_crud(db, ann_id, str(current_user.id))
    if not ok:
        raise HTTPException(status_code=404, detail="公告不存在")
    return UnifiedResponse(data={"deleted": True})


@comm_router.patch("/announcements/{ann_id}/pin", response_model=UnifiedResponse)
def pin_announcement(ann_id: str, db: Session = Depends(get_db),
                     current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import update_announcement_crud
    from app.models import AnnouncementModel
    ann = db.query(AnnouncementModel).filter(AnnouncementModel.id == ann_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    ann.is_pinned = not ann.is_pinned
    db.commit()
    return UnifiedResponse(data={"is_pinned": ann.is_pinned})


@comm_router.post("/messages/read", response_model=UnifiedResponse)
def teacher_mark_read(req: MarkReadRequest, db: Session = Depends(get_db),
                       current_user: UserModel = Depends(require_teacher_role)):
    """教师批量标记消息已读。"""
    from app.models import MessageModel
    if req.message_ids:
        db.query(MessageModel).filter(MessageModel.id.in_(req.message_ids)).update(
            {MessageModel.is_read: True}, synchronize_session=False
        )
        db.commit()
    return UnifiedResponse(data={"marked": len(req.message_ids)})


@comm_router.get("/messages/poll", response_model=UnifiedResponse)
def teacher_messages_poll(since: str = Query(""), student_id: str = Query(None),
                           group_id: str = Query(None), db: Session = Depends(get_db),
                           current_user: UserModel = Depends(require_teacher_role)):
    """教师端时间戳轮询，支持按学生/分组过滤。"""
    if not since:
        return UnifiedResponse(data={"items": [], "has_new": False})
    from app.models import MessageModel, UserModel as UM
    tid = str(current_user.id)
    try:
        from datetime import datetime as dt
        clean_since = since.replace("Z", "+00:00")
        since_dt = dt.fromisoformat(clean_since)
        if since_dt.tzinfo is not None:
            since_dt = since_dt.replace(tzinfo=None)
        q = db.query(MessageModel).filter(MessageModel.created_at > since_dt)
        if student_id:
            # 只查该学生与教师的私聊
            q = q.filter(
                ((MessageModel.sender_id == tid) & (MessageModel.receiver_id == student_id)) |
                ((MessageModel.sender_id == student_id) & (MessageModel.receiver_id == tid))
            )
        elif group_id:
            q = q.filter(MessageModel.group_id == group_id)
        else:
            q = q.filter(
                (MessageModel.receiver_id == tid) | (MessageModel.sender_id == tid)
            )
        items = q.order_by(MessageModel.created_at.asc()).all()
        data = [_msg_to_dict_teacher(db, m) for m in items]
        return UnifiedResponse(data={"items": data, "has_new": len(data) > 0})
    except ValueError:
        return UnifiedResponse(data={"items": [], "has_new": False})


@comm_router.get("/messages/received", response_model=UnifiedResponse)
def list_received_messages(db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import get_received_messages
    from app.models import UserModel as UM
    items, total = get_received_messages(db, str(current_user.id))
    data = []
    for m in items:
        sender = db.query(UM).filter(UM.id == m.sender_id).first()
        data.append({"id": m.id, "sender_id": m.sender_id, "sender_name": sender.username if sender else "",
                     "receiver_id": m.receiver_id, "subject": m.subject, "content": m.content,
                     "is_read": m.is_read, "parent_id": m.parent_id,
                     "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else None})
    return UnifiedResponse(data={"items": data, "total": total})


@comm_router.get("/messages/sent", response_model=UnifiedResponse)
def list_sent_messages(db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import get_sent_messages
    items, total = get_sent_messages(db, str(current_user.id))
    data = [{"id": m.id, "sender_id": m.sender_id, "receiver_id": m.receiver_id,
             "subject": m.subject, "content": m.content, "is_read": m.is_read,
             "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else None} for m in items]
    return UnifiedResponse(data={"items": data, "total": total})


@comm_router.get("/messages/with/{student_id}", response_model=UnifiedResponse)
def get_messages_with_student(student_id: str, db: Session = Depends(get_db),
                               current_user: UserModel = Depends(require_teacher_role)):
    """获取教师与指定学生的聊天历史。"""
    from app.models import MessageModel
    teacher_id = str(current_user.id)
    messages = db.query(MessageModel).filter(
        ((MessageModel.sender_id == teacher_id) & (MessageModel.receiver_id == student_id)) |
        ((MessageModel.sender_id == student_id) & (MessageModel.receiver_id == teacher_id))
    ).order_by(MessageModel.created_at.asc()).all()

    from app.models import UserModel as UM
    data = []
    for m in messages:
        sender = db.query(UM).filter(UM.id == m.sender_id).first()
        data.append({
            "id": m.id, "sender_id": m.sender_id, "sender_name": sender.username if sender else "",
            "receiver_id": m.receiver_id, "content": m.content,
            "is_read": m.is_read,
            "created_at": m.created_at.strftime("%m-%d %H:%M") if m.created_at else None,
        })
    return UnifiedResponse(data=data)


@comm_router.get("/messages/group/{group_id}", response_model=UnifiedResponse)
def get_group_messages(group_id: str, db: Session = Depends(get_db),
                        current_user: UserModel = Depends(require_teacher_role)):
    """获取群发到指定分组的所有消息。"""
    from app.models import MessageModel
    messages = db.query(MessageModel).filter(
        MessageModel.group_id == group_id
    ).order_by(MessageModel.created_at.desc()).limit(100).all()

    from app.models import UserModel as UM
    data = []
    for m in reversed(messages):
        sender = db.query(UM).filter(UM.id == m.sender_id).first()
        data.append({
            "id": m.id, "sender_id": m.sender_id, "sender_name": sender.username if sender else "",
            "content": m.content, "is_read": m.is_read,
            "created_at": m.created_at.strftime("%m-%d %H:%M") if m.created_at else None,
        })
    return UnifiedResponse(data=data)


@comm_router.get("/unread-count", response_model=UnifiedResponse)
def teacher_unread_count(db: Session = Depends(get_db),
                          current_user: UserModel = Depends(require_teacher_role)):
    """返回教师的未读消息数。"""
    from app.models import MessageModel
    tid = str(current_user.id)
    unread = db.query(func.count(MessageModel.id)).filter(
        MessageModel.receiver_id == tid, MessageModel.is_read.is_(False)
    ).scalar() or 0
    return UnifiedResponse(data={"messages": unread})


@comm_router.get("/conversations", response_model=UnifiedResponse)
def get_conversation_list(db: Session = Depends(get_db),
                           current_user: UserModel = Depends(require_teacher_role)):
    """获取教师的会话列表：含所有自己分组下的学生+所有分组。"""
    from app.models import MessageModel, TeacherGroupModel, UserModel as UM
    teacher_id = str(current_user.id)

    conversations = []

    # 获取该教师分组下的所有学生
    my_groups = db.query(TeacherGroupModel.id).filter(TeacherGroupModel.teacher_id == teacher_id).all()
    my_group_ids = [g[0] for g in my_groups]
    if my_group_ids:
        students = db.query(UM).filter(UM.role == "student", UM.group_id.in_(my_group_ids)).all()
        for stu in students:
            unread = db.query(func.count(MessageModel.id)).filter(
                MessageModel.sender_id == str(stu.id), MessageModel.receiver_id == teacher_id,
                MessageModel.is_read.is_(False)
            ).scalar() or 0
            conversations.append({
                "type": "student", "id": str(stu.id), "name": stu.username or "学生",
                "unread": unread, "avatar": stu.avatar,
            })

    # 添加分组会话
    my_groups = db.query(TeacherGroupModel).filter(TeacherGroupModel.teacher_id == teacher_id).all()
    for g in my_groups:
        conversations.append({
            "type": "group", "id": str(g.id), "name": g.name, "unread": 0,
        })

    return UnifiedResponse(data=conversations)


@comm_router.post("/messages/send", response_model=UnifiedResponse)
def send_message_endpoint(req: MessageSend, db: Session = Depends(get_db),
                          current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import send_message_crud
    msg = send_message_crud(db, str(current_user.id), req.content, req.receiver_id,
                            req.group_id, req.subject, req.parent_id)
    return UnifiedResponse(data={"id": msg.id})


# Task router
task_router = APIRouter(dependencies=[Depends(require_teacher_role)])


@task_router.get("", response_model=UnifiedResponse)
def list_tasks(group_id: str | None = Query(None), status: str | None = Query(None),
               db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import get_teacher_tasks
    items, total = get_teacher_tasks(db, str(current_user.id), group_id, status)
    return UnifiedResponse(data={"items": items, "total": total})


@task_router.post("", response_model=UnifiedResponse)
def create_task(req: TaskCreate, db: Session = Depends(get_db),
                current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import create_task_crud
    from datetime import datetime as dt
    kwargs = {"description": req.description, "target_type": req.target_type,
              "target_group_id": req.target_group_id,
              "practice_goal": req.practice_goal, "speaking_goal": req.speaking_goal,
              "free_talk_goal": req.free_talk_goal, "clip_goal": req.clip_goal,
              "accuracy_goal": req.accuracy_goal}
    if req.deadline:
        try:
            kwargs["deadline"] = dt.fromisoformat(req.deadline)
        except ValueError:
            pass
    task = create_task_crud(db, str(current_user.id), req.title, **kwargs)
    return UnifiedResponse(data={"id": task.id, "title": task.title})


@task_router.get("/{task_id}", response_model=UnifiedResponse)
def get_task(task_id: str, db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import get_task_detail
    data = get_task_detail(db, task_id, str(current_user.id))
    if not data:
        raise HTTPException(status_code=404, detail="任务不存在")
    return UnifiedResponse(data=data)


@task_router.put("/{task_id}", response_model=UnifiedResponse)
def edit_task(task_id: str, req: TaskUpdate, db: Session = Depends(get_db),
              current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import update_task_crud
    from datetime import datetime as dt
    kwargs = {"title": req.title, "description": req.description,
              "practice_goal": req.practice_goal, "speaking_goal": req.speaking_goal,
              "free_talk_goal": req.free_talk_goal, "clip_goal": req.clip_goal,
              "accuracy_goal": req.accuracy_goal}
    if req.deadline:
        try:
            kwargs["deadline"] = dt.fromisoformat(req.deadline)
        except ValueError:
            pass
    task = update_task_crud(db, task_id, str(current_user.id), **kwargs)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return UnifiedResponse(data={"id": task.id})


@task_router.delete("/{task_id}", response_model=UnifiedResponse)
def delete_task(task_id: str, db: Session = Depends(get_db), current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import delete_task_crud
    ok = delete_task_crud(db, task_id, str(current_user.id))
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在")
    return UnifiedResponse(data={"deleted": True})


@task_router.patch("/{task_id}/status", response_model=UnifiedResponse)
def change_task_status(task_id: str, db: Session = Depends(get_db),
                       current_user: UserModel = Depends(require_teacher_role)):
    from app.crud import update_task_crud
    from app.models import TaskModel
    task = db.query(TaskModel).filter(TaskModel.id == task_id, TaskModel.teacher_id == str(current_user.id)).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    new_status = "completed" if task.status == "active" else "active"
    task.status = new_status
    db.commit()
    return UnifiedResponse(data={"status": new_status})


# Student interaction router
student_comm_router = APIRouter(dependencies=[Depends(require_bound_student)])


@student_comm_router.get("/announcements", response_model=UnifiedResponse)
def student_announcements(db: Session = Depends(get_db), current_user: UserModel = Depends(require_student_role)):
    from app.crud import get_student_announcements
    items, total = get_student_announcements(db, str(current_user.id))
    data = [{"id": a.id, "title": a.title, "content": a.content,
             "is_pinned": a.is_pinned,
             "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else None} for a in items]
    return UnifiedResponse(data={"items": data, "total": total})


def _student_message_query(db: Session, student_id: str, since: str | None = None):
    """构建学生消息查询（含私聊+分组消息），可选时间过滤。"""
    from app.models import MessageModel
    student = db.query(UserModel).filter(UserModel.id == student_id).first()
    group_id = student.group_id if student else None
    conditions = [
        # 私聊：学生是发送者或接收者
        ((MessageModel.sender_id == student_id) | (MessageModel.receiver_id == student_id)) & (MessageModel.group_id.is_(None)),
    ]
    if group_id:
        # 群聊：发到该分组的消息
        conditions.append(MessageModel.group_id == group_id)
    from sqlalchemy import or_
    q = db.query(MessageModel).filter(or_(*conditions))
    if since:
        try:
            from datetime import datetime as dt
            clean = since.replace("Z", "+00:00")
            since_dt = dt.fromisoformat(clean)
            if since_dt.tzinfo is not None:
                since_dt = since_dt.replace(tzinfo=None)
            q = q.filter(MessageModel.created_at > since_dt)
        except ValueError:
            pass
    return q.order_by(MessageModel.created_at.asc())


@student_comm_router.get("/messages", response_model=UnifiedResponse)
def student_messages(db: Session = Depends(get_db), current_user: UserModel = Depends(require_student_role)):
    """返回学生相关的所有消息（私聊+群聊，按时间升序）。"""
    from app.models import UserModel as UM
    items = _student_message_query(db, str(current_user.id)).all()
    data = [_msg_to_dict(db, m) for m in items]
    return UnifiedResponse(data={"items": data, "total": len(data)})


@student_comm_router.get("/messages/poll", response_model=UnifiedResponse)
def student_messages_poll(since: str = Query(""), db: Session = Depends(get_db),
                           current_user: UserModel = Depends(require_student_role)):
    """时间戳轮询——只返回 since 之后的新消息。"""
    if not since:
        return UnifiedResponse(data={"items": [], "has_new": False})
    items = _student_message_query(db, str(current_user.id), since=since).all()
    data = [_msg_to_dict(db, m) for m in items]
    return UnifiedResponse(data={"items": data, "has_new": len(data) > 0})


class MarkReadRequest(BaseModel):
    message_ids: list[str] = []


@student_comm_router.post("/messages/read", response_model=UnifiedResponse)
def student_mark_read(req: MarkReadRequest, db: Session = Depends(get_db),
                       current_user: UserModel = Depends(require_student_role)):
    """批量标记消息已读。"""
    from app.models import MessageModel
    ids = req.message_ids
    if ids:
        db.query(MessageModel).filter(MessageModel.id.in_(ids)).update(
            {MessageModel.is_read: True}, synchronize_session=False
        )
        db.commit()
    return UnifiedResponse(data={"marked": len(ids)})


@student_comm_router.get("/unread-count", response_model=UnifiedResponse)
def student_unread_count(db: Session = Depends(get_db),
                          current_user: UserModel = Depends(require_student_role)):
    """返回学生的未读消息数和活跃任务数。"""
    from app.models import MessageModel, TaskProgressModel
    sid = str(current_user.id)
    # 未读私聊
    unread_msgs = db.query(func.count(MessageModel.id)).filter(
        MessageModel.receiver_id == sid, MessageModel.is_read.is_(False)
    ).scalar() or 0
    active_tasks = db.query(func.count(TaskProgressModel.id)).filter(
        TaskProgressModel.student_id == sid, TaskProgressModel.is_completed.is_(False)
    ).scalar() or 0
    return UnifiedResponse(data={"messages": unread_msgs, "tasks": active_tasks})


@student_comm_router.post("/messages", response_model=UnifiedResponse)
def student_send_message(req: MessageSend, db: Session = Depends(get_db),
                         current_user: UserModel = Depends(require_student_role)):
    from app.crud import send_message_crud
    from app.models import TeacherGroupModel
    receiver_id = req.receiver_id
    group_id = req.group_id
    student = db.query(UserModel).filter(UserModel.id == str(current_user.id)).first()
    # 自动路由：若未指定接收人和分组，查找教师作为接收人
    if not receiver_id and not group_id:
        if student and student.group_id:
            tg = db.query(TeacherGroupModel).filter(TeacherGroupModel.id == student.group_id).first()
            if tg:
                receiver_id = tg.teacher_id
    # 若指定了 group_id（群聊），使用学生自己的 group_id
    if group_id and student and student.group_id:
        group_id = student.group_id
    msg = send_message_crud(db, str(current_user.id), req.content, receiver_id,
                            group_id, req.subject, req.parent_id)
    return UnifiedResponse(data={"id": msg.id, "created_at": msg.created_at.isoformat() if msg.created_at else None})


def _msg_to_dict(db: Session, m) -> dict:
    """MessageModel → 前端字典。"""
    from app.models import UserModel as UM
    sender = db.query(UM).filter(UM.id == m.sender_id).first()
    return {
        "id": m.id, "sender_id": m.sender_id, "sender_name": sender.username if sender else "",
        "content": m.content, "is_read": m.is_read, "group_id": m.group_id,
        "created_at": m.created_at.strftime("%m-%d %H:%M") if m.created_at else None,
    }


def _msg_to_dict_teacher(db: Session, m) -> dict:
    from app.models import UserModel as UM
    sender = db.query(UM).filter(UM.id == m.sender_id).first()
    return {
        "id": m.id, "sender_id": m.sender_id, "sender_name": sender.username if sender else "",
        "content": m.content, "is_read": m.is_read,
        "created_at": m.created_at.strftime("%m-%d %H:%M") if m.created_at else None,
    }


@student_comm_router.get("/group-info", response_model=UnifiedResponse)
def student_group_info_endpoint(db: Session = Depends(get_db), current_user: UserModel = Depends(require_student_role)):
    """返回学生所属分组的名称和基本信息。"""
    from app.models import TeacherGroupModel
    student = db.query(UserModel).filter(UserModel.id == str(current_user.id)).first()
    if not student or not student.group_id:
        return UnifiedResponse(data={"group_name": "未分组", "member_count": 0})
    group = db.query(TeacherGroupModel).filter(TeacherGroupModel.id == student.group_id).first()
    member_count = db.query(func.count(UserModel.id)).filter(
        UserModel.group_id == student.group_id, UserModel.role == "student"
    ).scalar() or 0
    return UnifiedResponse(data={
        "group_name": group.name if group else "未分组",
        "description": group.description if group else None,
        "member_count": member_count,
    })


@student_comm_router.get("/tasks", response_model=UnifiedResponse)
def student_tasks(db: Session = Depends(get_db), current_user: UserModel = Depends(require_student_role)):
    from app.crud import get_student_tasks
    tasks = get_student_tasks(db, str(current_user.id))
    return UnifiedResponse(data=tasks)


api_router.include_router(speaking_router, prefix="/speaking", tags=["Speaking"])
api_router.include_router(tts_router, prefix="/tts", tags=["TTS"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(student_router, tags=["Student Learning"])
api_router.include_router(teacher_router, prefix="/teacher", tags=["Teacher"])
api_router.include_router(teacher_ai_router, tags=["Teacher AI"])
api_router.include_router(free_talk_router, prefix="/free-talk", tags=["Free Talk"])
api_router.include_router(assistant_thread_router, prefix="/assistants", tags=["Assistant Threads"])
api_router.include_router(comm_router, prefix="/teacher/communication", tags=["Communication"])
api_router.include_router(task_router, prefix="/teacher/tasks", tags=["Tasks"])
api_router.include_router(student_comm_router, prefix="/student/interactions", tags=["Interactions"])
