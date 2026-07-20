# 星识 (Star-Learn) 项目完整功能地图

> 本文档列出项目中**每一个功能**对应的**具体代码位置**。
> 按功能模块组织，从前端到后端到AI链路完整贯通。

---

## 目录

- [一、全局基础设施](#一全局基础设施)
- [二、用户系统](#二用户系统)
- [三、AI 问答中心](#三ai-问答中心)
- [四、AI 教师课堂](#四ai-教师课堂)
- [五、苏格拉底对话](#五苏格拉底对话)
- [六、课程中心](#六课程中心)
- [七、学习进度与日历](#七学习进度与日历)
- [八、代码工坊](#八代码工坊)
- [九、个人中心与生态](#十个人中心与生态)
- [十、全息视界 (视频播放器)](#十全息视界-视频播放器)
- [十一、创作工具](#十一创作工具)
- [十二、今日要闻与每日航线](#十二今日要闻与每日航线)
- [十三、AI Agent 编排系统](#十三ai-agent-编排系统)
- [十四、LLM 调用层](#十四llm-调用层)
- [十五、数据层总览](#十五数据层总览)
- [十六、配置文件](#十六配置文件)

---

## 一、全局基础设施

### 1.1 主题系统（壁纸 + 液态玻璃 + 深浅色）

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端核心 | `js/theme.js` | 壁纸状态管理、Modal 弹窗、CSS 变量应用、`window.StarTheme` API |
| 全局样式 | `css/index.css` | `[data-glass="true"]` 液态玻璃规则、`.global-bg-layer` 背景层 |
| Hub 样式 | `css/hub.css` | `.theme-modal-overlay` / `.theme-modal` Modal 样式、壁纸网格、滑块样式 |
| 页面入口 | `html/hub.html` 等 6 个页面 | `#theme-settings-btn` 主题设置按钮 |

**相关后端（可选）**：`app/api/settings.py`（如需要服务端持久化主题设置）

### 1.2 全局加载动画（3D 地球 + 四角星 Spinner）

| 层级 | 文件 | 职责 |
|------|------|------|
| CSS 动画 | `css/loading.css` | `.loading-spinner` 3D 伪元素旋转、`.loading-overlay` 淡出过渡、star-dive 完成动画 |
| JS 控制 | `js/loading.js` | `isLoading` 状态、预加载队列（img + 壁纸 + 头像）、2.5s 超时兜底、`window.LoadingSystem` API |
| SVG 资源 | `static/loader.svg` | 地球 + 45°轨道环 + 四角星 + 尾迹粒子矢量图 |
| 页面覆盖 | 所有 `html/*.html` | `<head>` 中统一引入 `loading.css` + `loading.js` |

### 1.3 前端数据同步层

| 文件 | 职责 |
|------|------|
| `js/sync-engine.js` | 前端状态同步引擎，连接后端 SSE/WebSocket |
| `js/data-layer.js` | 数据抽象层，localStorage ↔ 后端 API 桥接 |
| `js/focus-sync.js` | 专注状态同步 |

---

## 二、用户系统

### 2.1 注册 / 登录

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/login.html` / `html/register.html` | 登录/注册 UI |
| 前端逻辑 | `js/login.js` / `js/register.js` | 表单验证、调用后端 API |
| 后端 API | `main.py:1218` `@app.post("/api/login")` | 登录验证 |
| 后端 API | `main.py:1198` `@app.post("/api/register")` | 用户注册 |
| 数据模型 | `app/models/user.py` | `User` 表（id, username, password_hash, avatar_url...） |
| 数据库 | `db.py` | 传统 pymysql 用户 CRUD |

### 2.2 个人中心

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/personal.html` | 个人资料、学习画像、成就展示 |
| 前端逻辑 | `js/personal.js` | 数据渲染、编辑交互 |
| 后端 API | `main.py:1269` `@app.post("/api/user/update")` | 更新用户信息 |
| 后端 API | `main.py:1292` `@app.post("/api/user/preferences")` | 保存用户偏好 |
| 后端 API | `main.py:1326` `@app.get("/api/user/preferences/{user_id}")` | 读取用户偏好 |
| 后端 API | `main.py:2123` `@app.post("/api/profile/portrait/update")` | 更新学习画像 |
| 后端 API | `main.py:2167` `@app.get("/api/profile/portrait/{user_id}")` | 获取学习画像 |

### 2.3 学习评估问卷

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/assessment.html` | 入学评估问卷 |
| 前端逻辑 | `js/assessment.js` | 问卷逻辑、评分计算 |
| 后端 API | `main.py:2180` `@app.post("/api/assessment/submit")` | 提交评估结果 |

---

## 三、AI 问答中心

### 3.1 主聊天页面 (OpenMAIC 风格)

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/index.html` | 双栏布局：侧边栏 + 聊天主区域 |
| 前端逻辑 | `js/index.js` | 消息渲染、Markdown 解析、代码高亮、主题切换、流式 SSE 消费 |
| 前端样式 | `css/index.css` | 玻璃态 UI、主题变量（ocean/forest/sunset 等 8 套主题）、消息气泡 |
| 前端组件 | `js/link-renderer.js` | 链接卡片渲染 |
| 前端组件 | `js/openmaic-slide-player.js` | 幻灯片播放器 |

### 3.2 V1 聊天 API

| 后端 API | `main.py:2582` `@app.post("/api/chat")` | 非流式单轮聊天 |
| 后端 API | `main.py:2974` `@app.post("/api/v2/chat")` | V2 非流式聊天 |
| 后端 API | `main.py:3020` `@app.post("/api/v2/chat/stream")` | **V2 流式聊天（SSE）** |
| 后端 API | `main.py:3450` `@app.get("/api/chat/history")` | 聊天历史查询 |
| 数据模型 | `state.py:203` `ChatRequestV2` / `ChatResponseV2` | 请求/响应 Pydantic 模型 |
| 数据模型 | `state.py:232` `StreamChatRequest` | 流式请求模型 |

### 3.3 V2 智能体对话 API（Agent 编排）

| 后端 API | `main.py:2974` `@app.post("/api/v2/chat")` | Agent 编排入口 |
| Agent 控制器 | `agents.py:1033` `MasterController` | 统一调度多个 Agent |
| 状态管理 | `state.py:143` `StudentState` | 学生状态上下文（对话历史、知识掌握、学习目标） |
| 状态持久化 | `agent_utils.py` `save_state` / `load_state` | 状态保存/恢复 |
| 上下文管理 | `agent_utils.py` `list_student_contexts` | 多会话上下文列表 |

---

## 四、AI 教师课堂

### 4.1 AI 教师对话管道

这是项目中最复杂的 AI 功能链路，完整数据流如下：

```
前端 (classroom.html)
  ↓ POST /api/v2/teacher/chat  (SSE)
后端 app/api/teacher_chat.py:48
  ↓ TeacherPipeline.run()
后端 app/services/teacher/pipeline.py:49
  ↓ PersonaManager.build_system_prompt()
后端 app/services/teacher/personas.py
  ↓ call_llm_stream_messages() (带 tools)
后端 llm_stream.py:233
  ↓ MiniMax API
  ↓ 返回 SSE 流 (text_delta / action / function_call / function_result)
前端 js/classroom.js 消费 SSE
  ↓ TTS 播放 + 白板绘制 + 字级高亮
```

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/classroom.html` | AI 课堂主界面 |
| 前端逻辑 | `js/classroom.js` | SSE 消费、TTS 播放、白板 SVG 绘制、Action 解析 |
| 前端样式 | `css/classroom.css` | 课堂布局、白板样式 |
| 后端 API | `app/api/teacher_chat.py:48` `@router.post("/chat")` | 文本对话 SSE 入口 |
| 后端 API | `app/api/teacher_chat.py:88` `@router.post("/speech")` | 语音对话入口 |
| 对话管道 | `app/services/teacher/pipeline.py:32` `TeacherPipeline` | 核心管道：组装 Prompt → 调用 LLM → 解析 Action/Function Call → 执行工具 |
| 角色引擎 | `app/services/teacher/personas.py` `PersonaManager` | 4 种教师角色（ patient_tutor / expert_mentor / enthusiastic_coach / strict_master ） |
| 工具执行 | `app/services/teacher/tool_executor.py:21` `ToolExecutor` | 执行 Function Calling：web_search / grade_quiz / generate_outline / search_kb / run_code |
| 功能工具定义 | `app/services/teacher/function_tools.py` | OpenAI 格式的 tools JSON Schema |
| 网络搜索 | `app/services/teacher/web_search.py` | Web 搜索 + 结果格式化 |
| Prompt 构建 | `app/services/teacher/prompt_builder.py` | System Prompt 动态组装 |
| 评分逻辑 | `app/services/teacher/grading.py` | 测验评分 |
| 讨论角色 | `app/services/teacher/discussion_roles.py` | 课堂讨论角色配置 |
| 动作 Schema | `app/services/teacher/action_schemas.py` | UI Action JSON Schema（speech / spotlight / wb_draw_svg 等） |

### 4.2 课堂会话管理

| 后端 API | `app/api/classroom.py` | 课堂会话 CRUD |
| 数据模型 | `app/models/classroom.py` | `ClassroomSession` / `QuizRecord` / `AgentTurnRecord` |

---

## 五、苏格拉底对话

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/socratic-ai.html` | 苏格拉底对话界面 |
| 前端逻辑 | `js/socratic-ai.js` | 对话逻辑、理解度检查点 |
| 前端样式 | `css/socratic-ai.css` | 对话样式 |
| 后端 API | `main.py:1755` `@app.post("/api/socratic/role")` | 获取苏格拉底角色 |
| 后端 API | `main.py:1777` `@app.post("/api/socratic/question")` | 提问生成 |
| 后端 API | `main.py:1798` `@app.post("/api/socratic/score")` | 回答评分 |
| 后端 API | `main.py:1816` `@app.post("/api/socratic/checkpoint")` | 理解度检查点 |
| 后端 API | `main.py:1842` `@app.post("/api/socratic/tts")` | TTS 生成 |
| 后端 API | `main.py:1948` `@app.post("/api/socratic/asr")` | 语音识别 |
| 后端 API | `main.py:2101` `@app.get("/api/socratic/voices")` | 音色列表 |
| Agent | `agents.py:662` `SocraticEvaluatorAgent` | 苏格拉底评估 Agent |

---

## 六、课程中心

### 6.1 学科/课程列表页

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/courses.html` | 可汗学院风格学科分组 + 课程卡片网格 |
| 前端逻辑 | `js/courses.js` | 课程数据加载（后端 API → localStorage 回退）、编辑 Modal、渲染 |
| 前端样式 | `css/courses.css` | 学科区块、课程卡片、编辑面板、B站导入面板样式 |
| 编辑 Modal | `html/courses.html` | 编辑课程面板（液态玻璃） |
| B站导入 | `js/bilibili-import.js` | 三 Tab 导入逻辑（粘贴链接 / 搜索 / 合集） |

### 6.2 课程学习页

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/course-learn.html` | 双栏布局：左侧章节树 + 右侧 B站 iframe + 字幕/讲义/笔记 |
| 前端逻辑 | `js/course-learn.js` | 章节导航、B站播放器控制、字幕同步、Tab 切换、进度保存 |
| 前端样式 | `css/course-learn.css` | 双栏布局、视频容器、字幕时间轴 |

### 6.3 后端课程 API

| 后端 API | `app/api/courses.py:164` `@router.get("/subjects")` | 获取学科列表（含嵌套课程） |
| 后端 API | `app/api/courses.py:170` `@router.post("/subjects")` | 创建学科 |
| 后端 API | `app/api/courses.py:176` `@router.patch("/subjects/{id}")` | 更新学科 |
| 后端 API | `app/api/courses.py:184` `@router.delete("/subjects/{id}")` | 删除学科 |
| 后端 API | `app/api/courses.py:194` `@router.get("/courses/{id}")` | 获取课程详情（含嵌套章节→子章节） |
| 后端 API | `app/api/courses.py:202` `@router.post("/courses")` | 创建课程 |
| 后端 API | `app/api/courses.py:226` `@router.post("/import-bilibili")` | B站视频导入为课程 |
| 后端 API | `app/api/courses.py:234` `@router.post("/import-playlist")` | B站合集导入为课程 |
| 服务层 | `app/services/course_service.py` | Subject / Course / Chapter / SubChapter CRUD |
| 导入编排 | `app/services/course_import.py` | B站视频/合集 → 课程层次结构生成 |
| 数据模型 | `app/models/course.py` | `Subject` / `Course` / `Chapter` / `SubChapter` / `KnowledgePoint` |
| B站 API | `app/services/bilibili.py` | B站视频解析、搜索、合集解析、字幕获取 |
| B站路由 | `app/api/bilibili.py` | `/api/bilibili/parse` / `search` / `playlist` / `subtitles` |
| 数据库迁移 | `alembic/versions/20260529_add_subjects_chapters_subchapters.py` | 课程中心表结构迁移 |

### 6.4 B站导入样式

B站导入的 CSS 样式已包含在 `css/courses.css` 中（`.bilibili-import-panel`、`.im-tab`、`.im-video-row` 等），无需单独文件。

---

## 七、学习进度与日历

### 7.1 学习进度

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/progress.html` | 学习进度可视化 |
| 前端逻辑 | `js/progress.js` | 进度图表渲染 |
| 前端样式 | `css/progress.css` | 进度条、统计卡片 |
| 后端 API | `main.py:1379` `@app.post("/api/progress/save")` | 保存学习进度 |
| 后端 API | `main.py:2470` `@app.post("/api/progress/load")` | 加载学习进度 |

### 7.2 学习日历

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/calendar.html` | 日历视图 |
| 前端逻辑 | `js/calendar.js` | 日历渲染、事件管理 |
| 前端样式 | `css/calendar.css` | 日历网格、事件标记 |

### 7.3 心流共振仪

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/flow-meter.html` | 专注力监测仪表板 |
| 前端逻辑 | `js/flow-meter.js` | 心率/专注度数据可视化 |
| 前端样式 | `css/flow-meter.css` | 心电图风格图表 |
| 后端 API | `main.py:4551` `@app.post("/api/v2/telemetry")` | 遥测数据上报 |
| 后端 API | `main.py:4653` `@app.get("/api/v2/telemetry/{student_id}")` | 遥测数据查询 |

---

## 八、代码工坊

### 8.1 代码编写与运行

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/code.html` | 代码编辑器页面 |
| 前端逻辑 | `js/code.js` | CodeMirror 集成、代码运行、结果展示 |
| 前端样式 | `css/code.css` | 编辑器主题、输出面板 |
| 后端 API | `main.py:2887` `@app.post("/api/run-code")` | 代码执行 |
| 后端 API | `main.py:2913` `@app.post("/api/grade-code")` | 代码评分 |

### 8.2 AI 代码审查

| 后端 API | `main.py:3962` `@app.post("/api/v2/code/review")` | 代码审查 |
| 后端 API | `main.py:4039` `@app.post("/api/v2/code/review/stream")` | 流式代码审查 |

### 8.3 编程题目生成

| 后端 API | `main.py:3692` `@app.post("/api/v2/coding-problem/generate")` | 生成编程题 |
| 后端 API | `main.py:3823` `@app.post("/api/v2/coding-problem/generate/stream")` | 流式生成 |
| 后端 API | `main.py:3880` `@app.post("/api/v2/coding-problem/generate-batch")` | 批量生成 |
| Agent | `agents.py:391` `ExerciseGeneratorAgent` | 练习题生成 Agent |

---

## 九、个人中心与生态

### 9.1 星宝宠物游戏

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/pixel-pet-game.html` | 像素宠物游戏 |
| 前端逻辑 | `js/pixel-pet-game.js` | 宠物养成逻辑 |

### 9.2 我的生态（植物养成）

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/plant.html` | 植物生态页面 |
| 前端逻辑 | `js/plant.js` | 植物生长逻辑 |
| 后端 API | `main.py:5761` `@app.post("/api/garden/save")` | 生态数据保存 |

### 9.3 星云陈列室

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/stellar-showcase.html` | 成就与收藏展示 |
| 前端逻辑 | `js/stellar-showcase.js` | 陈列室交互 |

### 9.4 成就系统

| 前端数据 | `js/achievements-data.js` | 成就定义数据 |
| 前端逻辑 | `js/achievement-manager.js` | 成就解锁逻辑 |
| 后端 API | `main.py:5675` `@app.post("/api/achievements/save")` | 成就数据保存 |

---

## 十、全息视界 (视频播放器)

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/video-player.html` | 视频播放器页面 |
| 前端逻辑 | `js/video-player.js` | 视频播放控制、播放列表 |
| 前端样式 | `css/video-player.css` | 播放器 UI |
| 后端 API | `main.py:701` `@app.get("/api/local-videos")` | 本地视频列表 |
| 后端 API | `main.py:735` `@app.get("/api/video-courses")` | 视频课程列表 |
| 后端 API | `main.py:749` `@app.get("/api/video-courses/{course_id}")` | 视频课程详情 |
| 后端 API | `main.py:779` `@app.post("/api/video-courses")` | 创建视频课程 |
| 后端 API | `main.py:848` `@app.get("/api/video-playlists")` | 播放列表 |
| B站播放 | `main.py:925` `@app.get("/api/bilibili/info")` | B站视频信息 |
| B站播放 | `main.py:953` `@app.get("/api/bilibili/playurl")` | B站播放地址 |
| B站播放 | `main.py:1029` `@app.get("/api/bilibili/stream")` | B站流地址 |

---

## 十一、创作工具

### 11.1 白板绘图

| 层级 | 文件 | 职责 |
|------|------|------|
| 后端 API | `main.py:1113` `@app.post("/api/whiteboard/draw")` | AI 白板绘图（LLM 生成 SVG） |
| 前端渲染 | `js/classroom.js` | 白板 SVG 渲染 |

### 11.2 架构蓝图

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/architecture-blueprint.html` | 架构图设计器 |
| 前端逻辑 | `js/architecture-blueprint.js` | 蓝图绘制逻辑 |
| 前端样式 | `css/architecture-blueprint.css` | 蓝图样式 |

### 11.3 AI 结对编程

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/ai-pair-programming.html` | 结对编程界面 |
| 前端逻辑 | `js/ai-pair-programming.js` | 实时协作逻辑 |
| 前端样式 | `css/ai-pair-programming.css` | 结对编程样式 |

### 11.4 概念分析器

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端页面 | `html/concept-analyzer.html` | 概念分析页面 |
| 前端逻辑 | `js/concept-analyzer.js` | 概念图谱分析 |
| 前端样式 | `css/concept-analyzer.css` | 概念图样式 |

### 11.5 PPT 生成

| 后端 API | `app/api/ppt.py:49` `@router.post("/generate")` | AI 生成 PPT |
| 服务层 | `app/services/ppt/minimax.py` | MiniMax PPT 生成 |
| 服务层 | `app/services/ppt/regenerate_course.py` | 课程 PPT 重生成 |
| 数据模型 | `app/models/course.py` `SceneOutline` / `Slide` | PPT 数据结构 |

---

## 十二、今日要闻与每日航线

### 12.1 今日要闻

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端模块 | `html/hub.html` 内嵌 | 今日要闻卡片网格 |
| 前端逻辑 | `js/hub.js` | 新闻加载、渲染 |
| 后端 API | `main.py:4973` `@app.get("/api/news/today")` | 获取今日新闻 |
| 后端 API | `main.py:5435` `@app.get("/api/news/more")` | 加载更多新闻 |

### 12.2 每日星际航线（学习路线推荐）

| 层级 | 文件 | 职责 |
|------|------|------|
| 前端模块 | `html/hub.html` 内嵌 | 每日学习路线启动组件 |
| 前端逻辑 | `js/hub.js` | 航线节点渲染、进度追踪 |
| 后端 API | `main.py:5122` `@app.post("/api/daily-route/generate")` | 生成每日路线 |
| 后端 API | `main.py:5345` `@app.post("/api/daily-route/complete")` | 完成节点 |
| 后端 API | `main.py:5394` `@app.get("/api/daily-route/status")` | 路线状态 |
| Agent | `agents.py:312` `PlannerAgent` | 学习计划生成 Agent |

---

## 十三、AI Agent 编排系统

所有 AI Agent 定义在 `agents.py` 中，由 `MasterController` 统一调度。

### 13.1 Agent 列表

| Agent 类 | 职责 | 代码位置 |
|----------|------|----------|
| `ProfilerAgent` | 学生画像分析（学习风格、认知水平） | `agents.py:58` |
| `PlannerAgent` | 学习计划生成 | `agents.py:312` |
| `DocumentGeneratorAgent` | 文档/讲义生成 | `agents.py:391` |
| `MindmapGeneratorAgent` | 思维导图生成 | `agents.py:442` |
| `ExerciseGeneratorAgent` | 练习题生成 | `agents.py:509` |
| `VideoContentAgent` | 视频脚本生成 | `agents.py:564` |
| `ResourcePushAgent` | 学习资源推荐 | `agents.py:594` |
| `EvaluationAgent` | 学习效果评估 | `agents.py:624` |
| `SocraticEvaluatorAgent` | 苏格拉底式评估 | `agents.py:662` |
| `FlashcardAgent` | 闪卡生成 | `agents.py:1267` |
| `EchoAgent` | 回显/测试 Agent | `agents.py:1164` |

### 13.2 Agent 控制器

| 文件 | 类/函数 | 职责 |
|------|---------|------|
| `agents.py:1033` | `MasterController` | Agent 注册、调度、编排 |
| `agents.py:1586` | `create_default_controller()` | 创建默认控制器实例 |
| `main.py:4475` | `@app.post("/api/v2/agents/register")` | 动态注册 Agent |
| `main.py:4513` | `@app.get("/api/v2/agents/list")` | 列出已注册 Agent |

### 13.3 任务管理器

| 文件 | 类 | 职责 |
|------|-----|------|
| `task_manager.py` | `AsyncTaskState` / `TaskManager` | 异步任务调度、状态追踪 |
| `main.py:4452` | `@app.get("/api/v2/resource/status/{context_id}")` | 任务状态查询 |

---

## 十四、LLM 调用层

### 14.1 核心 LLM 封装

| 文件 | 函数 | 职责 |
|------|------|------|
| `llm_stream.py:37` | `call_llm_async()` | 非流式单轮调用 MiniMax |
| `llm_stream.py:85` | `call_llm_stream()` | 流式单轮调用 MiniMax |
| `llm_stream.py:189` | `call_llm_async_messages()` | 非流式多轮（完整 messages） |
| `llm_stream.py:233` | `call_llm_stream_messages()` | 流式多轮（完整 messages） |
| `llm_stream.py:153` | `call_llm_stream_with_log()` | 流式调用 + 日志事件 |
| `llm_stream.py:297` | `call_llm_stream_with_log_messages()` | 多轮流式 + 日志 |

### 14.2 LLM 配置

| 文件 | 配置项 | 默认值 |
|------|--------|--------|
| `config/config.py` | `minimax_api_url` | `https://api.minimax.chat/v1` |
| `config/config.py` | `minimax_api_key` | `sk-cp-...` |
| `config/config.py` | `minimax_model_name` | `MiniMax-M2.7` |
| `config/config.py` | `xunfei_api_url` | 讯飞大模型地址 |
| `config/config.py` | `xunfei_api_key` | 讯飞 API Key |
| `config/config.py` | `model_name` | `astron-code-latest` |
| `config/.env` | 环境变量覆盖 | 实际运行时配置 |

### 14.3 语音相关服务

| 服务 | 文件 | 说明 |
|------|------|------|
| TTS | `app/api/tts.py` | TTS API 路由（generate / file / stream / voices） |
| TTS 注册表 | `app/services/tts/registry.py` | TTS 提供商注册中心 |
| TTS MiniMax | `app/services/tts/providers/minimax.py` | MiniMax TTS |
| TTS OpenAI兼容 | `app/services/tts/providers/openai_compat.py` | OpenAI 兼容 TTS |
| ASR | `app/api/asr.py` | 语音识别路由（transcribe / conversation / providers） |
| ASR Whisper | `app/services/asr/providers/whisper.py` | Whisper ASR |
| ASR 百度 | `app/services/asr/providers/baidu.py` | 百度语音识别 |

---

## 十五、数据层总览

### 15.1 数据库模型 (SQLAlchemy ORM)

| 模型文件 | 类 | 表名 | 说明 |
|----------|-----|------|------|
| `app/models/user.py` | `User` | `users` | 用户表 |
| `app/models/user.py` | `StudentProfile` | `student_profiles` | 学生画像 |
| `app/models/course.py` | `Subject` | `subjects` | 学科分类 |
| `app/models/course.py` | `Course` | `courses` | 课程表 |
| `app/models/course.py` | `Chapter` | `chapters` | 章节表 |
| `app/models/course.py` | `SubChapter` | `subchapters` | 子章节（课时）表 |
| `app/models/course.py` | `KnowledgePoint` | `knowledge_points` | 知识点表 |
| `app/models/course.py` | `SceneOutline` | `scene_outlines` | 场景大纲 |
| `app/models/course.py` | `Slide` | `slides` | 幻灯片表 |
| `app/models/classroom.py` | `ClassroomSession` | `classroom_sessions` | 课堂会话 |
| `app/models/classroom.py` | `QuizRecord` | `quiz_records` | 测验记录 |
| `app/models/classroom.py` | `AgentTurnRecord` | `agent_turn_records` | Agent 对话轮次 |
| `app/models/message.py` | `Message` | `messages` | 聊天消息 |
| `app/models/message.py` | `ConversationSummary` | `conversation_summaries` | 会话摘要 |

### 15.2 传统数据库操作 (pymysql)

| 文件 | 说明 |
|------|------|
| `db.py` | 传统 pymysql 数据库操作（用户、进度、成就等旧表） |
| `check_db.py` | 数据库连接检查 |

### 15.3 前端存储

| 文件/Key | 说明 |
|----------|------|
| `localStorage` (`starlearn_theme_v2`) | 主题设置（壁纸、亮度、模糊、深浅色） |
| `localStorage` (`starlearn_courses_data`) | 课程数据缓存 |
| `localStorage` (`starlearn_course_notes`) | 课程笔记 |
| `localStorage` (`starlearn_course_progress`) | 课程进度 |

### 15.4 Alembic 迁移

| 文件 | 说明 |
|------|------|
| `alembic/env.py` | 迁移环境配置 |
| `alembic/versions/b01b4224a404_initial_*.py` | 初始迁移（users/courses/classroom 等） |
| `alembic/versions/20260529_add_subjects_chapters_subchapters.py` | 课程中心表结构迁移 |

---

## 十六、配置文件

| 文件 | 说明 |
|------|------|
| `config/config.py` | Pydantic Settings 配置中心（API Key、模型名、调试开关） |
| `config/.env.example` | 环境变量模板 |
| `config/.env` | 实际环境变量（不提交到 Git） |
| `Navicat/setup_database.py` | 数据库初始化脚本 |

---

## 附：功能 → 代码速查表

如果你想知道**某个具体功能**在哪里实现，按这个表查找：

| 你想找的功能 | 看这里 |
|-------------|--------|
| 换个 LLM 模型 | `config/config.py` → `llm_stream.py`（改 API Key + base_url + model） |
| 改主题 Modal 样式 | `css/hub.css`（搜索 `.theme-modal`） |
| 改课程卡片样式 | `css/courses.css`（搜索 `.course-card`） |
| 加一个新的前端页面 | `html/*.html` + `js/*.js` + `css/*.css` + `main.py` 加路由 |
| 加一个新的后端 API | `app/api/*.py` 新建路由 → `main.py` 注册 |
| 改 AI 教师说话风格 | `app/services/teacher/personas.py`（改 `PERSONAS['xxx'].identity`） |
| 改 AI 教师的工具 | `app/services/teacher/function_tools.py` + `tool_executor.py` |
| 改聊天界面的主题色 | `css/index.css`（搜索 `[data-theme="ocean"]`） |
| 改加载动画 | `css/loading.css` + `js/loading.js` + `static/loader.svg` |
| 改 B站视频解析逻辑 | `app/services/bilibili.py` |
| 数据库加表 | `app/models/*.py` 定义模型 → `alembic revision --autogenerate` |
| 改学生画像算法 | `agents.py` `ProfilerAgent` |
| 改每日路线推荐 | `agents.py` `PlannerAgent` + `main.py` `/api/daily-route/generate` |
