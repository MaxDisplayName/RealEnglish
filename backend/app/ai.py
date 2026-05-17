import asyncio
import base64
import hashlib
import hmac
import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse, urlencode, quote

import httpx
import websockets

from app.config import settings
from app.time_utils import beijing_now


def _gmtime_date() -> str:
    """返回讯飞 API 签名所需的 GMT 时间字符串（必须是真正的 UTC 时间）。"""
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
# DeepSeek API Client
# ══════════════════════════════════════════════
def _build_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}


def _build_payload(messages: list[dict], temperature: float, stream: bool = False) -> dict:
    return {"model": "deepseek-chat", "messages": messages, "temperature": temperature, "stream": stream}


async def call_deepseek(prompt: str, temperature: float = 0.6, max_retries: int = 3) -> str:
    messages = [{"role": "user", "content": prompt}]
    last_error = None
    url = f"{settings.deepseek_api_base}/chat/completions"
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=_build_headers(), json=_build_payload(messages, temperature))
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except (httpx.TimeoutException, httpx.HTTPStatusError) as error:
            last_error = error
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            continue
    raise RuntimeError(f"DeepSeek API 调用失败，重试 {max_retries} 次后仍错误: {last_error}")


async def stream_deepseek_messages(messages: list[dict], temperature: float = 0.7):
    url = f"{settings.deepseek_api_base}/chat/completions"
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=60.0)) as client:
        async with client.stream("POST", url, headers=_build_headers(), json=_build_payload(messages, temperature, stream=True)) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                content = json.loads(data)["choices"][0].get("delta", {}).get("content", "")
                if content:
                    yield content


# ══════════════════════════════════════════════
# Question Generator
# ══════════════════════════════════════════════
PART2_PROMPT_TEMPLATE = """你是一个托业听力出题官。请根据以下对话，生成 {count} 个 Part2 问答题（即一个问题，对应三个回答选项）。

对话内容：
{dialogue}

要求：
- 问题必须基于对话中的关键信息。
- 三个选项用英文写出，其中只有一个正确。
- 输出必须是严格的 JSON 数组格式，每个元素包含以下字段：
  question: 问题（英文）
  options: 三个选项（英文数组）
  answer: 正确选项的索引（0, 1, 2）
  explanation: 中文解析

输出 JSON：
"""


async def generate_questions_via_api(dialogue_text: str, difficulty: str = "B", count: int = 3) -> list[dict]:
    prompt = PART2_PROMPT_TEMPLATE.format(dialogue=dialogue_text, count=count)
    raw = await call_deepseek(prompt, temperature=0.6)
    return _parse_questions(raw, count)


def _parse_questions(raw_text: str, expected_count: int) -> list[dict]:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"无法解析 DeepSeek 返回内容为 JSON: {text[:200]}")
    if not isinstance(data, list):
        raise ValueError(f"期望返回数组，实际返回: {type(data)}")
    required_fields = {"question", "options", "answer", "explanation"}
    valid_questions = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if not required_fields.issubset(item.keys()):
            continue
        if not isinstance(item["options"], list) or len(item["options"]) != 3:
            continue
        if not isinstance(item["answer"], int) or item["answer"] not in (0, 1, 2):
            continue
        valid_questions.append(item)
    if not valid_questions:
        raise ValueError("所有生成的题目均未通过字段校验")
    logger.info(f"成功生成 {len(valid_questions)} 道题目 (期望 {expected_count} 道)")
    return valid_questions


# ══════════════════════════════════════════════
# Dialogue Translation (DeepSeek)
# ══════════════════════════════════════════════
_translation_cache: dict[str, str] = {}


async def translate_dialogue(text: str) -> str:
    """将英文对话文本翻译为中文，带简单内存缓存。"""
    cache_key = text[:120]
    if cache_key in _translation_cache:
        return _translation_cache[cache_key]

    prompt = (
        "将以下英文影视对话翻译为自然的中文口语。保持原文的 [角色名] 格式，每个角色说的话单独一行。"
        "只输出译文，不要任何解释：\n\n" + text
    )
    try:
        result = await call_deepseek(prompt, temperature=0.3)
        _translation_cache[cache_key] = result.strip()
        return result.strip()
    except Exception:
        return ""


# ══════════════════════════════════════════════
# 讯飞 Speech Evaluation
# ══════════════════════════════════════════════
DEFAULT_SCORE = {"total_score": 3.5, "accuracy": 3.5, "fluency": 3.5, "integrity": 3.5}
CHUNK_SIZE = 1280


async def evaluate_audio(pcm_data: bytes, reference_text: str, app_id: str, api_key: str, api_secret: str) -> dict:
    ws_url = _build_eval_ws_url(api_key, api_secret)
    text = "﻿[content]\n" + reference_text
    try:
        async with websockets.connect(ws_url) as ws:
            first = {"common": {"app_id": app_id}, "business": {"cmd": "ssb", "sub": "ise", "ent": "en_vip", "category": "read_sentence", "ttp_skip": True, "text": text, "tte": "utf-8", "rstcd": "utf8", "auf": "audio/L16;rate=16000", "aue": "raw"}, "data": {"status": 0}}
            await ws.send(json.dumps(first))
            total = len(pcm_data)
            for off in range(0, total, CHUNK_SIZE):
                chunk = pcm_data[off:off + CHUNK_SIZE]
                is_last = (off + CHUNK_SIZE) >= total
                aus = 1 if off == 0 else (4 if is_last else 2)
                status = 2 if is_last else 1
                frame = {"common": {"app_id": app_id}, "business": {"cmd": "auw", "aus": aus, "aue": "raw"}, "data": {"status": status, "data": base64.b64encode(chunk).decode("utf-8")}}
                await ws.send(json.dumps(frame))
                if is_last:
                    break
                await asyncio.sleep(0.04)
            while True:
                msg = await ws.recv()
                resp = json.loads(msg)
                if resp.get("code") != 0:
                    logger.error("讯飞评测返回错误: code=%s, message=%s", resp.get("code"), resp.get("message"))
                    break
                data = resp.get("data", {})
                if data.get("status") == 2:
                    return _parse_eval_result(data)
    except Exception as e:
        logger.error("讯飞评测 WebSocket 调用失败: %s", e)
    return dict(DEFAULT_SCORE)


def _build_eval_ws_url(api_key: str, api_secret: str) -> str:
    host_url = "wss://ise-api.xfyun.cn/v2/open-ise"
    parsed = urlparse(host_url)
    date = _gmtime_date()
    sign_origin = f"host: {parsed.hostname}\ndate: {date}\nGET {parsed.path} HTTP/1.1"
    signature_sha = hmac.new(api_secret.encode("utf-8"), sign_origin.encode("utf-8"), digestmod=hashlib.sha256).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    auth_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
    authorization = base64.b64encode(auth_origin.encode("utf-8")).decode("utf-8")
    params = {"host": parsed.hostname, "date": date, "authorization": authorization}
    return f"{host_url}?{urlencode(params, quote_via=quote)}"


def _parse_eval_result(data: dict) -> dict:
    try:
        raw = data.get("data", "")
        if not raw:
            return dict(DEFAULT_SCORE)
        xml_str = base64.b64decode(raw).decode("utf-8")
        root = ET.fromstring(xml_str)
        for elem in root.iter():
            if elem.tag in ("read_sentence", "read_chapter") and elem.get("total_score"):
                return {"total_score": round(float(elem.get("total_score", 0)), 1), "accuracy": round(float(elem.get("accuracy_score", 0)), 1), "fluency": round(float(elem.get("fluency_score", 0)), 1), "integrity": round(float(elem.get("integrity_score", 0)), 1)}
        logger.warning("讯飞评测 XML 中未找到 total_score 属性")
    except Exception as e:
        logger.error("讯飞评测结果解析失败: %s", e)
    return dict(DEFAULT_SCORE)


# ══════════════════════════════════════════════
# 讯飞大模型多语种语音识别 (IAT)
# ══════════════════════════════════════════════
IAT_HOST = "iat.cn-huabei-1.xf-yun.com"
IAT_PATH = "/v1"
IAT_CHUNK_SIZE = 1280


def _build_iat_ws_url(api_key: str, api_secret: str) -> str:
    host_url = f"wss://{IAT_HOST}{IAT_PATH}"
    parsed = urlparse(host_url)
    date = _gmtime_date()
    sign_origin = f"host: {parsed.hostname}\ndate: {date}\nGET {parsed.path} HTTP/1.1"
    signature_sha = hmac.new(api_secret.encode("utf-8"), sign_origin.encode("utf-8"), digestmod=hashlib.sha256).digest()
    signature = base64.b64encode(signature_sha).decode("utf-8")
    auth_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
    authorization = base64.b64encode(auth_origin.encode("utf-8")).decode("utf-8")
    params = {"host": parsed.hostname, "date": date, "authorization": authorization}
    return f"{host_url}?{urlencode(params, quote_via=quote)}"


async def recognize_speech(pcm_data: bytes, app_id: str, api_key: str, api_secret: str, language: str = "en") -> str:
    """调用讯飞大模型多语种语音识别，返回识别文本。"""
    ws_url = _build_iat_ws_url(api_key, api_secret)
    try:
        async with websockets.connect(ws_url) as ws:
            # 首帧：发送参数 + 第一包音频
            total = len(pcm_data)
            first_chunk = pcm_data[:IAT_CHUNK_SIZE]
            first_frame = {
                "header": {"app_id": app_id, "status": 0},
                "parameter": {
                    "iat": {
                        "domain": "slm",
                        "language": "mul_cn",
                        "accent": "mandarin",
                        "ln": language,
                        "result": {"encoding": "utf8", "compress": "raw", "format": "json"},
                    }
                },
                "payload": {
                    "audio": {
                        "encoding": "raw",
                        "sample_rate": 16000,
                        "channels": 1,
                        "bit_depth": 16,
                        "seq": 0,
                        "status": 0,
                        "audio": base64.b64encode(first_chunk).decode("utf-8"),
                    }
                },
            }
            await ws.send(json.dumps(first_frame))

            # 中间帧 + 末帧
            seq = 1
            for off in range(IAT_CHUNK_SIZE, total, IAT_CHUNK_SIZE):
                chunk = pcm_data[off:off + IAT_CHUNK_SIZE]
                is_last = (off + IAT_CHUNK_SIZE) >= total
                status = 2 if is_last else 1
                frame = {
                    "header": {"app_id": app_id, "status": status},
                    "payload": {
                        "audio": {
                            "encoding": "raw",
                            "sample_rate": 16000,
                            "status": status,
                            "seq": seq,
                            "audio": base64.b64encode(chunk).decode("utf-8"),
                        }
                    },
                }
                await ws.send(json.dumps(frame))
                seq += 1
                if is_last:
                    break
                await asyncio.sleep(0.04)

            # 特殊情况：如果音频只有一帧，补发末帧
            if total <= IAT_CHUNK_SIZE:
                last_frame = {
                    "header": {"app_id": app_id, "status": 2},
                    "payload": {
                        "audio": {
                            "encoding": "raw",
                            "sample_rate": 16000,
                            "status": 2,
                            "seq": 1,
                            "audio": "",
                        }
                    },
                }
                await ws.send(json.dumps(last_frame))

            # 接收识别结果
            full_text = ""
            final_text = ""
            while True:
                msg = await ws.recv()
                resp = json.loads(msg)
                code = resp.get("header", {}).get("code", -1)
                if code != 0:
                    logger.error("讯飞识别返回错误: code=%s, message=%s", code, resp.get("header", {}).get("message", ""))
                    break
                payload = resp.get("payload", {})
                result = payload.get("result", {})
                text_b64 = result.get("text", "")
                if not text_b64:
                    if result.get("status") == 2 or payload.get("audio", {}).get("status") == 2:
                        break
                    continue
                # 解码 text 字段（base64 → JSON）
                try:
                    text_json = json.loads(base64.b64decode(text_b64).decode("utf-8"))
                except Exception:
                    continue
                # 提取识别词
                words = []
                for ws_item in text_json.get("ws", []):
                    for cw in ws_item.get("cw", []):
                        w = cw.get("w", "")
                        if w:
                            words.append(w)
                full_text += "".join(words)
                if text_json.get("ls") or result.get("status") == 2:
                    final_text = full_text
                    break

            return final_text or full_text
    except Exception as e:
        logger.error("讯飞语音识别调用失败: %s", e)
        return ""


# ══════════════════════════════════════════════
# DeepSeek 自由应答评分
# ══════════════════════════════════════════════
async def evaluate_free_response(question: str, transcript: str) -> dict:
    """使用 DeepSeek 对自由应答进行多维度评分。"""
    if not transcript.strip():
        return {
            "score": 0,
            "content_score": 0,
            "grammar_score": 0,
            "fluency_score": 0,
            "vocabulary_score": 0,
            "feedback": "未检测到有效语音内容，请重新录制。",
        }

    prompt = (
        "你是一位专业的英语口语考官。请根据以下信息对学生的英语回答进行多维度评分。\n\n"
        f"问题：{question}\n"
        f"学生回答（语音识别转写）：{transcript}\n\n"
        "请从以下四个维度评分（每个维度满分5分）：\n"
        "1. 内容相关性 (content): 回答是否切题，逻辑是否清晰\n"
        "2. 语法准确性 (grammar): 语法结构是否正确\n"
        "3. 表达流畅度 (fluency): 表达是否自然流畅\n"
        "4. 词汇丰富度 (vocabulary): 用词是否丰富恰当\n\n"
        "请严格按以下JSON格式输出（不要输出任何其他内容）：\n"
        '{"content": 4.0, "grammar": 3.5, "fluency": 4.0, "vocabulary": 3.5, '
        '"feedback": "这里写一段50-100字的中文评语，先肯定优点，再给1-2条改进建议，以鼓励结尾。"}'
    )
    try:
        raw = await call_deepseek(prompt, temperature=0.3)
        content = raw.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        result = json.loads(content)
        scores = [
            float(result.get("content", 0)),
            float(result.get("grammar", 0)),
            float(result.get("fluency", 0)),
            float(result.get("vocabulary", 0)),
        ]
        avg = round(sum(scores) / len(scores), 1)
        return {
            "score": avg,
            "content_score": scores[0],
            "grammar_score": scores[1],
            "fluency_score": scores[2],
            "vocabulary_score": scores[3],
            "feedback": result.get("feedback", "继续加油！"),
        }
    except Exception as e:
        logger.error("自由应答评分失败: %s", e)
        return {
            "score": 3.0,
            "content_score": 3.0,
            "grammar_score": 3.0,
            "fluency_score": 3.0,
            "vocabulary_score": 3.0,
            "feedback": "评分暂时不可用，但你做得很好！请继续练习。",
        }


# ══════════════════════════════════════════════
# 讯飞 TTS Client
# ══════════════════════════════════════════════
class TTSEngine:
    def __init__(self, app_id: str, api_key: str, api_secret: str):
        self.host_url = "wss://tts-api.xfyun.cn/v2/tts"
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret

    def _build_ws_url(self) -> str:
        ul = urlparse(self.host_url)
        date = _gmtime_date()
        sign_string = f"host: {ul.hostname}\ndate: {date}\nGET {ul.path} HTTP/1.1"
        signature_sha = hmac.new(self.api_secret.encode("utf-8"), sign_string.encode("utf-8"), digestmod=hashlib.sha256).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        auth_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
        authorization = base64.b64encode(auth_origin.encode("utf-8")).decode("utf-8")
        query_params = {"host": ul.hostname, "date": date, "authorization": authorization}
        return f"{self.host_url}?{urlencode(query_params, quote_via=quote)}"

    async def synthesize(self, text: str, voice: str = "x4_xiaoyan", speed: int = 50, volume: int = 50) -> Optional[bytes]:
        ws_url = self._build_ws_url()
        audio_chunks = []
        business = {"aue": "lame", "sfl": 1, "auf": "audio/L16;rate=16000", "vcn": voice, "speed": speed, "volume": volume, "tte": "UTF8", "reg": 2}
        common = {"app_id": self.app_id}
        data = {"status": 2, "text": base64.b64encode(text.encode("utf-8")).decode("utf-8")}
        request_body = {"common": common, "business": business, "data": data}
        try:
            async with websockets.connect(ws_url) as ws:
                await ws.send(json.dumps(request_body))
                while True:
                    msg = await ws.recv()
                    resp = json.loads(msg)
                    if resp.get("code") != 0:
                        break
                    audio_data = resp.get("data", {}).get("audio")
                    if audio_data:
                        audio_chunks.append(base64.b64decode(audio_data))
                    if resp.get("data", {}).get("status") == 2:
                        break
                return b"".join(audio_chunks) if audio_chunks else None
        except Exception:
            return None


async def synthesize_tts(text: str, voice: str = "x4_xiaoyan", speed: int = 50) -> Optional[bytes]:
    api_key = getattr(settings, "xf_api_key", None)
    api_secret = getattr(settings, "xf_api_secret", None)
    app_id = getattr(settings, "xf_appid", None)
    if not all([app_id, api_key, api_secret]):
        return None
    engine = TTSEngine(app_id, api_key, api_secret)
    return await engine.synthesize(text, voice=voice, speed=speed)
