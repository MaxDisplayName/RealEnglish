# RealEnglish v21 功能开发计划书

> 日期: 2026-05-11
> 基于 v20 当前代码状态

---

## 一、当前状态回顾（v20）

v20 完成了以下关键修复和增强：

- 登录页角色选择（学生/教师），后端 `role` 精确过滤
- 邀请码注册链修复（前端→后端完整传递）
- 未绑定教师弹窗引导（`BindTeacherDialog`）
- 片断翻译升级为流式大模型翻译（SSE + localStorage 缓存 + 重新生成）
- 多项 Bug 修复（`loadStudents` 报错、`el-check-tag` 切换、403 轮询等）

---

## 二、计划开发的四个功能

| 序号 | 功能 | 端 | 工作量 | 优先级 |
|------|------|------|--------|--------|
| 1 | 学习预警面板 | 教师 | 中 | P0 |
| 2 | 单词本 | 学生 | 中 | P1 |
| 3 | 口语录音回顾 | 教师 | 中 | P2 |
| 4 | 口语练习历史趋势图 | 学生 | 中 | P3 |

---

## 三、功能一：学习预警面板（教师端）

### 3.1 需求描述

教师看板顶部展示预警条，自动标记三类需要关注的学生，帮助教师在大班教学中快速定位问题学生。

### 3.2 预警规则

| 类型 | 规则 | 颜色 |
|------|------|------|
| 不活跃 | 最近 7 天无任何练习记录 | 橙色 |
| 正确率骤降 | 本周正确率比上周下降 ≥30% | 红色 |
| 未定级 | `level IS NULL` | 灰色 |

### 3.3 后端

**新增端点** `GET /teacher/students/alerts`（`teacher_router`）：

- 查询当前教师绑定学生，逐条判断是否触发预警
- 返回 `{ alerts: [{ student_id, username, type, description }] }`

**涉及文件**：`backend/app/api.py`、`backend/app/crud.py`

### 3.4 前端

**修改文件**：`TeacherDashboardPage.vue`

- 统计卡片下方新增预警条组件
- 3 类预警分 3 条 `el-alert`，每条列出触发学生（点击跳转详情）
- 无预警时整块隐藏

### 3.5 数据依赖

已有数据完全满足：
- `practice_records` 表（答题记录 + `answered_at`）
- `users.level`（定级状态）

无需新建数据表。

---

## 四、功能二：单词本（学生端）

### 4.1 需求描述

学生在观看影视片段时，点击对话中的任意单词可查看 AI 解释，并可收藏到个人单词本。单词本页面支持复习模式。

### 4.2 交互流程

```
对话区点击单词
  → el-popover 弹出：音标 + DeepSeek 中文释义 + 例句 + [收藏] 按钮
  → 已收藏显示 ★，未收藏显示 ☆

导航栏新增「单词本」入口
  → 列表视图（按时间/字母排序，分页）
  → 复习模式（遮住释义，点击显示，标记已掌握/未掌握）
```

### 4.3 后端

**新增模型** `UserVocabularyModel`：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) PK | UUID |
| user_id | FK → users | |
| word | String(100) | 单词原文 |
| clip_id | FK → video_clips | 来源片段（可空）|
| definition | Text | AI 释义 |
| mastered | Boolean | 是否已掌握，默认 false |
| created_at | DateTime | |

**新增端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/student/vocabulary/lookup` | 查单词，调用 DeepSeek 返回释义 |
| POST | `/student/vocabulary/save` | 收藏单词 |
| DELETE | `/student/vocabulary/{id}` | 删除单词 |
| GET | `/student/vocabulary` | 单词列表（分页+排序） |
| PATCH | `/student/vocabulary/{id}/mastered` | 标记已掌握/未掌握 |

**涉及文件**：`backend/app/api.py`、`backend/app/models.py`、`backend/app/crud.py`、`backend/app/schemas.py`

### 4.4 前端

**新建文件**：`frontend/src/pages/VocabularyPage.vue`

**修改文件**：
- `ClipDetailPage.vue` — 对话单词可点击 + popover
- `StudentLayout.vue` — 导航栏加"单词本"链接
- `app.js` — 路由加 `/student/vocabulary`
- `pages.vue` — 注册新页面组件

### 4.5 UI 参考

popover 样式参考现有 `FloatingAssistant.vue` 的卡片风格。单词本页面样式参考错题本 `WrongNotePage.vue` 的列表布局。

---

## 五、功能三：口语录音回顾（教师端）

### 5.1 需求描述

教师在学生详情抽屉中能播放该学生的口语录音，配合 AI 评分反馈，真正了解学生的口语水平。

### 5.2 后端

**修改端点** `GET /teacher/students/{student_id}`：

- 返回数据中新增 `speaking_samples` 字段：最近 5 条口语记录
- 每条包含：`mode`、`reference_text`、`audio_url`、`score_json`、`feedback`、`created_at`

**新增端点** `GET /speaking/{record_id}/audio`：

- 返回口语录音文件（MP3 流），如果存储在本地的 `storage/` 目录

**涉及文件**：`backend/app/api.py`、`backend/app/crud.py`

### 5.3 前端

**修改文件**：`TeacherStudentListPage.vue`

- 学生详情抽屉新增"口语记录"Tab 或折叠面板
- 每条记录：音频播放器（`<audio>` 标签）+ 评分维度展示 + AI 反馈文字
- 评分展示复用 `SpeakingRecorder.vue` 的评分条动画

### 5.4 数据依赖

已有数据完全满足：
- `speaking_records` 表（`audio_url`、`score_json`、`feedback`）

从 `init_users.py` 看已有 87 条口语记录，测试数据充足。

---

## 六、功能四：口语练习历史趋势图（学生端）

### 6.1 需求描述

口语练习页新增 ECharts 折线图，展示学生口语总分/准确度/流畅度的历史变化趋势，让进步可视化。

### 6.2 后端

**新增端点** `GET /student/speaking/history`：

- 返回最近 30 天口语记录（最多 50 条）
- 每条：`mode`、`total_score`、`accuracy`、`fluency`、`integrity`、`created_at`

**涉及文件**：`backend/app/api.py`

### 6.3 前端

**修改文件**：`SpeakingPracticePage.vue`

- 页面底部新增"历史趋势"折叠区域
- ECharts 双折线图：总分趋势 + 三维度分别趋势
- 复用 `DashboardCharts.vue` 的 ECharts 初始化模式

**涉及文件**：`frontend/src/pages/SpeakingPracticePage.vue`

**新建文件**（可选）：`frontend/src/components/SpeakingTrendChart.vue`（如果复用不方便）

### 6.4 数据依赖

已有数据完全满足：
- `speaking_records` 表（`score_json` JSON 字段包含 `total_score`、`accuracy`、`fluency`、`integrity`）

---

## 七、开发顺序

```
Day 1  上午: 功能一「学习预警」（后端 + 前端）
       下午: 功能三「口语录音回顾」（后端 + 前端）

Day 2  上午: 功能二「单词本」后端（模型 + API）
       下午: 功能二「单词本」前端（ClipDetailPage 点击 + VocabularyPage）

Day 3  上午: 功能四「口语趋势图」（后端 + 前端）
       下午: 联调测试 + 文档更新
```

---

## 八、测试验证

### 功能一验证
1. 用 `teacher_wang / pass123` 登录教师端
2. 看板顶部应显示预警条（预期有不活跃/正确率下降的学生）
3. 点击预警学生跳转详情页

### 功能二验证
1. 用学生账号打开片段详情 → 点击对话中的英文单词
2. popover 弹出，显示释义 → 点"收藏"
3. 导航到单词本页面 → 确认单词在列表中
4. 进入复习模式 → 测试掌握/未掌握切换

### 功能三验证
1. 教师进入学生管理 → 点击学生查看详情
2. 详情中有"口语记录"区域 → 点击播放录音
3. 查看评分维度和 AI 反馈

### 功能四验证
1. 学生进入口语练习页 → 页面底部有"历史趋势"
2. 折线图展示练习趋势数据
3. 确认数据与实际练习记录一致

---

## 九、注意事项

1. **功能一**涉及 `TeacherDashboardPage.vue`，注意之前已修复的 `loadStudents` 问题，不要引入类似 bug
2. **功能二**的 popover 点击需要阻止冒泡，避免触发行朗读
3. **功能三**的音频播放注意跨域问题，如果音频在 `storage/` 目录需确认静态文件服务配置
4. **功能四**的图表组件注意在 `onMounted` 之后初始化 ECharts，避免 DOM 未挂载
5. 所有新功能完成后，更新 `Instruction.md` 和 `docs/progress.md`（v21）
