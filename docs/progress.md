# RealEnglish 项目进度报告

> 最后更新: 2026-05-12 (v22 · 最终版)
> 维护者: RealEnglish 开发团队

## 一、已完成功能

### 1. 后端 (FastAPI)

| 模块 | 状态 | 说明 |
|------|------|------|
| 用户管理 | ✅ 完成 | 账号制用户体系（student/teacher），前端主流程已切换为账号登录 |
| 认证系统 | ✅ 完成 | JWT 签发/验证、密码哈希、角色（student/teacher）|
| 匿名数据兼容 | ⚠️ 保留兼容 | 后端仍保留 deviceId 兼容逻辑，但前端主链路已不再依赖 |
| 影视片段 CRUD | ✅ 完成 | 支持分类/难度筛选，分页查询 |
| B站视频代理 | ✅ 完成 | DASH 流代理、视频流聚合、iframe 嵌入 |
| AI 出题 (DeepSeek) | ✅ 完成 | 托业风格 Part2/Part3 题目生成，含 JSON 解析 |
| 定级测试 | ✅ 完成 | 10 题随机抽样 (A3+B4+C3)，等级映射 |
| 答题记录 & 错题本 | ✅ 完成 | 提交答案、错题列表、练习统计 |
| 口语评测 (讯飞) | ✅ 完成 | WebSocket 流式评测、音频转码、降级策略 |
| 自由应答问题生成 | ✅ 完成 | DeepSeek 生成开放性问题 |
| 语音合成 TTS (讯飞) | ✅ 完成 | 文本转 MP3，OSS 上传 |
| AI 英语教练对话 | ✅ 完成 | DeepSeek 聊天，带历史记录 |
| LangGraph 多智能体 | ✅ 完成 | 出题 Agent、口语 Agent、兴趣推荐 Agent |
| 本地日志系统 | ✅ 完成 | 文件轮转日志 (10MB×5)，前端日志收集接口 |
| 数据库初始化 | ✅ 完成 | Excel 数据导入，自动建表 |
| 教师端 API | ✅ 完成 | 学生列表（分页+搜索）、等级分布统计、单个学生详情（含练习统计、难度正确率、14天活跃、高频错题汇总）|
| ReportAgent | ✅ 完成 | LangGraph 双节点：fetch_data → write_narrative，DeepSeek 生成英雄之旅叙事报告 |
| 教师分组模型 | ✅ 完成 | 新增 teacher_groups 模型、学生 group_id 关联 |
| 教师分组 API | ✅ 完成 | 分组列表、创建分组、更新分组、学生分组分配 |
| 情景式自由对话 API | ✅ 完成 | `/free-talk/start|respond|end|{id}`，AI 生成场景+角色扮演+多轮对话+统一评测 |
| 学生助手 API | ✅ 完成 | LangGraph ReAct Agent，12 个工具：统计/错题/活跃/片段搜索/任务/报告/单词本/口语趋势/复习计划等 |
| 教师助手 API | ✅ 完成 | LangGraph ReAct Agent，19 个工具：学生管理/报告/分组/任务/公告/通信/对比/周报等 |
| 角色权限收紧 | ✅ 完成 | 学生专属接口限制为 student，教师分析接口限制为 teacher |
| 学习预警 API | ✅ 完成 | `GET /teacher/students/alerts/list`，自动标记不活跃/正确率骤降/未定级学生 |
| 单词本 API | ✅ 完成 | 6 个端点：查词(lookup)/保存/删除/列表/掌握切换(DeepSeek释义+缓存) |
| 口语趋势 API | ✅ 完成 | `GET /speaking/history` 最近30天+口语录音回放 `/speaking/{id}/audio` |
| 流式翻译 API | ✅ 完成 | `POST /clips/{id}/translate/stream` SSE 流式对话翻译 |

### 2. 前端 (Vue 3)

| 模块 | 状态 | 说明 |
|------|------|------|
| 学生仪表盘 | ✅ 完成 | 等级徽章、统计概览、快速入口 |
| 定级测试页面 | ✅ 完成 | 10 题向导，含关联视频播放，结果展示 |
| 登录/注册页面 | ✅ 完成 | 邮箱+密码注册/登录，学生/教师身份选择 |
| 个人中心页面 | ✅ 完成 | 用户信息展示、等级/角色显示、退出登录 |
| 影视片段列表 | ✅ 完成 | 分类/难度筛选，卡片网格 |
| 片段详情页 | ✅ 完成 | B站 iframe 播放器、对话展示、出题入口 |
| 答题练习页面 | ✅ 完成 | AI 题目作答，实时反馈 |
| 口语练习页面 | ✅ 完成 | 跟读/自由应答双模式，逐句练习 |
| 错题本页面 | ✅ 完成 | 分页展示错题，含解析 |
| AI 英语教练 | ✅ 完成 | 聊天界面 |
| B站播放器组件 | ✅ 完成 | iframe 嵌入，进度条 seek，片段定时结束 |
| 口语录音组件 | ✅ 完成 | MediaRecorder 封装，5 分制评测展示 |
| 本地日志工具 | ✅ 完成 | 错误捕获，定时上传后端，导出功能 |
| 教师端看板 | ✅ 完成 | 统计概览、等级分布、学生表格、抽屉详情含难度正确率/活跃柱状图/高频错题/AI 报告 |
| 学生端/教师端分离 | ✅ 完成 | 单应用双工作台，独立布局、独立路由树、独立导航与登录跳转 |
| 学生学习助手 | ✅ 完成 | 学习规划、片段推荐、复习建议、练习指导 |
| 教师管理助手 | ✅ 完成 | 学情分析、分组建议、跟进建议 |
| 教师分组管理页面 | ✅ 完成 | 创建分组、查看分组、为学生分组 |
| 情景式自由对话页面 | ✅ 完成 | AI 生成话题+场景，聊天式多轮对话（文字/语音），结束后四维度评测 |
| Profile 悬浮对话框 | ✅ 完成 | 点击导航栏用户名弹出个人中心对话框，替代原独立页面 |
| 全局难度颜色统一 | ✅ 完成 | A级(高级)绿色/B级(中级)蓝色/C级(初级)紫色，全局 span.diff-badge 样式替换 el-tag |
| 统一返回按钮 | ✅ 完成 | 所有二级页面添加 ArrowLeft+text 风格返回按钮 |
| 学习预警面板 | ✅ 完成 | 教师看板顶预警条，3类预警点击跳转学生管理页 |
| 单词本 | ✅ 完成 | 片段对话单词可点击查词收藏，单词本页支持列表/排序/复习模式 |
| 口语录音回顾 | ✅ 完成 | 教师学生详情抽屉可播放口语录音，评分+反馈展示 |
| 口语趋势图 | ✅ 完成 | 口语练习页底部 ECharts 折线图（总分/准确度/流畅度趋势） |

### 3. 数据模型

| 表 | 状态 | 说明 |
|----|------|------|
| users | ✅ 完成 | deviceId + level |
| video_clips | ✅ 完成 | B站视频元数据 + 对话文本 |
| questions | ✅ 完成 | 关联 clip 的多选题，JSON content |
| practice_records | ✅ 完成 | 答题记录，含正误标记 |
| speaking_records | ✅ 完成 | 口语练习历史，含评分 |
| teacher_groups | ✅ 完成 | 教师轻量分组 |
| users.group_id | ✅ 完成 | 学生归属分组 |
| free_conversations | ✅ 完成 | 情景式自由对话会话记录（话题/场景/角色/状态/评测） |
| conversation_messages | ✅ 完成 | 对话消息记录（角色/内容/音频URL） |
| announcements | ✅ 完成 | 教师公告（标题/内容/可见范围/置顶） |
| messages | ✅ 完成 | 师生双向私信（发送者/接收者/分组/已读/回复线程） |
| tasks | ✅ 完成 | 教师学习任务（练习/口语/对话/片段目标/截止日期/状态） |
| task_progress | ✅ 完成 | 学生任务进度快照（各项完成量/正确率/完成状态） |
| user_vocabulary | ✅ 完成 | 学生单词本（单词/释义/掌握状态/来源片段，uq_user_word 约束） |

---

## 二、待完成功能（已全部完成/转为运维项）

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 学习预警系统 | ✅ 已完成 | 教师看板顶部预警条：不活跃/正确率骤降/未定级（v21） |
| 教师端口语录音回顾 | ✅ 已完成 | 学生详情抽屉播放口语录音+评分+反馈（v21） |
| 单词本 | ✅ 已完成 | 点击查词收藏、检测模式出题、错题联动（v21） |
| 口语趋势图 | ✅ 已完成 | ECharts 折线图 30 天趋势（v21） |
| 登录角色选择 | ✅ 已完成 | 落地页+Vue SPA 双入口（v20） |
| 邀请码注册修复 | ✅ 已完成 | 前端到后端完整传递链（v20） |
| 流式大模型翻译 | ✅ 已完成 | SSE 流式+缓存+重新生成（v20） |
| 单元测试 | 运维 | pytest 测试核心逻辑 |
| Docker 部署 | 运维 | Dockerfile + docker-compose.yml |
| 移动端适配 | 运维 | PWA、响应式布局优化 |
| Redis Checkpointer | 运维 | 替换 MemorySaver |
| OSS 生产配置 | 运维 | 接入阿里云 OSS |
| Alembic 迁移 | 运维 | SQLite → PostgreSQL |

---

## 三、语音评测实现详情

### 3.1 架构

```
前端 (MediaRecorder) → WebM/Opus → 后端 (ffmpeg 转码 PCM) → 讯飞 ISE WebSocket → XML → 评分
                                                                        ↘ DeepSeek → AI 反馈
```

### 3.2 关键实现

- **协议**: 讯飞语音评测流式版 `wss://ise-api.xfyun.cn/v2/open-ise`
- **参数**: `en_vip` 英语引擎，`read_sentence` 句子模式，`category=read_sentence`
- **评分维度**: total_score, accuracy, fluency, integrity（5 分制）
- **降级策略**: 讯飞 API 失败时返回默认评分 3.5/5 + 通用鼓励语
- **音频转码**: ffmpeg 子进程将 WebM/Opus 转为 PCM 16kHz/16bit/单声道

### 3.3 已解决的问题

1. ✅ 凭证配置：APIKey/APISecret 正确配置
2. ✅ WebSocket 协议：SSB（参数上传）→ AUW（音频分片，40ms 间隔）→ 响应（base64 XML）
3. ✅ 前端分数制：由 100 分制改为 5 分制，与讯飞原始返回值一致
4. ✅ 完整度维度：前端已添加 integrity 显示，展示全部 4 个评分维度

---

## 四、后续功能建议

以下功能来自讯飞语音评测 API 文档和其他第三方能力，可考虑在后续版本中实现。

### 4.1 音素级发音反馈（高价值）

讯飞 ISE API 返回的 XML 中包含每个音素（phoneme）的详细评分数据，包括：
- 每个单词的发音得分
- 每个音素的准确度（元音/辅音）
- 发音错误类型（替换、省略、插入）

**建议实现**: 解析 XML 中的 `<word>` 和 `<phone>` 标签，提取发音不准确的单词，在 AI 反馈中给出具体单词级别的改进建议（"注意单词 'interesting' 中 /t/ 的发音"）。

**影响范围**: `backend/app/core/speech_eval.py` — 扩展 `_parse_eval_result()`，返回 `word_scores` 和 `phone_errors`

### 4.2 自由朗读模式（read_chapter）

当前仅支持 `read_sentence`（跟读单句），讯飞还支持：
- `read_word`: 单词级评测
- `read_chapter`: 段落级自由朗读（无参考文本，或整段参考文本）

**建议实现**: 增加 `mode=chapter` 参数，允许用户朗读整个片段对话后获得综合评分。

**影响范围**: `backend/app/api/v1/speaking.py` — 增加 mode 参数分支；`frontend/src/components/SpeakingRecorder.vue` — 增加"段落朗读"模式选项

### 4.3 口语练习历史趋势图

前端 `SpeakingRecorder.vue` 目前仅展示单次评分结果，可增加历史趋势：
- 从 `speaking_records` 表查询该用户的最近 N 条记录
- 绘制折线图展示总分、准确度、流畅度变化趋势
- 帮助用户看到进步轨迹

**影响范围**: 后端新增 `/api/v1/speaking/history` 接口；前端新增趋势图表组件（可使用 ECharts 或 Chart.js）

### 4.4 语音合成（TTS）在前端的应用扩展

TTS 模块已经实现（`backend/app/api/v1/tts/synthesize`），但目前前端未充分使用：
- AI 教练反馈文本可自动朗读
- 生词点击可播放发音
- 对话文本可逐句朗读

**建议实现**: 在 AI 反馈区域增加"朗读反馈"按钮；在对话展示区域点击单词触发 TTS。

### 4.5 DeepSeek 多轮口语对话 ✅ 已实现

已实现为「情景式自由对话」模块：
- AI 生成生活场景和角色 → 用户与 AI 多轮对话（文字/语音）→ 结束后四维度评测
- 语音输入通过讯飞 IAT 转文本，对话内容由 DeepSeek 生成

**影响范围**: `backend/app/api.py` free_talk_router；`frontend/src/pages/FreeTalkPage.vue`

### 4.6 兴趣引导推荐

多智能体框架中已实现 `interest_agent.py`（向量检索推荐），但前端未接入：
- 根据用户练习记录和偏好，推荐新的影视片段
- 在仪表盘增加"推荐给你"板块

**影响范围**: 前端 `StudentDashboard.vue` — 增加推荐区域；后端 agent 调用需接入

---

---

## 六、认证系统实现详情

### 6.1 架构

```
前端登录/注册 → POST /auth/login 或 /auth/register → JWT 签发 → 前端存储 token
→ 后续请求 Authorization: Bearer <token> → 后端解析 → 返回用户信息
→ 当前前端主链路要求账号登录；后端仍保留 X-Device-Id 兼容入口用于过渡
```

### 6.2 后端组件

| 文件 | 说明 |
|------|------|
| `models/user.py` | 扩展字段：username, email, hashed_password, avatar, role, is_active, updated_at |
| `core/security.py` | `hash_password()` / `verify_password()` (bcrypt), `create_access_token()` / `decode_access_token()` (JWT HS256) |
| `schemas/auth.py` | RegisterRequest（含密码强度校验）、LoginRequest、TokenResponse、MergeDeviceRequest |
| `api/v1/auth.py` | `POST /register`, `POST /login`, `GET /me`, `POST /merge-device` |

### 6.3 前端组件

| 文件 | 说明 |
|------|------|
| `views/Login.vue` | 用户名/邮箱 + 密码登录 |
| `views/Register.vue` | 注册表单，学生/教师身份选择 |
| `views/Profile.vue` | 个人信息展示，退出登录 |
| `stores/user.js` | 新增 `loginByAccount()`, `registerByAccount()`, `logout()`, `checkAuth()` |
| `api/request.js` | 拦截器统一使用 `Authorization: Bearer <token>` |
| `router/index.js` | 已拆分学生端与教师端双路由树，按角色跳转与守卫 |
| `layouts/StudentLayout.vue` / `TeacherLayout.vue` | 两套独立布局与导航 |

### 6.4 兼容性

- 当前产品主路径不再依赖匿名学习
- 后端仍保留 `GET /auth/me` 的兼容降级逻辑，便于过渡期迁移
- `merge-device` 仍保留接口，但前端默认流程已不再调用

### 6.5 定级测试视频

定级测试的 10 道题现在每道题都关联一个 B站视频片段。后端 `GET /questions/placement` 返回每个题目的 `clip_id` 对应视频的 `bvid/page/start_sec/end_sec`，前端 `PlacementTest.vue` 嵌入 `VideoPlayer` 组件显示相应片段。

---

## 七、技术债务

| 项目 | 说明 |
|------|------|
| log_config.py 中的 `exc_info=True` | 调式时添加的详细异常堆栈，生产环境可考虑按等级控制 |
| 前端日志缓冲区 | 当前 200 条上限，生产环境可能需要调整 |
| ffmpeg 依赖 | 音频转码依赖系统安装 ffmpeg，需在部署文档中注明 |
| X-Device-Id 匿名用户兼容逻辑 | 已不符合当前双工作台产品结构，建议下一阶段彻底移除 |

---

## 八、更新日志

### v5 (2026-05-07)
- 新增情景式自由对话模块：AI 生成场景+角色，用户与 AI 多轮对话（文字/语音），对话结束后四维度评测
- 新增 `free_conversations` 和 `conversation_messages` 数据模型
- 新增 `POST /free-talk/start|respond|end` 和 `GET /free-talk/{id}` API
- 新增 `FreeTalkPage.vue` 前端页面，路由 `/student/free-talk`
- Profile 改为悬浮对话框（`ProfileDialog.vue`），不再作为独立页面
- 全局统一难度颜色：A=绿色/B=蓝色/C=紫色（新增 `.diff-badge` 全局样式，修复 ClipListPage/WrongNotePage/TeacherDashboardPage）
- 所有二级页面统一添加 ArrowLeft+text 风格返回按钮
- 修复 AI 智能出题的答题记录不保存到错题本的问题（`submit_answer` 端点增加记录落库）
- ClipDetailPage 难度标签改用统一 `diff-badge`，返回按钮移至左上角

### v6 (2026-05-07)
- 学生助手升级为 LangGraph ReAct Tool-Calling Agent（`create_agent`），绑定 5 个工具
- 教师助手升级为 LangGraph ReAct Tool-Calling Agent（`create_agent`），绑定 6 个工具
- 工具通过 `RunnableConfig` 注入用户身份，LLM 无需知道用户 ID
- SSE 流式格式从纯文本改为 JSON 行事件（`content`/`tool_start`/`tool_end`/`done`）
- 前端助手页面适配 JSON SSE 解析，新增工具调用状态指示（蓝色脉冲圆点）
- 保留现有 4 个 Agent（quiz/speaking/report/interest）不动
- LangSmith 可追踪完整 ReAct 循环（LLM → Tool Call → Tool Result → LLM → ...）

### v7 (2026-05-07)
- Agent 多轮对话记忆改为 LangGraph 内置 `MemorySaver` checkpoint 机制，配合 `thread_id` 实现状态持久化
- 移除手动 `req.history` 拼接逻辑，每个用户/线程仅发当前消息，历史由 checkpointer 自动加载
- Agent 改为模块级单例（`get_student_agent()` / `get_teacher_agent()`），共享 MemorySaver 实例
- 验证: 第 2 轮消息数自动从 6 累积到 8，Agent 正确记住了用户名
- Markdown 表格样式补齐：新增 `table/th/td` CSS（边框+斑马纹），覆盖 3 个聊天页面
- 工具调用改为时间轴可视化：可折叠面板，每项显示工具名、运行状态（✓/spinner）、耗时、结果摘要
- 修复 `.env` 中 `OPENAI_API_KEY` 导致 pydantic-settings `extra=forbid` 校验失败的问题

### v8 (2026-05-07)
- Agent checkpoint 从 MemorySaver 升级为 SqliteSaver（`langgraph-checkpoint-sqlite`），服务重启不丢失会话
- 新增 `assistant_threads` 表存储会话元数据（用户/角色/标题/时间）
- 新增 4 个线程 CRUD 端点：GET/POST/PATCH/DELETE `/assistants/threads`
- 助手页面重构：左侧会话列表侧边栏（新建/切换/删除）+ 右侧聊天区
- Chat 端点增加 `thread_id` 参数，首条消息自动创建线程并更新标题
- SSE 流增加 `thread_id` 事件通知前端
- 前端 UI 视觉打磨：精炼编辑风（渐变头像、多级阴影、毛玻璃顶栏、浮动空状态、时间轴左绿条激活指示器）
- 教师端独立配色（暖金色调）：sidebar 渐变、时间轴金调、indigo 用户气泡
- 新增 `frontend/src/api/assistant/api.js` 共享线程 API 模块

### v9 (2026-05-08)
- `DEEPSEEK_API_KEY` 统一重命名为 `OPENAI_API_KEY`（config.py/.env/.env.example/ai.py/agents.py），LangSmith 追踪恢复
- Agent checkpoint 成功升级为 SqliteSaver（独立线程事件循环初始化 `AsyncSqliteSaver`），服务重启不丢失会话
- 助手页全宽（布局 `max-width` 移除）+ 全高（`calc(100vh - 56px - 40px)`）
- 双气泡修复：预创助手消息自带 streaming 动画，移除底部独立 loading 区块
- 时间轴折叠状态存入独立 `reactive({})` 字典，不被 computed 覆盖
- 操作按钮（复制/编辑/重新生成）移至气泡外部 + 内联 SVG 图标

### v10 (2026-05-08)
- **对话持久化**：新增 `thread_messages` 表，非流式/流式端点均在完成后写入 user + assistant 消息
- **历史恢复 API**：`GET /assistants/threads/{id}/messages` 从 `thread_messages` 表读取，绕过 SqliteSaver 事件循环问题
- `selectThread` 改为 `async`，加载历史消息；修复 `handleNewThread`/`handleDeleteThread` 中 `await` 缺失导致的竞态条件（消息被异步覆盖）
- 修复流式端点只保存用户消息不保存 AI 回复（`full_reply` 收集完整内容后写入）
- **LangSmith 追踪修复**：`config.py` 中将 `langsmith_*` 配置回写到 `os.environ`，LangChain 自动追踪机制可以读取
- 移除 `AsyncSqliteSaver`/`init_checkpointer` 等跨事件循环方案，简化为直接 SQLite 持久化

### v11 (2026-05-08)
- **片段分类合并**：14 个散乱分类合并为 7 个清晰大类（动画/家庭生活/社交聊天/演讲/职场/餐饮购物/日常生活）
- **search_clips 工具重写**：移除 FAISS 依赖（DeepSeek 不支持 embeddings），改为纯关键词模糊搜索，搜索范围扩展到全部片段和 title/summary/dialogue_text/category 四个字段，返回结构化 JSON（含 id/match_score）
- **AI 推荐表格**：更新 student agent system prompt，指导 LLM 将搜索结果格式化为 Markdown 推荐表格（⭐推荐指数 + 可点击片段链接），前端增加 `clip://` 链接拦截跳转
- **导航栏增加"情景对话"入口**：StudentLayout header 新增 Free Talk 导航链接
- **答题练习页增加视频播放**：PracticePage 复用 VideoPlayer 组件，题目上方显示片段视频

### v12 (2026-05-08)
- **片段数据迁移至 CSV**：从 SQLite 导出 `backend/res/video_clips.csv`（12 列，去掉了"备注"列），作为片段的唯一数据源
- **启动同步机制**：`db.py` 改为每次启动从 CSV upsert 同步（按 BV号+分P+起始时间匹配，存在则更新、不存在则新增），不再依赖 `res/video_clips.xlsx`
- **改进版提取脚本**：新增 `backend/res/bili_clip_extractor_v2.py`，操作 CSV 文件，支持交互/命令行双模式，AI 自动识别角色性别，支持追加和更新已有片段
- **B站播放器修复**：iframe URL 增加 `_tstamp` 缓存破坏参数 + `jsapi=1` 启用 postMessage；新增播放/暂停按钮（暂停=销毁iframe，播放=重建iframe）；暂停遮罩显示提示文字
- **口语评测动画**：SpeakingRecorder 增加评测中加载动画（旋转圆环+声波柱）、分数数字跳动、评分条填充动画、维度交错渐入、结果卡片整体入场

### v13 (2026-05-08)
- **片段默认按难度排序**：`get_clips` 增加 `ORDER BY difficulty ASC`（A→B→C），前端 `limit` 从默认 20 提升到 100
- **学习概览页全面升级**：
  - 3 统计卡片：今日练习次数、今日学习片段数、今日口语练习数
  - 新增 `GET /student/dashboard` 聚合端点：返回今日统计 + 近 7 天趋势 + 6 个月热力图 + 个性化推荐
  - ECharts 数据看板：每日练习/口语折线图、正确率柱状图、口语均分趋势图
  - GitHub 风格贡献热力图（27周×7天 CSS Grid，绿色深度表示活跃度）
  - 片段推荐算法：基于用户等级 + 类别偏好 + 已练习历史评分排序
- **口语时长持久化**：`useRecorder` 追踪录音时长，`SpeakingRecorder` 提交时传 `duration_sec`，后端 `SpeakingRecordModel.duration_sec` 落库

### v14 (2026-05-08)
- **片段学习助手**：ClipDetailPage 新增悬浮可拖动 AI 对话助手，解答词汇/语法/文化背景问题
  - 后端 `POST /assistants/student/clip-chat/stream`：从 DB 读取片段信息注入 system prompt，直接流式返回（无需 Agent）
  - 前端 `FloatingAssistant.vue`：可拖动气泡按钮 + 可拖动对话卡片，SSE 流式渲染，`sessionStorage` 持久化位置和展开状态
- **AI 时间感知**：学生/教师助手新增 `get_current_time` 工具，返回准确北京时间

### v15 (2026-05-09)
- **片段助手流式输出修复**：后端 `llm.astream` 每个 token 间加 `asyncio.sleep(0.015)`，强制独立 SSE 块发送避免本地网络一次性到达；前端完全对齐 StudentAssistantPage 的 SSE 解析模式
- **片段助手拖动修复**：回归 `makeDraggable` 闭包模式，避免 Vue 模板中 ref 自动解包导致 `.value` 访问失败
- **B站播放器暂停修复**：暂停时 `iframe.src = 'about:blank'` 销毁播放器实现真正停止；`pausedByUser` 守卫防止残留 `onFrameReady` 误触发；播放时重建 iframe 从保存位置开始
- **活跃热力图优化**：显示范围从 6 个月改为本月+上月完整两月，`localKey()` 替代 `toISOString()` 修复 UTC 时区偏移导致的日期错位
- **片段数据源迁移**：从 `res/video_clips.xlsx` 迁移至 `backend/res/video_clips.csv`，启动时 upsert 同步；新增 `bili_clip_extractor_v2.py` 改进版提取脚本（`.env` 自动读取 API Key、分类选择器、Whisper 纯语音识别、AI 审核循环）
- **`search_clips` 工具重写**：移除 FAISS embeddings 依赖，改为纯关键词模糊搜索（4字段×全部片段），返回结构化 JSON 含 match_score
- **AI 推荐表格**：student agent 输出 ⭐推荐指数 + `clip://` 可点击链接，前端拦截 Vue Router 跳转

### v16 (2026-05-09)
- **AI 对话智能提示词**：三个 AI 对话界面（学生学习助手、片段学习助手、教师管理助手）新增 AI 生成的个性化提示词
- 学生学习助手：根据用户等级/学习统计/错题/活跃度生成 4 条情景问题（绿色调气泡）
- 片段学习助手：根据当前片段对话文本/剧名/剧情生成 4 条引导性提问（绿色调小气泡，居中排列）
- 教师管理助手：根据学生名单/等级分布/分组情况生成 4 条管理建议（金色调气泡）
- 后端新增 3 个轻量端点（`/student/suggestions`、`/clip-chat/suggestions`、`/teacher/suggestions`），非流式返回 JSON 数组
- 前端 `sessionStorage` 缓存提示词，加载时显示骨架屏，点击气泡自动填入并发送

### v17 (2026-05-09)
- **教师看板数据增强**：参照学生端增加 ECharts 数据看板（4 统计卡片 + 练习/口语趋势折线 + 正确率柱状 + 口语均分 + 等级分布环形图），支持按分组筛选
- **分组管理完善**：分组详情（成员列表+组内统计）、编辑/解散分组、批量分配学生、分组对比视图
- **师生通信系统**（聊天室风格）：教师端左侧会话列表（学生+群组）+右侧气泡聊天区；学生端标签页聊天（我的教师/班级消息）
- **任务系统**：教师创建学习任务（练习/口语/对话/片段四项指标+截止日期），自动为相关学生生成进度快照，答题后自动更新进度
- **公告系统**：全局公告栏（`AnnouncementBar.vue`）在所有页面顶部轮播，可关闭
- **学生互动中心**（`/student/interactions`）：消息聊天室 + 任务进度卡片 + 分组信息
- **教师端 UI 重构**：导航精简为 5 项（管理看板/学生管理/学生消息/任务公告/AI助手）；看板去除学生表格改为快速入口；学生管理页标签式（学生列表+分组管理）
- **看板与学生管理分离**：`/teacher` = 纯看板，`/teacher/students` = 独立学生管理页（含分组管理标签页）
- **Agent 工具大扩展**：
  - 教师 Agent（14 工具）：+`create_task`、`send_announcement`、`send_group_message`、`get_task_progress`、`get_group_stats`、`assign_student_to_group`、`create_group`
  - 学生 Agent（8 工具）：+`get_my_tasks`、`generate_my_report`
- **全局时区修复**：新增 `time_utils.beijing_now()` 替换全部 `datetime.utcnow()`，所有时间戳使用北京时间
- **前端细节修复**：红色按钮 hover 下沉效果、对话消息头像+正确左右方向、按钮白色文字对比度、编辑重发修复、`cancelEdit` 清理 `editText` 时序问题

### v18 (2026-05-10)
- **等级体系反转**：A=高级/C=初级（原 A=初级/C=高级 与 AI 常识相悖），`assign_level`、定级测试结果、CSV 片段难度列全部统一
- **通信系统重构**：消息端点改为时间戳轮询（`GET /messages/poll?since=`）替代 UUID 字符串比较；消息去重用 `sender_id|content|created_at` 组合键，杜绝重复
- **实时通知**：未读计数迁入 Pinia `userStore.unreadCount`，标记已读即时归零；Header 导航栏 `el-badge` 红点 10s 轮询同步
- **消息上下文隔离**：教师轮询按当前会话 `student_id`/`group_id` 过滤，A 对话消息不会串到 B 对话界面
- **聊天 UI 全面统一**：学生端互动中心改为与教师端完全一致的气泡聊天样式（左右头像+绿底/灰底气泡+圆形发送按钮+进出动画），撑满全屏
- **分组管理增强**：分组详情页"添加学生"弹窗 + "移出"功能；侧栏会话列表未读红点徽章
- **任务分组合并**：学生端任务和分组信息整合为悬浮面板（`<teleport>` 毛玻璃弹窗），底部按钮触发
- **公告系统重做**：教师端不显示公告；学生端改为登录弹窗毛玻璃面板 + "已读确认"按钮，`sessionStorage` 记录已读
- **Agent 工具补充**：教师 +`create_group_tool`（14→15 工具）、+`get_group_stats_tool`、+`assign_student_to_group_tool`；提示词明确 A=高级/C=初级
- **时区全面修复**：`time_utils.beijing_now()` 独立模块替代全部 `datetime.utcnow()`，解决循环导入

### v19 (2026-05-10)
- **教师邀请码系统**：每位教师自动生成 4 位字母+数字邀请码，ProfileDialog 可查看复制；学生注册时填写邀请码自动绑定教师+加入分组
- **学生绑定机制**：`UserModel` 新增 `teacher_id`（直接绑定）+ `invite_code`（教师邀请码），替代纯分组间接关联
- **互动中心权限控制**：未绑定教师的学生进入互动中心显示锁定覆盖层，输入邀请码即可绑定；`require_bound_student` 依赖保护所有互动端点
- **分级管理功能**：学生管理页新增"分级管理"标签页——等级统计卡片 + 学生表格（批量选择+一键应用 A/B/C 等级）+ 行内等级按钮即时更新
- **Agent 分级工具**：教师 Agent +`update_student_level_tool`，学情改善时自动升级（C→B, B→A），16 个工具
- **数据隔离修复**：教师仅看到自己分组下的学生，Dashboard/Agent/学生列表全部统一
- **教师邀请码预设**：init 脚本 teacher_wang=W4X9, teacher_li=K2M7，12 名学生预绑定

### v21 (2026-05-12)
- **学习预警面板**：新增 `GET /teacher/students/alerts/list` 端点，教师看板顶部展示预警条（不活跃/正确率骤降/未定级），点击跳转学生详情
- **单词本**（完整功能）：
  - 新增 `user_vocabulary` 数据模型 + 6 个 API 端点
  - 片段对话中点击英文单词弹出查词卡片（DeepSeek 释义），可收藏到单词本
  - 新增 `VocabularyPage.vue` — 列表/排序/复习模式/掌握切换
  - 导航栏新增「单词本」入口
- **口语录音回顾**：教师学生详情抽屉新增口语录音面板，`<audio>` 播放录音 + 评分展示 + AI 反馈
- **口语趋势图**：口语练习页底部新增 ECharts 折线图（总分/准确度/流畅度），`GET /speaking/history` 端点返回 30 天记录
- **流式翻译端点**：`POST /clips/{id}/translate/stream` SSE 流式输出 DeepSeek 翻译

### v20 (2026-05-11)
- **登录角色选择**：落地页和 Vue SPA 登录页均新增学生/教师身份选择，后端 `get_user_by_login` 支持按 `role` 精确匹配，解决师生同名歧义
- **邀请码注册修复**：修复前端 `authApi.register` 丢失 `invite_code` 参数的问题，注册时邀请码正确传递到后端、自动绑定教师和分组
- **邀请码注册修复**：落地页和 Vue SPA 注册表单均修复，选择"教师"身份时隐藏邀请码字段
- **邀请码绑定弹窗**：新建 `BindTeacherDialog.vue`，未绑定学生在仪表盘自动弹出（可跳过/可绑定），绑定后刷新用户状态
- **片断翻译升级为流式大模型翻译**：
  - 新增 `POST /clips/{clip_id}/translate/stream` SSE 流式端点
  - 对话区按钮改为「英文原文」和「大模型翻译」
  - 翻译结果流式逐字输出，写入 localStorage 缓存（刷新不丢）
  - 翻译完成后出现「重新生成」按钮，可重新调用 DeepSeek 翻译
- **多项 Bug 修复**：
  - 修复教师看板 `onGroupChange` 调用已删除的 `loadStudents()` 报错
  - 修复 `el-check-tag` 的 `v-model` 与 `@change` 双重赋值导致中英切换无效
  - 修复未绑定学生 403 轮询报错（`StudentLayout` 未读计数 + `AnnouncementBar` 公告）
  - `UserOut` 暴露 `teacher_id` 供前端判断绑定状态，`LoginRequest` 新增可选 `role`

### v22 (2026-05-12 · 最终版)
- **"我的积累"合并页**：单词本 + 错题本合并为 `AccumulatePage.vue`（Tab 切换），导航/仪表盘统一入口，旧路由自动重定向
- **单词释义修复**：收藏时间步存储 definition，单词列表不再显示"释义加载中..."
- **单词检测模式**：`POST /vocabulary/quiz/generate` DeepSeek 根据个人单词本出选择题，`/quiz/submit` 判对错并联动错题本
- **Agent 工具扩展**：
  - 学生 +2：`get_speaking_trend`（口语趋势）+ `get_smart_review_plan`（复习计划）→ 共 12 工具
  - 教师 +2：`compare_students`（学生对比）+ `get_weekly_digest`（班级周报）→ 共 19 工具
- **查词卡片拖拽**：`word-lookup-card` 支持标题栏拖动，解决长对话底部被遮挡问题
- **多项 Bug 修复**：
  - `init_users.py` 学生缺少 `teacher_id` 导致教师看不到学生列表
  - `bind-invite` 缺少 `TeacherGroupModel` 导入导致 500
  - `VocabSaveRequest` 使用未导入的 `Optional` 导致 500
  - `pages.vue`/`app.js` 重复导出和残留引用修复
- **文档产出**：`项目说明文档.md`（竞赛配套完整说明）+ `docs/progress.md` 最终版更新
