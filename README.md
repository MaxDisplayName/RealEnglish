# RealEnglish — AI 驱动的英语视听说学习平台

> 武汉理工大学 "华工杯" AI 应用创新大赛参赛作品

**RealEnglish（真语英语）** 是一个全栈 Web 英语学习平台，使用**真实影视片段**（美剧/英剧/电影）作为学习素材，结合 **DeepSeek 大模型**智能出题和**科大讯飞语音评测**引擎，实现"看 → 听 → 说 → 评"四步闭环式英语学习。

---

## 功能特性

### 学生端

- **定级测试** — 10 题混合难度测评，A/B/C 三级精准定级
- **影视片段库** — 35 段精选美剧/英剧/电影片段，7 大分类，B站播放器嵌入
- **AI 智能出题** — DeepSeek 根据对话内容自动生成托业/四六级风格听力题
- **口语评测** — 三种模式（跟读/自由应答/情景对话），讯飞 ISE 四维评分（准确度/流畅度/完整度/总分）
- **情景式自由对话** — AI 生成真实场景+角色，多轮英语对话，结束后综合评测
- **AI 学习助手** — LangGraph ReAct Agent，12 个工具，智能推荐片段/分析学情/生成复习计划
- **片段助手** — 悬浮可拖动 AI 对话，解答词汇/语法/文化背景问题
- **流式大模型翻译** — SSE 流式中英对照翻译，localStorage 缓存
- **单词本** — 点击单词查词（DeepSeek 释义），收藏/复习/检测模式
- **错题本** — 自动收录错题，分类复习
- **数据看板** — ECharts 趋势图 + GitHub 风格贡献热力图 + 学习统计

### 教师端

- **管理看板** — 4 统计卡片 + ECharts 趋势图 + 等级分布环形图 + 学习预警
- **学生管理** — 学生列表（分页+搜索），分组管理，A/B/C 分级管理，详情抽屉含练习统计+口语录音回放+AI 报告
- **师生通信** — 气泡聊天室（单聊+群发），消息已读/未读状态
- **任务系统** — 创建学习任务（练习/口语/对话/片段四项指标），自动生成进度快照
- **公告系统** — 全局公告发布，学生登录弹窗展示，已读确认
- **AI 教师助手** — LangGraph ReAct Agent，19 个工具，覆盖学情分析/任务创建/公告发布/进度追踪
- **教师邀请码** — 4 位邀请码绑定，自动加入分组

---

## 技术栈

| 层 | 技术 |
|-----|------|
| 前端 | Vue 3 (Composition API) · TypeScript · Vite · Element Plus · ECharts 5 · Pinia |
| 后端 | FastAPI (Python) · SQLAlchemy 2.0 · Pydantic v2 · JWT (HS256) |
| AI | DeepSeek · LangGraph · LangChain · ReAct Agent |
| 语音 | 科大讯飞 ISE (WebSocket 流式评测) · 讯飞 TTS |
| 数据 | SQLite (开发) · PostgreSQL (生产规划) |
| 视频 | B站 iframe/DASH · postMessage 通信 |

---

## 项目结构

```
RealEnglish/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── main.py           # 应用入口
│   │   ├── api.py            # API 路由（所有端点）
│   │   ├── models.py         # SQLAlchemy 数据模型 (13 张表)
│   │   ├── schemas.py        # Pydantic 校验模型
│   │   ├── agents.py         # LangGraph ReAct Agent
│   │   ├── ai.py             # DeepSeek LLM 封装
│   │   ├── config.py         # 配置管理
│   │   ├── db.py             # 数据库初始化 + CSV 同步
│   │   ├── crud.py           # 数据库操作
│   │   ├── bilibili.py       # B站视频代理
│   │   └── time_utils.py     # 北京时间工具
│   ├── res/
│   │   ├── video_clips.csv   # 片段数据源
│   │   └── bili_clip_extractor_v2.py  # 片段提取脚本
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── layouts/          # StudentLayout / TeacherLayout
│   │   ├── pages/            # 20+ 页面组件
│   │   ├── components/       # 可复用组件
│   │   ├── api/              # API 模块 (student/teacher/auth/assistant)
│   │   ├── composables/      # Vue Composables
│   │   ├── stores/           # Pinia stores
│   │   └── utils/            # 工具函数
│   ├── index.html            # 落地页 (GSAP 动画)
│   └── package.json
├── remotion-video/           # Remotion 演示视频项目
│   └── src/scenes/           # 9 个演示视频场景
├── docs/
│   └── progress.md           # 项目进度报告
├── demo-video-script.md      # 演示视频分镜脚本
└── README.md
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- ffmpeg（音频转码）

### 1. 克隆仓库

```bash
git clone git@github.com:MaxDisplayName/RealEnglish.git
cd RealEnglish
```

### 2. 后端配置

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 API Key
```

### 3. 前端配置

```bash
cd frontend
npm install
npm run dev
```

### 4. 启动

两个终端窗口：

```bash
# 终端 1 — 后端
cd backend && .venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 终端 2 — 前端
cd frontend && npm run dev
```

浏览器打开 **http://localhost:5173**

---

## 环境变量

复制 `backend/.env.example` 为 `backend/.env` 并填写：

```env
# DeepSeek API (必填)
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com/v1

# 讯飞语音评测 (必填)
XFYUN_APP_ID=xxx
XFYUN_API_KEY=xxx
XFYUN_API_SECRET=xxx

# 数据库
DATABASE_URL=sqlite:///./reelenglish.db

# LangSmith (可选，用于 Agent 追踪)
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=lsv2_xxx
```

---

## 数据库

SQLite 数据库在首次启动时自动创建，并从 `backend/res/video_clips.csv` 同步片段数据。初始化脚本可预设测试账号：

```bash
cd backend
python init_users.py
```

预设账号（密码 `12345678`）：

| 角色 | 用户名 | 邀请码 |
|------|--------|--------|
| 教师 | teacher_wang | W4X9 |
| 教师 | teacher_li | K2M7 |
| 学生 | student_01 ~ 12 | — |

---

## 演示视频

项目包含 Remotion 演示视频源码（`remotion-video/`），展示全部核心功能。

```bash
cd remotion-video
npm install
npm run dev     # 预览
npm run build   # 导出 MP4
```

---

## 许可证

MIT License
