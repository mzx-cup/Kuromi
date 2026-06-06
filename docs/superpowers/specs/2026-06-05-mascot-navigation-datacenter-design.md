# 星识项目全面深化改造设计文档

> **范围**: Phase 3-5（2D 看板娘 + 导航重构 + 知域迁移）
> **日期**: 2026-06-05
> **状态**: 设计已确认（v1.1 修订）

---

## 目录

- [Phase 3: 2D 看板娘 AI 助手](#phase-3-2d-看板娘-ai-助手)
- [Phase 4: 双通道导航重构](#phase-4-双通道导航重构)
- [Phase 5: 知域迁移（教师端 + 数据大屏）](#phase-5-知域迁移教师端--数据大屏)
- [技术约束与兼容性](#技术约束与兼容性)
- [错误处理与降级策略](#错误处理与降级策略)
- [实施优先级](#实施优先级)

---

## Phase 3: 2D 看板娘 AI 助手

### 目标

创建一个 2D 看板娘角色"小星"，完整复刻参考项目"小慧"的 AI 助手功能（语音对话、页面导航、网页总结、情绪识别），使用星识现有技术栈（原生 JS + Python FastAPI）。

### 架构概览

```
┌────────── 星识前端 ──────────┐    ┌──── 星识后端 ────┐
│                               │    │                   │
│  ┌── 2D 看板娘渲染层 ──────┐  │    │  /api/mascot/     │
│  │ Live2D SDK (CDN)        │  │    │   ├── stt         │
│  │ 模型: Senko / Shizuku   │  │    │   ├── chat (SSE)  │
│  │ 表情参数: ParamEyesOpen  │  │    │   ├── tts         │
│  │         ParamMouthOpen   │  │    │   └── emotion     │
│  │ CSS 后备: 3D 视差 + PNG │  │    │                   │
│  └──────────────────────────┘  │    │ 复用已有：        │
│               ↕                 │    │ AI问答V2流式对话   │
│  ┌── 看板娘控制器 ──────────┐  │    │ 苏格拉底教学       │
│  │ 语音录制 (MediaRecorder) │──┼───→│ 课程生成            │
│  │ 语音播放 (AudioContext)  │←─┼───│                   │
│  │ 对话状态管理             │  │    │                   │
│  │ 指令解析 + 导航跳转      │  │    │                   │
│  │ 摄像头情绪采集(可选)     │  │    │                   │
│  └──────────────────────────┘  │    └───────────────────┘
└───────────────────────────────┘
```

### 角色形象与动画技术选型

**主方案：复用项目已有的 Live2D 系统**

星识项目已具备完整的 Live2D 看板娘基础设施（`js/kanban.js` + `css/components.css`），直接升级复用：

| 组成部分 | 当前状态 | Phase 3 改造 |
|----------|----------|--------------|
| Live2D SDK | CDN 加载（Cubism 2.1 SDK） | 保留，增加 Cubism 4 SDK 兼容 |
| 角色模型 | Senko / Shizuku（CDN 免费模型） | 保留作为默认角色，增加角色切换入口 |
| 渲染方式 | Canvas 渲染 + requestAnimationFrame | 保留 |
| 静态后备 | `/static/kanban.png`（**缺失**） | 补充 PNG 角色立绘作为 Live2D 加载失败的后备 |
| 对话气泡 | 已有 CSS 气泡样式（`.app-kanban-bubble`） | 增强：支持流式逐字显示 + Markdown 渲染 |
| 3D 视差 | 已有鼠标跟踪视差效果 | 保留 |

**后备方案：如 CDN 模型不可用**

- 使用 `static/kanban.png` 作为静态立绘（CSS 动画表达 4 种表情：透明度/缩放/旋转过渡）
- 或从 Live2D 社区免费模型库（如 Live2D Cubism Samples）下载本地备用模型

**表情与动作映射：**

Live2D 模型通过参数（Parameter）控制表情，不同模型参数名可能不同，通过适配层统一：

| 表情 | 触发条件 | Live2D 参数调整 | CSS 后备 |
|------|----------|----------------|----------|
| 微笑(默认) | 空闲/打招呼/回复完成 | ParamMouthOpen=0.3, ParamEyeLOpen/ROpen=1.0 | 正常 PNG，微微 scale 动画 |
| 思考 | LLM 处理中 / 等待回复 | ParamEyeLOpen/ROpen=0.5, 头部倾斜 | 歪头 + 省略号气泡 |
| 惊讶 | 识别到用户语音/新消息 | ParamEyeLOpen/ROpen=1.5, ParamMouthOpen=0.8 | 眼睛区放大 + 身体后仰 |
| 鼓励 | 用户完成任务/答对/里程碑 | 快速眨眼 + 跳跃 | 举手 + 星星粒子特效 |

| 动作 | 触发条件 | 实现方式 |
|------|----------|----------|
| 招手 | 用户首次打开页面 / 长时间未交互后返回 | Live2D motion 组播放 |
| 注视 | 鼠标靠近看板娘区域 | 现有 3D 视差跟踪 |
| 小憩 | 5 分钟无交互 | 呼吸动画（闭眼缓动） |

### 交互模式

**模式 1：角落驻留（默认）**
- 位置：页面右下角，固定定位，120×120px 区域
- 行为：Live2D 角色静默显示默认表情，鼠标悬停放大到 150px
- 有新消息时弹出气泡提示（如"有新的学习提醒~"）
- z-index 低于模态框，高于页面内容

**模式 2：对话面板（点击展开）**
- 从右下角弹出 360×480px 对话面板
- 包含：对话历史（滚动）+ 输入框 + 语音按钮（需用户点击授权）+ 发送按钮
- 角色头像在面板顶部，表情随对话内容实时变化
- 支持文字输入和语音输入两种方式
- 语音输入流程：用户点击麦克风按钮 → 浏览器弹出权限请求 → 用户授权 → MediaRecorder 开始录制
- 点击面板外区域或关闭按钮收起

**模式 3：全屏伴学（课程页面专用）**
- 课程学习页面右侧伴学面板，宽度约 320px
- 角色在顶部，下方显示 AI 导师的实时指导
- 根据课程内容自动推送提示（如"注意这里的关键概念"）
- 用户可以主动提问，不影响课程播放

### 功能闭环

| 功能 | 前端实现 | 后端 API | 说明 |
|------|----------|----------|------|
| 语音输入 | `MediaRecorder` → WAV Blob（需用户点击授权） | `POST /api/mascot/stt` | 复用星识已有 STT 服务 |
| 文字对话 | SSE 流式消费 | `POST /api/mascot/chat/stream` | 复用 V2 流式对话管线 |
| 语音输出 | `new Audio(url)` 播放 | `POST /api/mascot/tts` | 复用星识已有 TTS 服务 |
| 网页导航 | 解析指令标签 → `window.location` | 无（纯前端） | 继承"小慧"指令协议 |
| 页面总结 | 传入 `pageContext` 到 LLM | 同上 chat 端点 | 根据当前页面描述生成总结 |
| 情绪识别 | 摄像头 → Canvas → Blob | `POST /api/mascot/emotion` | 百度/讯飞人脸分析 API（可选） |
| 角色动画控制 | Live2D 参数 + motion 切换 | 无（前端驱动） | 根据对话状态和指令触发 |

### 指令协议

LLM 回复中使用 XML 标签控制看板娘行为，前端 `js/mascot.js` 解析并执行：

```xml
<网站指令>打开课程中心</网站指令>    → 路由跳转
<网站指令>打开个人中心</网站指令>    → 路由跳转
<表情>开心</表情>                    → Live2D 参数切换 / CSS 动画
<表情>思考</表情>                    → Live2D 参数切换 / CSS 动画
<动作>鼓励</动作>                    → Live2D motion 播放 + 粒子特效
<动作>招手</动作>                    → Live2D motion 播放
<打开链接>url</打开链接>            → window.open(url)
```

指令在 SSE 流式回复中与普通文本混合，前端实时解析剥离标签后渲染纯文本。

### System Prompt 设计

看板娘使用独立的 System Prompt（不同于普通 AI 问答）：

```
你是"小星"，星识学习平台的 AI 看板娘助手。

角色设定：活泼可爱的女高中生风格，热爱学习，擅长鼓励。
年龄感：16-18 岁，语气自然不做作。

核心职责：
1. 回答学习问题（调用平台知识库）
2. 帮助用户导航平台功能
3. 在课程学习时提供伴学指导
4. 提醒学习进度和任务

对话风格：
- 日常闲聊：活泼亲切，每次 2-3 句话
- 专业问答：切换到认真模式，详细解答
- 导航请求：回复包含 <网站指令> 标签
- 鼓励场景：回复包含 <表情> 和 <动作> 标签
- 学习提醒：温和提醒，不催促

行为规范：
- 不回答政治敏感问题（安全护栏拦截）
- 不生成暴力/色情内容
- 不确定时诚实说不知道
- 记住用户的偏好和之前聊过的话题
```

### 技术实现

**前端文件：**
- `js/mascot.js` — 看板娘控制器（全局单例），在现有 `js/kanban.js` 基础上扩展
- `css/mascot.css` — 看板娘样式 + CSS 动画 + 粒子特效 + 对话面板样式
- `static/kanban.png` — 角色静态立绘（Live2D 加载失败时的后备，**需新建/补充**）
- Live2D 模型文件（CDN 加载，无需本地存储）：
  - Senko: `https://cdn.jsdelivr.net/gh/Eikanya/Live2d-model/Live2D/Senko_Normals/senko.model3.json`
  - Shizuku: `https://cdn.jsdelivr.net/npm/live2d-widget-model-shizuku@latest/assets/shizuku.model.json`

**后端文件：**
- `app/api/mascot.py` — 看板娘专属 API 路由
- 复用：`llm_stream.py`（流式对话）、`agent_utils.py`（TTS/STT）

**初始化流程：**
1. 页面加载 → 创建 MascotController 实例
2. 加载 Live2D SDK + 模型文件（CDN）→ 渲染角色到右下角
3. Live2D 加载失败 → 降级使用 `static/kanban.png` 静态立绘 + CSS 动画
4. 检查 localStorage 是否有用户画像 → 无则首访时提示
5. 建立 SSE 长连接（接收服务端推送消息）

**页面集成：**
- 所有页面在 `<head>` 中引入 `mascot.css`
- 在所有页面的 `<body>` 末尾引入 `mascot.js`
- 看板娘作为全局组件，不干扰各页面独立逻辑

---

## Phase 4: 双通道导航重构

### 目标

解决星识 hub 侧边栏功能入口过多（12 项）导致新用户认知负荷高的问题，建立"精简导航 + AI 入口"的双通道模型。

### 当前侧边栏结构

```
核心功能：AI问答、全息视界
学习中心：课程中心、学习进度、学习日历
创作工具：代码工坊
探索体验：智脑苏格拉底、我的生态、星云陈列室、心流共振仪
个人：个人中心、设置
─────────────────────────────
共 12 个导航项，5 个分组
```

### 新侧边栏结构（精简为 5 项）

```
┌────────────────────┐
│ 🏠 首页             │  Hub 总览（保留）
│────────────────────│
│ 💬 AI 问答          │  统一入口，内嵌：
│                    │   苏格拉底教学（原 智脑苏格拉底）
│                    │   代码编辑器（原 代码工坊）
│                    │   视频播放（原 全息视界）
│────────────────────│
│ 我的课程         │  统一入口，内嵌：
│                    │   已生成课程列表（原 课程中心）
│                    │   学习进度视图
│                    │   学习日历视图（原 学习日历）
│────────────────────│
│ 学习数据         │  统一入口，内嵌：
│                    │   学习分析大屏
│                    │   能力雷达图
│                    │   知识图谱
│────────────────────│
│ 👤 个人中心         │  聚合入口，内嵌：
│                    │   个人资料 + 设置（原 设置）
│                    │   成就展示（原 星云陈列室）
│                    │   学习生态（原 我的生态）
│                    │   心流数据（原 心流共振仪）
└────────────────────┘

看板娘"小星"（右下角常驻）— 所有 AI 交互入口
```

### 页面合并方案（AJAX 动态加载）

**合并方式：AJAX 动态加载 + 组件化嵌入**

明确选择 **AJAX 动态加载**（非 iframe），原因：
- 更好的 UX：无滚动冲突、样式统一、JS 可通信
- 与星识现有主题系统无缝集成（CSS 变量继承）
- 看板娘控制器可直接与嵌入内容交互

**实施策略**：将原独立页面重构为"内容组件"——每个旧页面提取其核心内容区域，作为 HTML片段 / JS 渲染函数，由聚合页面的 Tab/面板容器动态加载。

**页面 ID 隔离**：各嵌入组件使用独立的 ID 命名空间（如 `data-section="socratic"`），避免 CSS/JS 冲突。

| 原独立页面 | 合并到 | 合并方式 |
|------------|--------|----------|
| 智脑苏格拉底.html | AI 问答 | 提取苏格拉底对话 UI 为独立组件，AI 问答页检测意图后动态加载到对话面板 |
| 全息视界.html | AI 问答 | 视频播放器组件化，AI 对话中需要播放视频时内嵌 |
| 代码工坊.html | AI 问答 | CodeMirror 编辑器组件化，AI 对话中需要写代码时内嵌 |
| 课程中心.html | 我的课程 | 作为课程列表子视图，通过 Tab 切换加载 |
| 学习进度.html | 我的课程 | 课程详情页中内嵌进度视图组件 |
| 学习日历.html | 我的课程 | 课程详情页中内嵌日程视图组件 |
| 心流共振仪.html | 学习数据 | 数据大屏中内嵌心流状态组件 |
| 星云陈列室.html | 个人中心 | 成就展示整合进个人中心 Tab |
| 我的生态.html | 个人中心 | 学习生态整合进个人中心 Tab |
| 设置.html | 个人中心 | 个人中心中的设置 Tab/面板 |

> **兼容性策略**：原独立页面文件保留不动（避免外部链接断裂）。每个旧页面的 `<body>` 中添加重定向脚本：检测是否在 iframe 中加载，若被直接访问则 `window.location` 跳转到新聚合页面 + 对应 hash/Tab。

### 全局命令搜索框

顶部搜索框升级为统一命令中心（`⌘K` 快捷键）：

```
┌──────────────────────────────────────────────┐
│ 🔍 搜索课程、功能或输入指令...         ⌘K   │
├──────────────────────────────────────────────┤
│ 分组: 课程                                   │
│   Python数据分析实战 · 进度 60%              │
│   机器学习入门 · 进度 30%                     │
│                                              │
│ 分组: 功能                                   │
│   生成新课程 → AI问答                         │
│   查看学习数据 → 学习数据                     │
│   代码工坊 → AI问答                           │
│                                              │
│ 分组: 快捷操作                               │
│   继续上次的学习...                           │
│   复习第3章：Pandas数据清洗                   │
└──────────────────────────────────────────────┘
```

**前端实现**：
- 新建 `js/search-command.js`，基于 Fuse.js（模糊搜索库，~15KB gzipped）
- 索引内容：页面路由 + 课程名称 + 功能名称 + 用户最近活动
- 结果排序：精确匹配 > 模糊匹配 > 最近使用

### 新手引导系统

用户首次访问 hub 时的引导流程：

```
Step 1: 看板娘招手动画 + Toast "欢迎来到星识！我是小星~"
Step 2: 引导填写学习画像（3-4 个关键问题，可选跳过）
Step 3: Spotlight Tour（3步，高亮 + 遮罩）：
  ① 💬 AI问答 → "在这里，你可以和AI对话、生成课程、写代码"
  ② 我的课程 → "所有AI生成的课程都在这里"
  ③ 🤖 看板娘 → "随时点击右下角呼叫我，语音或打字都可以"
Step 4: 引导结束，遮罩消失，自由探索
```

**前端实现**：
- 新建 `js/onboarding.js`
- 支持查询参数跳过：`?skip-onboarding=1`
- 引导状态存储在 localStorage：`starlearn_onboarding_completed`
- 导航栏增加"帮助"按钮可随时重新触发引导

### AI 导航集成

看板娘和 AI 问答共享导航路由能力：

| 用户输入 | 系统行为 |
|----------|----------|
| "帮我生成一门 Python 课" | 进入脑暴式课程生成（跳转 AI 问答页面并预填） |
| "打开我的课程" | `window.location = '/html/my-courses.html'` 或修改 hub hash |
| "我上次学到哪了" | 查询学习记录 → 直接打开课程详情 + 定位到上次位置 |
| "今天有什么学习任务" | 查询日程 → 在看板娘对话面板中展示今日任务列表 |
| "帮我复习 Pandas" | AI 问答切换到苏格拉底模式 + RAG 加载教材 |
| "我想写代码练习" | AI 问答中内嵌打开代码编辑器 |
| "看看我的学习数据" | 跳转到学习数据页面 |

导航意图识别流程：
1. 用户输入 → LLM 判断是否为导航意图
2. 若是导航意图 → LLM 返回 `<网站指令>` 标签
3. 前端解析标签 → 执行路由跳转
4. 无需跳转 → 走正常 AI 对话流程

### 实现文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `html/hub.html` | 修改 | 精简侧边栏 HTML 结构，旧页面添加重定向脚本 |
| `css/hub.css` | 修改 | 精简侧边栏样式调整 |
| `js/hub.js` | 修改 | 导航逻辑更新 |
| `js/search-command.js` | 新建 | 全局搜索命令中心（Fuse.js） |
| `css/search-command.css` | 新建 | 搜索面板样式 |
| `js/onboarding.js` | 新建 | 新手引导系统 |
| `css/onboarding.css` | 新建 | 引导遮罩和 spotlight 样式 |

---

## Phase 5: 知域迁移（教师端 + 数据大屏）

### 目标

将知域项目（Vue3 + Spring Boot）的教师端和数据可视化大屏功能，用星识技术栈（原生 HTML/JS/CSS + Python FastAPI + PyMySQL）完整重写。

### 迁移对照表

```
知域 (Vue + Spring Boot)              星识 (原生JS + Python)
──────────────────────────            ────────────────────────
认证系统：
  LoginModal.vue              →        html/login.html（独立登录页）
  auth.js (Pinia store)       →        js/auth.js（原生 JS，localStorage 管理）
  AuthInterceptor.java        →        FastAPI 中间件 / Depends
  JwtTokenProvider.java       →        Python PyJWT / python-jose

教师端：
  TeacherDashboard.vue       →        html/teacher-dashboard.html
  TeacherAssistant.vue       →        合并到看板娘 + AI问答
  TeacherExam.vue            →        html/teacher-exam.html
  TeacherManage.vue          →        html/teacher-manage.html
  ClassManagement.vue        →        html/teacher-class.html
  ContentManagement.vue      →        html/teacher-content.html
  AIContentReview.vue        →        html/teacher-content.html（内嵌审核 Tab）

数据大屏：
  DataCenter.vue             →        html/data-dashboard.html

AI助手（不参考知域，参考"小慧"项目）：
  AIFloatingBall.vue         →        被 Phase 3 2D 看板娘替代
  AIDialogBar.vue            →        被 Phase 3 看板娘对话面板替代
```

### 认证体系设计（移植自知域）

星识目前没有独立的教师登录页面。Phase 5 将移植知域的 JWT 认证体系：

**前端（原生 JS）：**

| 组件 | 文件 | 说明 |
|------|------|------|
| 登录页面 | `html/login.html` | 移植知域 LoginModal 为独立页面，含角色选择（学生/教师），可选快速登录按钮 |
| 认证模块 | `js/auth.js` | JWT 管理：login/logout/fetchMe，token 存储在 `localStorage('sp_token')` |
| HTTP 拦截器 | `js/http-intercept.js` | 包装 fetch/XHR，自动附加 `Authorization: Bearer` 头，401 时跳转登录页 |

**后端（Python FastAPI）：**

| 组件 | 文件 | 说明 |
|------|------|------|
| JWT 工具 | `app/utils/jwt.py` | PyJWT 生成/验证，荷载：`{uid, username, role}`，与知域保持一致 |
| 认证中间件 | `app/middleware/auth.py` | FastAPI Depends，解析 Bearer token，注入 `current_user` |
| 角色守卫 | `app/middleware/roles.py` | `@require_role("teacher")` 装饰器，检查 role 字段 |
| 白名单路径 | — | `/api/auth/login`, `/api/auth/register` 等公开端点不校验 token |

**认证流程：**

```
用户访问教师页面 → 检测无 token → 重定向到 /html/login.html
→ 输入用户名/密码 → POST /api/auth/login
→ 后端验证密码(SHA-256 hash) → 返回 JWT token + 用户信息
→ 前端存储 token 到 localStorage('sp_token')
→ 后续请求自动附带 Authorization: Bearer <token>
→ 401 响应 → 清除 token → 跳转登录页
```

**三种角色**（与知域一致）：`student`、`teacher`、`admin`

**安全说明**：知域使用 SHA-256（未加盐）哈希密码，迁移到星识时保持一致的验证逻辑（兼容已有用户数据）。后续可升级为 bcrypt。

### 教师端页面结构

#### 1. 教师仪表盘（teacher-dashboard.html）

```
┌─ 教师工作台 ────────────────────────────┐
│  [统计卡片行]                                │
│  ┌────────┬────────┬────────┬────────┐      │
│  │授课班级│在授课程│待批改   │平均成绩 │      │
│  │  3个   │  2门   │ 15份   │  82分  │      │
│  └────────┴────────┴────────┴────────┘      │
│                                              │
│  ┌─ 班级学习概览 ──┐  ┌─ 最近任务 ────────┐  │
│  │ [ECharts 柱状图]│  │ 第3章作业      │  │
│  │ 各班级进度对比  │  │    提交 28/35     │  │
│  │                 │  │ 期中测试       │  │
│  │                 │  │    待批改 10份    │  │
│  └─────────────────┘  └───────────────────┘  │
│                                              │
│  ┌─ 学生能力雷达 ──┐  ┌─ AI 教学建议 ────┐  │
│  │ [ECharts 雷达图]│  │ ⚠️ 3班进度落后   │  │
│  │ 编程/理论/实践  │  │ 💡 建议为李四补课│  │
│  └─────────────────┘  └───────────────────┘  │
└──────────────────────────────────────────────┘
```

#### 2. 班级管理（teacher-class.html）

- 班级列表 + 创建/编辑/删除
- 学生花名册（支持 CSV 批量导入）
- 班级分组管理
- 学生个人学习档案查看

#### 3. 题库管理（teacher-manage.html）

- 题目 CRUD，支持 4 种题型：选择/填空/编程/简答
- 分类标签 + 难度标签（易/中/难）
- 批量导入（CSV/JSON 格式）
- 题目搜索和筛选

#### 4. 考试管理（teacher-exam.html）

- 创建考试：手动选题 / AI 自动组卷
- 设置考试时间、时长、参与班级
- 发布/撤销/归档考试
- 成绩查看与批改
- 成绩分析：分数分布、各题正确率、班级对比

#### 5. 内容管理（teacher-content.html）

- 课程大纲编辑（树形结构拖拽排序）
- 教案审核与发布
- 教学资源上传与管理
- **AI 内容审核**（从知域移植）：AI 生成课程讲义草稿 → 教师人工审核（批准/拒绝）→ 批准后发布。此功能与 Phase 1 的 AI 安全护栏性质不同——这是教师对 AI 生成教学内容的质量把关，而非用户输入内容的安全过滤。

### 考试自动批改策略

参考星识代码工坊（`main.py` `/api/grade-code` 端点）的 LLM 评估模式，以及 `/api/run-code` 的 subprocess 执行模式：

| 题型 | 批改方式 | 实现 |
|------|----------|------|
| **选择题** | 自动批改 | 答案字符串精确匹配（key-value 比对） |
| **填空题** | 自动批改 | 答案字符串匹配（支持多个等价答案、忽略空白大小写） |
| **编程题** | AI 辅助批改 → 教师审核 | ① `subprocess.run` 执行代码（10s 超时，复用现有 `/api/run-code` 逻辑）② LLM 评估代码质量（0-100 评分，复用现有 `/api/grade-code` 提示词模式）③ 生成预评分 + 评语 → 教师确认或修改 |
| **简答题** | AI 辅助批改 → 教师审核 | LLM 语义相似度评估（对比学生答案与参考答案）→ 生成预评分 + 评语 → 教师确认或修改 |

**教师审核流程**：AI 生成预评分后，教师可在批改界面查看每道题的 AI 评分和评语，直接确认或手动修改分数。所有最终分数以教师确认为准。

### 数据可视化大屏（data-dashboard.html）

```
┌─ 星识数据中台 ────────────────────────────┐
│  [学校] [学院/专业] [班级] [个人]  ← 层级Tabs    │
│                                                │
│  ┌─────────┬─────────┬─────────┬─────────┐     │
│  │总课程│学生数│完成率 │总学时│     │
│  │  128   │ 3,562  │ 78.5%  │45,620h │     │
│  └─────────┴─────────┴─────────┴─────────┘     │
│                                                │
│  ┌─ 学习投入趋势 ────┐ ┌─ 完成率分布 ───────┐  │
│  │ [面积图 + 折线图] │ │ [环形比例 + 柱状图]│  │
│  │ 近30天学习时长    │ │ 已完成/进行中/未开始│  │
│  └───────────────────┘ └────────────────────┘  │
│                                                │
│  ┌─ 分布地图/柱状图 ──┐ ┌─ 能力维度雷达 ────┐  │
│  │ [ECharts 地图]    │ │ [多维度雷达图]     │  │
│  │ 各省/各学院分布   │ │ 综合/编程/数学...  │  │
│  └───────────────────┘ └────────────────────┘  │
│                                                │
│  ┌─ 实时学习动态 ────────────────────────────┐ │
│  │ 🟢 张三 完成了 Python第3章 · 2分钟前      │ │
│  │ 🔵 李四 开始学习 机器学习入门 · 5分钟前   │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

**图表库**：ECharts（纯 JS，与知域一致，无框架依赖）
**数据刷新**：SSE 流推送实时动态，图表数据定时轮询或手动刷新
**主题适配**：使用星识 CSS 变量适配深浅色主题
**层级切换**：学校 → 学院/专业 → 班级 → 个人，每级不同聚合粒度

### 后端新增 API

#### 认证 API（`app/api/auth.py`）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录，返回 JWT token + 用户信息 |
| POST | `/api/auth/register` | 注册（默认 student 角色） |
| GET | `/api/auth/me` | 获取当前用户信息（需认证） |
| PUT | `/api/auth/me` | 更新当前用户信息（需认证） |

#### 教师端 API（`app/api/teacher.py`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/teacher/dashboard` | 仪表盘统计汇总 |
| GET | `/api/teacher/classes` | 班级列表 |
| POST | `/api/teacher/class` | 创建班级 |
| PUT | `/api/teacher/class/{id}` | 编辑班级 |
| DELETE | `/api/teacher/class/{id}` | 删除班级 |
| GET | `/api/teacher/students/{class_id}` | 班级学生花名册 |
| POST | `/api/teacher/students/import` | 批量导入学生（CSV） |
| GET | `/api/teacher/questions` | 题库列表（支持筛选） |
| POST | `/api/teacher/question` | 创建题目 |
| PUT | `/api/teacher/question/{id}` | 编辑题目 |
| DELETE | `/api/teacher/question/{id}` | 删除题目 |
| POST | `/api/teacher/questions/import` | 批量导入题目 |
| GET | `/api/teacher/exams` | 考试列表 |
| POST | `/api/teacher/exam` | 创建考试（手动/AI组卷） |
| PUT | `/api/teacher/exam/{id}` | 编辑考试 |
| DELETE | `/api/teacher/exam/{id}` | 删除考试 |
| POST | `/api/teacher/exam/{id}/publish` | 发布考试 |
| GET | `/api/teacher/exam/{id}/results` | 考试成绩列表 |
| POST | `/api/teacher/exam/{id}/grade` | AI 预批改某份答卷 → 返回预评分供教师审核 |
| PUT | `/api/teacher/exam/{id}/grade` | 教师确认/修改最终分数 |
| GET | `/api/teacher/exam/{id}/analysis` | 成绩统计分析 |
| POST | `/api/teacher/content/generate` | AI 生成课程讲义草稿 |
| GET | `/api/teacher/content/reviews` | 待审核列表 |
| POST | `/api/teacher/content/review/{id}/approve` | 批准内容（发布课程） |
| POST | `/api/teacher/content/review/{id}/reject` | 拒绝内容 |

#### 数据大屏 API（`app/api/datacenter.py`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/datacenter/overview` | 总览统计（学校/学院/班级/个人） |
| GET | `/api/datacenter/trends` | 学习投入趋势数据 |
| GET | `/api/datacenter/distribution` | 分布数据（地域/学院/课程） |
| GET | `/api/datacenter/radar` | 能力维度雷达数据 |
| GET | `/api/datacenter/realtime` | 实时学习动态（SSE） |

### 数据库新增表

```sql
-- 用户认证表（扩展已有用户表，与知域 sp_user 结构兼容）
CREATE TABLE sp_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'student',
    display_name VARCHAR(64) NOT NULL,
    avatar_url VARCHAR(256) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 班级表
CREATE TABLE classes (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    teacher_id INTEGER NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    student_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 班级-学生关联表
CREATE TABLE class_students (
    class_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (class_id, student_id)
);

-- 题库表
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    teacher_id INTEGER NOT NULL,
    type VARCHAR(20) NOT NULL,        -- choice/blank/code/essay
    content TEXT NOT NULL,             -- 题干
    options JSON DEFAULT NULL,         -- 选项（选择题）
    answer TEXT NOT NULL,              -- 正确答案
    difficulty VARCHAR(10) DEFAULT 'medium',  -- easy/medium/hard
    tags JSON DEFAULT NULL,            -- 标签数组
    course_id INTEGER DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 考试表
CREATE TABLE exams (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    teacher_id INTEGER NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT DEFAULT '',
    questions_json JSON NOT NULL,      -- 题目ID数组 + 分值配置
    class_ids_json JSON NOT NULL,      -- 参与班级ID数组
    start_time TIMESTAMP DEFAULT NULL,
    end_time TIMESTAMP DEFAULT NULL,
    duration INTEGER DEFAULT 120,      -- 考试时长（分钟）
    status VARCHAR(20) DEFAULT 'draft', -- draft/published/closed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 考试成绩表
CREATE TABLE exam_results (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    exam_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    answers_json JSON NOT NULL,         -- 学生作答
    score DECIMAL(5,1) DEFAULT NULL,
    ai_score DECIMAL(5,1) DEFAULT NULL, -- AI 预评分
    ai_comment TEXT DEFAULT NULL,        -- AI 评语
    graded_by VARCHAR(50) DEFAULT 'auto', -- auto/manual teacher_id
    graded_at TIMESTAMP DEFAULT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 内容审核表
CREATE TABLE content_reviews (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    lesson_id BIGINT NOT NULL,
    ai_draft_json LONGTEXT NOT NULL,     -- AI 生成的讲义 JSON
    status VARCHAR(32) DEFAULT 'pending', -- pending/approved/rejected
    reviewer_id BIGINT DEFAULT NULL,
    reviewed_at DATETIME DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 数据快照表（大屏聚合缓存）
CREATE TABLE data_snapshots (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    dimension VARCHAR(50) NOT NULL,     -- school/department/class/student
    snapshot_json JSON NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 前端文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `html/login.html` | 新建 | 登录/注册页面（移植自知域 LoginModal） |
| `html/teacher-dashboard.html` | 新建 | 教师仪表盘 |
| `html/teacher-class.html` | 新建 | 班级管理 |
| `html/teacher-manage.html` | 新建 | 题库管理 |
| `html/teacher-exam.html` | 新建 | 考试管理（含批改界面） |
| `html/teacher-content.html` | 新建 | 内容管理（含 AI 内容审核 Tab） |
| `html/data-dashboard.html` | 新建 | 数据可视化大屏 |
| `js/auth.js` | 新建 | 认证模块（login/logout/fetchMe/token 管理） |
| `js/http-intercept.js` | 新建 | HTTP 拦截器（自动附加 token，401 处理） |
| `js/teacher-dashboard.js` | 新建 | 教师仪表盘逻辑 |
| `js/teacher-class.js` | 新建 | 班级管理逻辑 |
| `js/teacher-manage.js` | 新建 | 题库管理逻辑 |
| `js/teacher-exam.js` | 新建 | 考试管理逻辑 |
| `js/teacher-content.js` | 新建 | 内容管理逻辑 |
| `js/data-dashboard.js` | 新建 | 数据大屏逻辑 |
| `css/auth.css` | 新建 | 登录页样式 |
| `css/teacher.css` | 新建 | 教师端共享样式 |
| `css/data-dashboard.css` | 新建 | 数据大屏样式 |

### 后端文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/api/auth.py` | 新建 | 认证 API 路由 |
| `app/api/teacher.py` | 新建 | 教师端 API 路由 |
| `app/api/datacenter.py` | 新建 | 数据大屏 API 路由 |
| `app/utils/jwt.py` | 新建 | JWT 生成与验证工具 |
| `app/middleware/auth.py` | 新建 | 认证中间件（FastAPI Depends） |
| `app/middleware/roles.py` | 新建 | 角色守卫装饰器 |
| `app/models/teacher.py` | 新建 | 教师端数据模型 |
| `db.py` | 修改 | 新增教师端数据库操作函数 |

---

## 技术约束与兼容性

### 前端
- 所有新建页面遵循现有 HTML 页面结构模式（`html/*.html`）
- 使用 ECharts 作为统一图表库（知域也在用，无框架依赖）
- CSS 变量遵循星识现有主题系统的 `tokens.css`
- 看板娘使用 Live2D Cubism SDK（CDN 加载，~200KB），复用现有 `kanban.js` 基础设施
- 全局搜索使用 Fuse.js（~15KB gzipped）
- 语音录制使用浏览器原生 MediaRecorder API（需用户手势授权）
- 认证令牌存储在 localStorage，key 名 `sp_token`（与知域一致）

### 后端
- 所有新增 API 遵循现有 FastAPI 路由风格
- 数据库操作复用 `db.py` 中 pymysql 模式
- 流式响应使用 SSE（复用 `llm_stream.py` 已有实现）
- STT/TTS 复用星识已有服务端点
- JWT 实现使用 PyJWT 库，荷载结构与知域一致：`{uid, username, role}`
- 密码哈希使用 SHA-256（与知域兼容），后续可升级 bcrypt

### 页面兼容性
- 被合并的原独立页面文件保留不动
- 旧页面添加 JS 重定向脚本：直接访问时自动跳转到新聚合页面
- 旧路由在 `hub.html` 侧边栏中替换为新入口

---

## 错误处理与降级策略

### 看板娘（Phase 3）

| 故障场景 | 降级行为 |
|----------|----------|
| Live2D CDN 加载失败 | 降级为静态 PNG 立绘 + CSS 动画（`static/kanban.png`） |
| STT 服务不可用 | 隐藏语音按钮，仅支持文字输入 |
| TTS 服务不可用 | 仅显示文字回复，不播放语音（看板娘表情仍正常切换） |
| LLM 服务超时 | 看板娘显示"抱歉，我正在努力思考..."，30s 超时 |
| 麦克风权限被拒 | 隐藏语音按钮，仅支持文字输入 |
| SSE 连接断开 | 自动重连（指数退避，最多 5 次），重连期间显示"重新连接中..." |

### 教师端（Phase 5）

| 故障场景 | 降级行为 |
|----------|----------|
| Token 过期/无效 | 前端拦截器检测 401 → 清除 token → 跳转登录页 |
| AI 预批改失败 | 题目标记为"待手动批改"，不阻塞批改进程 |
| 代码执行超时 | 返回超时提示，编程题标记为需教师手动评审 |
| 数据大屏 SSE 断开 | 静默重连，图表数据保留最后快照 |

---

## Phase 执行顺序

```
Phase 3: 2D 看板娘 (1-2 周)
    ↓
Phase 4: 导航重构 (1 周)
    ↓ （看板娘完成后，导航入口可以使用看板娘能力）
Phase 5: 知域迁移 (2-3 周)
    ├── 认证系统 + 登录页 (0.5 周)
    ├── 教师端 (1.5 周)
    └── 数据大屏 (1 周)
```

**理由**：
1. 看板娘先做——它是 AI 交互的前端化身，导航重构依赖它
2. 导航重构基于看板娘的 AI 导航能力统一入口
3. 知域迁移最后——页面和 API 数量最多，但与其他两个 Phase 耦合度最低
4. 认证系统作为 Phase 5 第一个子任务——教师端所有页面都依赖认证

---

## 附录：参考项目分析

### 参考项目 A："小慧" (ai-assistant-teaching-website)

- **技术栈**：Vue3 + Unity WebGL + Django 后端
- **核心组件**：`UnityComponent.vue`（3D角色渲染）、`UnityInteraction.vue`（交互控制）
- **通信机制**：`UnityIns.SendMessage` → `window.handleUnityTransmission`
- **AI 管线**：百度 STT → 百度 ERNIE 3.5 LLM → 百度 TTS
- **导航能力**：LLM 返回 `<网站指令>` 标签 → 前端解析 → Vue Router 跳转
- **可选功能**：摄像头情绪识别（百度人脸分析 API）

### 参考项目 B：知域 (softwacecup)

- **技术栈**：Vue3 + Element Plus + Spring Boot + MySQL + Redis + Neo4j
- **教师端**：仪表盘、班级管理、题库管理、考试管理、内容管理、AI 内容审核
- **数据大屏**：多级数据展示（学校→学院→班级→个人）、ECharts 图表、实时动态
- **AI 助手**：悬浮球式（AIFloatingBall）+ 对话栏式（AIDialogBar）
- **认证系统**：JWT + localStorage + Pinia store + 路由守卫，三角色（student/teacher/admin）

### 星识项目现有资产

- **看板娘系统**：`js/kanban.js` + `css/components.css`，Live2D CDN 模型（Senko/Shizuku），3D 视差后备
- **代码工坊**：`html/code.html` + `js/code.js`，LLM 驱动的代码评估（`/api/grade-code`），subprocess 代码执行（`/api/run-code`）
- **AI 问答**：多智能体管线（Profiler → Planner → RAG → MasterController → Socratic/Multi-modal），SSE 流式响应
