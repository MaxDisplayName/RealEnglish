# RealEnglish 技术实现文档

> 本档面向开发者，详细说明系统的技术架构、关键模块实现、AI 集成方案及部署细节。

## 1. 总体技术架构

```mermaid
graph TB
    subgraph 客户端
        A[Vue3 前端]
    end

    subgraph 网关层
        B[Nginx / Caddy]
    end

    subgraph 后端服务
        C[FastAPI 应用]
        D[Worker (Celery)]
    end

    subgraph 数据层
        E[(PostgreSQL)]
        F[Redis 缓存]
        G[OSS 对象存储]
    end

    subgraph 外部API
        H[DeepSeek API]
        I[科大讯飞 语音评测]
        J[通义万相 文生图]
    end

    A --> B --> C
    C --> D
    C --> E
    C --> F
    C --> G
    C --> H
    C --> I
    C --> J
```

技术选型理由：

FastAPI：高异步性能，支持 WebSocket，自动生成 OpenAPI 文档。

PostgreSQL：支持 JSON 字段存储题目内容，方便灵活查询。

Celery（可选）：用于耗时任务（AI 批量出题、报告生成），避免阻塞 API。

Redis：缓存题目、用户进度、限流计数。

## 2. 核心模块详解

### 2.1 视频集成模块（前端）

目的：在不触及版权风险的前提下，为用户提供稳定的影视片段观看体验。

实现细节：

使用 B 站官方 <iframe> 外链播放器，仅嵌入 url，不存储任何视频文件。

支持起始时间跳转：URL 参数 t={秒}。例如：https://player.bilibili.com/player.html?bvid=BV1yP4y1n7tB&page=1&t=81

由于 B 站 iframe 无法精确控制结束，通过前端监听 timeupdate 事件，若当前播放时间 ≥ 结束时间则调用 postMessage 暂停播放（需等待 B 站播放器 API 支持）或简单提醒用户手动停止。

代码示例（前端组合式函数）：

```javascript
// composables/useBiliPlayer.js
import { ref, onMounted, onUnmounted } from "vue";

export function useBiliPlayer(iframeRef, startSec, endSec) {
  const isPlaying = ref(false);

  const handlePlay = () => {
    // 通过 postMessage 控制播放（B站支持有限的 API）
  };

  onMounted(() => {
    window.addEventListener("message", (event) => {
      // 监听播放进度
    });
  });

  return { isPlaying, handlePlay };
}
```

### 2.2 定级测试模块（后端 + 前端）

算法：根据用户答对的题目数量，映射到 A/B/C 等级。

实现步骤：

考试前从题库中按难度比例抽取 10 题（例如 A:3, B:4, C:3）。

用户答题后，后端计算正确率。

映射规则：

正确率 < 50% → A 级

50% ≤ 正确率 < 75% → B 级

正确率 ≥ 75% → C 级

将等级写入 users 表，并记录本次测试详情。

### 2.3 AI 出题服务（后端）

目标：根据影视片段对话文本，自动生成托业/四六级风格的听力题（Part2 问答题 / Part3 对话题）。

流程：

从数据库读取 dialogue_text（已标注角色）和 summary。

使用 Prompt 模板调用 DeepSeek API（见附录）。

解析返回的 JSON，校验字段完整性。

将题目存入 questions 表，关联 clip_id。

Prompt 设计范例（Part3）：

json
{
"model": "deepseek-chat",
"temperature": 0.6,
"messages": [
{"role": "system", "content": "你是一个托业听力命题专家，输出必须为合法 JSON。"},
{"role": "user", "content": "根据以下对话生成3个多项选择题：\n对话：{marked_dialogue}\n\n每个问题包含题干、4个选项（其中1个正确）、中文解析。输出格式：[{\"question\":\"...\", \"options\":[\"...\",...], \"answer\":0, \"explanation\":\"...\"}]"}
]
}
降级方案：若 API 调用失败或返回格式错误，则使用预先手工编写的备用题目。

### 2.4 口语评测与反馈（后端 + 前端）

已实现基于**科大讯飞语音评测（流式版）**的完整口语练习功能。

#### 流程

1. 前端使用 MediaRecorder 录制音频（`audio/webm;codecs=opus`）。
2. 上传至后端 `POST /api/v1/speaking/evaluate`（FormData: audio + reference_text + mode）。
3. 后端执行：
   - 使用 ffmpeg 将 WebM/Opus 实时转码为 PCM 16kHz/16bit/单声道。
   - 建立 WebSocket 连接至讯飞 ISE API `wss://ise-api.xfyun.cn/v2/open-ise`。
   - 发送 SSB 参数帧（`en_vip` 引擎，`read_sentence` 模式）→ 分片发送 AUW 音频帧（每 40ms 发送 1280B）→ 接收 base64 XML 结果。
   - 解析 XML 提取 `total_score` / `accuracy_score` / `fluency_score` / `integrity_score`（原始 5 分制，前端直接展示）。
   - 调用 DeepSeek 根据评分生成鼓励式中文反馈。
   - 保存录音到本地 storage/（OSS 降级），记录 `speaking_records` 表。
4. 前端展示 4 个维度的评分（总分 / 准确度 / 流畅度 / 完整度）+ AI 教练反馈。

#### 关键源码

- `backend/app/core/speech_eval.py` — WebSocket 连接、鉴权签名、分片上传、XML 解析
- `backend/app/api/v1/speaking.py` — 评测 API 路由、音频转码、AI 反馈生成、记录持久化
- `frontend/src/components/SpeakingRecorder.vue` — 录音控制、5 分制评分展示、AI 反馈展示
- `frontend/src/composables/useRecorder.js` — MediaRecorder 封装

#### 已解决的实现问题

1. **凭证配置**: APIKey 和 APISecret 不可颠倒，否则 HMAC 签名验证失败。
2. **WebSocket 协议**: 严格遵循三阶段协议 —— SSB（参数上传，含 `common.app_id` + `business`）→ AUW（音频分片，每帧需 `common.app_id` + `business.aus/aue` + 间隔 40ms）→ 响应（base64 编码 XML）。
3. **音频格式**: 前端 WebM/Opus 必须转为 PCM 16kHz/16bit/单声道（ffmpeg 参数 `-ac 1 -ar 16000 -sample_fmt s16 -f s16le`）。
4. **分数制统一**: 讯飞 ISE 返回 5 分制，前端按 5 分制展示，所有维度（含完整度）均显示。

#### 降级策略

- 讯飞 API 调用失败 → 返回默认评分 `3.5/5` + 通用鼓励语
- 音频保存失败 → 仅记录数据库，标记音频缺失

### 2.5 讯飞语音合成（流式版）

描述：在学生端，当 AI 生成一段中文反馈或解析时（例如“这道题的正确选项是 B，因为它描述了……”，或口语教练的鼓励语），我们可以在后端调用讯飞 TTS API，将文本转为音频文件（MP3 或 PCM），然后将音频 URL 返回给前端自动播放。这样可以提升用户体验，避免浏览器内置语音的机械感。

安装依赖：

```bash
pip install websockets requests pydub  # pydub 用于音频格式转换（可选）
```

集成流程概览:

```sequenceDiagram
    participant Client as 前端
    participant Backend as FastAPI后端
    participant XF as 讯飞TTS WebSocket

    Client->>Backend: POST /api/v1/tts/synthesize<br/>{text: "你好..."}
    Backend->>XF: WebSocket 握手(携带签名)
    XF-->>Backend: 101 协议升级成功
    Backend->>XF: 发送业务参数 + 文本(base64)
    XF-->>Backend: 返回音频数据分片 (base64)
    Backend->>Backend: 拼接音频，保存为MP3
    Backend-->>Client: {audio_url: "https://.../xxx.mp3"}
    Client->>Client: 播放音频
```

核心代码实现:
鉴权签名函数（生成带有 Authorization 参数的 WebSocket URL）

```py
# utils/tts_auth.py
import hashlib
import hmac
import base64
from datetime import datetime
from urllib.parse import urlencode, quote
from typing import Optional

def build_tts_ws_url(host_url: str, api_key: str, api_secret: str) -> str:
    """
    根据讯飞流式TTS文档生成带鉴权参数的WebSocket URL。
    host_url: 例如 "wss://tts-api.xfyun.cn/v2/tts"
    """
    ul = urlparse(host_url)
    # 签名时间（UTC时区，RFC1123格式）
    date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    # 参与签名的三个字段
    sign_string = f"host: {ul.hostname}\ndate: {date}\nGET {ul.path} HTTP/1.1"

    # 使用 HMAC-SHA256 加密
    signature_sha = hmac.new(
        api_secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode('utf-8')

    # 构建 authorization_origin
    auth_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
    authorization = base64.b64encode(auth_origin.encode('utf-8')).decode('utf-8')

    # 构造最终URL
    query_params = {
        "host": ul.hostname,
        "date": date,
        "authorization": authorization
    }
    encoded_query = urlencode(query_params, quote_via=quote)
    return f"{host_url}?{encoded_query}"
```

TTS 合成服务（异步 WebSocket 调用）

```py
# core/tts_client.py
import asyncio
import websockets
import json
import base64
from typing import Optional
from pathlib import Path
from app.utils.tts_auth import build_tts_ws_url
from app.config import settings  # 从环境变量读取凭证

class TTSEngine:
    def __init__(self):
        self.host_url = "wss://tts-api.xfyun.cn/v2/tts"
        self.app_id = settings.XF_APPID
        self.api_key = settings.XF_API_KEY
        self.api_secret = settings.XF_API_SECRET

    async def synthesize(self, text: str, voice: str = "x4_xiaoyan", speed: int = 50, volume: int = 50) -> Optional[bytes]:
        """
        将中文文本合成为音频（返回原始音频字节流，默认 MP3 格式）
        - text: 不超过2000汉字（base64前约8000字节）
        - voice: 发音人，建议使用中文女声 "x4_xiaoyan"（需在控制台开通）
        - speed: 语速 0-100，默认50
        - volume: 音量 0-100，默认50
        """
        ws_url = build_tts_ws_url(self.host_url, self.api_key, self.api_secret)
        audio_chunks = []

        # 构造请求参数（业务参数）
        business = {
            "aue": "lame",      # 返回 MP3 格式，需开启 sfl=1 支持流式
            "sfl": 1,           # 开启流式返回（MP3 分段）
            "auf": "audio/L16;rate=16000",
            "vcn": voice,
            "speed": speed,
            "volume": volume,
            "tte": "UTF8",      # 文本编码
            "reg": 2            # 英文按单词朗读
        }
        # 公共参数
        common = {"app_id": self.app_id}
        # 业务数据（文本 base64 编码）
        data = {
            "status": 2,        # 合成文本一次性发送
            "text": base64.b64encode(text.encode('utf-8')).decode('utf-8')
        }
        request_body = {
            "common": common,
            "business": business,
            "data": data
        }

        try:
            async with websockets.connect(ws_url) as ws:
                # 发送合成请求
                await ws.send(json.dumps(request_body))
                # 接收音频数据分片
                while True:
                    msg = await ws.recv()
                    resp = json.loads(msg)
                    if resp.get("code") != 0:
                        print(f"TTS API error: {resp.get('message')}")
                        break
                    audio_data = resp.get("data", {}).get("audio")
                    if audio_data:
                        # 解码 base64 并追加
                        audio_chunks.append(base64.b64decode(audio_data))
                    status = resp.get("data", {}).get("status")
                    if status == 2:  # 合成结束
                        break
                # 合并所有分片
                if audio_chunks:
                    return b''.join(audio_chunks)
        except Exception as e:
            print(f"WebSocket TTS error: {e}")
        return None

    async def save_audio(self, text: str, output_path: Path, **kwargs) -> bool:
        """合成并保存音频到指定路径"""
        audio_bytes = await self.synthesize(text, **kwargs)
        if audio_bytes:
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            return True
        return False
```

集成到 FastAPI 路由（提供 HTTP 接口）

```py
# api/v1/tts.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.tts_client import TTSEngine
from app.utils.file_upload import upload_to_oss  # 假设有 OSS 上传函数
from app.config import settings
import uuid
import tempfile

router = APIRouter()
tts_engine = TTSEngine()

class TTSRequest(BaseModel):
    text: str
    voice: str = "x4_xiaoyan"
    speed: int = 50

@router.post("/synthesize")
async def synthesize_speech(req: TTSRequest):
    """
    将文本合成为语音，返回音频的访问 URL。
    前端获取 URL 后可以用 audio 元素播放。
    """
    # 限制文本长度（约2000汉字）
    if len(req.text) > 2000:
        raise HTTPException(status_code=400, detail="Text too long")

    # 合成音频
    audio_bytes = await tts_engine.synthesize(req.text, voice=req.voice, speed=req.speed)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="TTS synthesis failed")

    # 临时保存文件
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    # 上传到 OSS（避免本地存储）
    filename = f"tts/{uuid.uuid4()}.mp3"
    audio_url = await upload_to_oss(tmp_path, filename)

    # 清理临时文件
    os.unlink(tmp_path)

    return {"audio_url": audio_url}
```

环境变量配置（.env 中添加）

```ini
XF_APPID=your_appid
XF_API_KEY=your_api_key
XF_API_SECRET=your_api_secret
```

前端调用示例

```js
// 在 Vue 组件中
async function playAIAdvice(text) {
  try {
    const res = await axios.post("/api/v1/tts/synthesize", { text });
    const audio = new Audio(res.data.audio_url);
    audio.play();
  } catch (err) {
    console.error("TTS failed, fallback to Web Speech API");
    speakText(text, "zh-CN"); // 降级到浏览器内置语音
  }
}
```

注意事项

文本编码：必须使用 UTF-8 编码，且合成前用 base64.b64encode(text.encode('utf-8'))。

发音人权限：默认 x4_xiaoyan（普通中文女声）可直接使用；如需高级音库（如 xiaorong）需在控制台开通购买。

WebSocket 协议：确保服务器支持 WebSocket 出站连接（无防火墙阻断）。

音频长度：单次合成文本不超过 2000 汉字，超出需分多次请求。

### 2.6 教师端学情报告（后端）

数据来源：

用户答题记录（正确率、题型分布）。

口语练习记录（评分趋势）。

错题本高频错题统计。

生成方式：

定时任务（Celery Beat）每天凌晨计算所有活跃学生的画像。

使用 LangChain 多智能体框架生成自然语言报告。例如：

```python
from langchain.agents import initialize_agent

def generate_story_report(user_stats):
    prompt = f"用户最近一周学习了{user_stats['practice_count']}次，正确率从{user_stats['prev_accuracy']}提升到{user_stats['curr_accuracy']}。请用英雄之旅的叙事风格写一段鼓励性学习报告。"
    response = llm.invoke(prompt)
    return response
```

3. 数据库关键表结构（简化示意）

```sql
-- 影视片段表
CREATE TABLE video_clips (
    id UUID PRIMARY KEY,
    bvid VARCHAR(20) NOT NULL,
    page SMALLINT NOT NULL,
    start_sec INT NOT NULL,
    end_sec INT NOT NULL,
    iframe_url TEXT,
    title VARCHAR(200),
    category VARCHAR(100),
    difficulty CHAR(1),
    dialogue_text TEXT,
    summary TEXT,
    subtitle_source VARCHAR(50),
    remark TEXT,
    imported_at TIMESTAMP DEFAULT NOW()
);

-- 题目表
CREATE TABLE questions (
    id UUID PRIMARY KEY,
    clip_id UUID REFERENCES video_clips(id) ON DELETE CASCADE,
    type VARCHAR(10) CHECK (type IN ('part2','part3')),
    difficulty CHAR(1),
    content JSONB NOT NULL, -- {question, options, answer, explanation}
    created_at TIMESTAMP DEFAULT NOW()
);

-- 练习记录
CREATE TABLE practice_records (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    question_id UUID REFERENCES questions(id),
    selected_option SMALLINT,
    is_correct BOOLEAN,
    answered_at TIMESTAMP DEFAULT NOW()
);
```

索引设计：

video_clips(difficulty, bvid)：加速按难度筛选。

questions(clip_id)：外键索引。

practice_records(user_id, answered_at)：学情分析。

## 4. 前端关键技术实现

### 4.1 音频录制（Web Audio API）

```javascript
// composables/useRecorder.js
import { ref } from "vue";

export function useRecorder() {
  const mediaRecorder = ref(null);
  const audioChunks = ref([]);

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.value = new MediaRecorder(stream, { mimeType: "audio/webm" });
    mediaRecorder.value.ondataavailable = (e) => audioChunks.value.push(e.data);
    mediaRecorder.value.start();
  }

  function stopRecording() {
    return new Promise((resolve) => {
      mediaRecorder.value.onstop = () => {
        const blob = new Blob(audioChunks.value, { type: "audio/webm" });
        resolve(blob);
      };
      mediaRecorder.value.stop();
    });
  }

  return { startRecording, stopRecording };
}
```

### 4.2 语音合成（Web Speech API）

```javascript
export function speakText(text, lang = "en-US") {
  if (!window.speechSynthesis) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  utterance.rate = 0.9;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}
```

### 4.3 状态管理（Pinia）示例

```javascript
// stores/quiz.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { submitAnswer } from "@/api/quiz";

export const useQuizStore = defineStore("quiz", () => {
  const currentQuestions = ref([]);
  const answers = ref([]);

  async function submitCurrentAnswer(questionId, optionIndex) {
    const result = await submitAnswer({
      questionId,
      selectedOption: optionIndex,
    });
    answers.value.push({ questionId, optionIndex, correct: result.correct });
    return result;
  }

  return { currentQuestions, answers, submitCurrentAnswer };
});
```

## 5. 部署与运维

### 5.1 容器化部署（Docker Compose）

```yaml
version: "3.8"
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: reelenglish
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: securepass
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://admin:securepass@postgres/reelenglish
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "80:80"
```

### 5.2 环境变量配置 (.env)

```ini
# 后端
DEEPSEEK_API_KEY=sk-xxx
XF_APPID=12345
XF_API_KEY=xxx
XF_API_SECRET=xxx
OSS_ACCESS_KEY=xxx
OSS_SECRET_KEY=xxx
OSS_BUCKET=reelenglish-audio
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com

# 前端（Vite）
VITE_API_BASE_URL=https://api.reelenglish.com/api/v1
```

### 5.3 性能优化建议

数据库连接池：SQLAlchemy 配置 pool_size=20, max_overflow=40。

Redis 缓存：用户定级结果缓存 1 小时，题目详情缓存 24 小时。

CDN 加速：前端静态资源使用阿里云 OSS + CDN。

API 限流：使用 slowapi 对每个 deviceId 限制 100 次/分钟。

## 6. 安全性考量

所有 API 使用 deviceId 作为用户标识，不收集真实身份。

讯飞、DeepSeek 的 API Key 仅在后端环境变量中存储，前端不可见。

音频文件上传到 OSS 时，生成 UUID 文件名，避免路径遍历。

数据库查询使用参数化，防止 SQL 注入。

## 7. 异常处理与降级策略

异常场景 降级方案
DeepSeek API 超时 使用本地预置题目（静态 JSON）
讯飞语音评测失败 返回默认评分（70分）+ 通用鼓励语
OSS 上传失败 仅保存本地路径，后台异步重试
B站 iframe 无法加载 显示提示信息，提供剧集名称和对应搜索链接

## 8. 测试与监控

单元测试：使用 pytest 测试核心业务逻辑（定级、出题解析等）。

集成测试：使用 httpx 模拟 API 调用，测试端到端流程。

日志：使用 loguru 记录所有 API 请求和外部调用耗时。

监控：接入 Prometheus + Grafana 监控 API 响应时间、错误率。

## 9. 数据流转示例（用户答题完整流程）

用户登录 → 前端请求 /api/v1/questions/random?difficulty=B&count=5。

后端从数据库随机抽取 5 题，返回题目列表。

用户选择答案 → 前端 POST /api/v1/answers/submit。

后端校验答案，记录到 practice_records，并更新用户错题本。

后端返回结果（正确/错误 + 解析）。

前端展示结果，并自动将错题加入本地 store。

## 10. 附录：关键 Prompt 模板

### 10.1 生成 Part2 问答题

```text
你是一个托业听力出题官。请根据以下对话，生成一个 Part2 问答题（即一个问题，对应三个回答选项）。对话内容：{dialogue}

要求：
- 问题必须基于对话中的关键信息。
- 三个选项用英文写出，其中只有一个正确。
- 输出 JSON：{ "question": "...", "options": ["...", "...", "..."], "answer": 0, "explanation": "中文解析" }
10.2 生成口语练习自由应答问题
```

```text
根据以下影视片段剧情，生成一个开放性的英语口试问题，鼓励用户表达个人观点。剧情：{summary}
要求问题与剧情相关，且没有标准答案。输出格式：{ "question": "..." }
```

文档版本: v1.0
最后更新: 2026-05-02
维护者: RealEnglish 开发团队
