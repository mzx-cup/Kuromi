# 星识项目文件整理说明

## 📁 项目结构总览

```
星识/
├── # 核心应用
├── main.py                    # 应用入口，FastAPI 服务启动
├── db.py                      # 数据库操作模块
├── state.py                   # 数据结构定义（请求/响应模型）
├── agents.py                  # 多智能体实现（MasterController 等）
├── agent_utils.py             # 智能体工具函数
├── llm_stream.py              # 大模型流式调用（讯飞 API）
├── proactive_tutor.py         # 主动辅导模块（推送消息）
├── task_manager.py            # 异步任务管理
├── prompts/                   # 提示词模板整合（含 __init__.py + snippets/ + templates/）
│
├── # 工具库 (libs/) - 归类散落的工具模块
├── libs/                      # 工具库目录
│   ├── __init__.py
│   ├── video/                 # 视频生成
│   │   ├── __init__.py
│   │   ├── cogvideo_api.py    # CogVideo 服务（独立运行）
│   │   ├── cogvideo_text_to_video.py
│   │   ├── cogvideo_image_to_video.py
│   │   └── download.py        # CogVideo 下载工具
│   ├── kling_api.py           # 可灵视频 API
│   ├── media.py               # 媒体生成（图片/TTS/视频）
│   ├── course.py              # 课程生成器
│   └── pptx.py               # PPT 导出
│
│   # 根目录的 re-export 文件（向后兼容）
├── cogvideo_api.py            # → libs.video.cogvideo_api (re-export)
├── cogvideo_text_to_video.py  # → libs.video.cogvideo_text_to_video (re-export)
├── cogvideo_image_to_video.py # → libs.video.cogvideo_image_to_video (re-export)
├── download_cogvideo.py       # → libs.video.download (re-export)
├── kling_api.py               # → libs.kling_api (re-export)
├── media_generation.py        # → libs.media (re-export)
├── course_generator.py        # → libs.course (re-export)
├── pptx_export.py             # → libs.pptx (re-export)
├── verify_ppt_templates.py    # → libs.pptx (re-export)
│
├── # 配置与数据库
├── config/                    # 配置目录
│   ├── __init__.py
│   ├── config.py              # 配置加载
│   ├── .env                   # 环境变量（私有）
│   └── .env.example           # 环境变量模板
├── alembic.ini                # Alembic 数据库迁移配置
├── alembic/                    # 数据库迁移脚本
├── Navicat/
│   └── setup_database.py      # 数据库初始化脚本
│
├── # API 模块 (app/)
├── app/
│   ├── api/                   # API 路由
│   │   ├── asr.py             # 语音识别
│   │   ├── classroom.py      # 课堂管理
│   │   ├── grading.py         # 评分
│   │   ├── ppt.py             # PPT 操作
│   │   ├── teacher_chat.py    # 教师聊天
│   │   └── tts.py             # 语音合成
│   ├── core/
│   │   ├── config.py          # 核心配置
│   │   ├── database.py        # 数据库连接
│   │   └── sse.py             # SSE 支持
│   ├── models/                # 数据模型
│   │   ├── base.py
│   │   ├── classroom.py
│   │   ├── course.py
│   │   └── user.py
│   ├── prompts/               # 提示词
│   ├── schemas/               # Pydantic schema
│   ├── services/              # 服务层
│   │   ├── asr/               # 语音识别服务
│   │   ├── ppt/               # PPT 服务
│   │   ├── teacher/           # 教师服务
│   │   └── tts/               # 语音合成服务
│   └── utils/
│
├── # 前端资源
├── html/                      # HTML 页面
│   ├── index.html             # 首页
│   ├── login.html             # 登录
│   ├── register.html          # 注册
│   ├── hub.html               # 中枢主页
│   ├── courses.html           # 课程中心
│   ├── code.html              # 代码练习
│   ├── socratic-ai.html       # 苏格拉底教学
│   ├── assessment.html        # 学习评估
│   ├── progress.html          # 学习进度
│   ├── calendar.html          # 学习日历
│   ├── personal.html          # 个人中心
│   ├── settings.html          # 设置
│   ├── flow-meter.html        # 心流仪
│   ├── stellar-showcase.html  # 星云陈列室
│   ├── plant.html             # 林场
│   ├── classroom.html         # 课堂
│   └── ...
├── css/                       # 样式文件
├── js/                        # JavaScript
├── static/                    # 静态资源
├── node_modules/              # Node.js 依赖
├── package.json               # Node.js 配置
│
├── # 存储目录
├── storage/                   # 运行时数据存储
│   ├── courses/               # 生成的课程数据
│   ├── task_storage/          # 任务状态存储
│   └── state_storage/         # 学生状态存储
├── audio/                     # 音频文件（TTS 输出）
│
├── # 工具与测试
├── tests/                     # 测试目录
│   ├── test_socratic.py
│   └── test_flashcard_flow.py
├── cogvideo_env/              # CogVideo 虚拟环境（独立 Python 环境）
│
├── # 文档
├── RUNNING_GUIDE.md           # 运行指南（重要！）
├── CODE_WIKI.md               # 代码百科
├── CODE_WIKI.md               # 代码说明
├── task_plan.md               # 任务计划
├── 代码同步操作手册.md         # 代码同步说明
├── 视频生成本地模型部署步骤.md # 视频模型部署
├── 星识_答辩演讲稿.md          # 答辩演讲稿
│
├── # 文档与报告（Word 格式）
├── 星识_作品报告.docx
├── 星识_答辩演讲稿.docx
│
├── # 项目配置
├── .claude/                   # Claude Code 配置
├── .clauderc
├── .gitignore
├── .vscode/                   # VSCode 配置
├── .pytest_cache/
├── requirements.txt           # Python 依赖
└── README.md
```

---

## 📂 文件分类说明

### 1️⃣ 核心应用模块（根目录 .py 文件）

| 文件 | 用途 |
|------|------|
| `main.py` | FastAPI 应用入口，路由注册 |
| `db.py` | 数据库 CRUD 操作（用户、课程、学习记录等） |
| `state.py` | Pydantic 模型定义（请求/响应数据结构） |
| `agents.py` | 多智能体实现，包含 MasterController、ProfilerAgent 等 |
| `agent_utils.py` | 智能体工具函数（状态构建、日志格式化等） |
| `llm_stream.py` | 讯飞大模型流式调用封装 |
| `proactive_tutor.py` | 主动辅导（推送消息、学习干预） |
| `task_manager.py` | 异步任务调度（思维导图、视频等） |
| `prompts/` | 所有提示词模板整合（含 __init__.py 注册表 + snippets/ + templates/） |

### 2️⃣ 工具库 (libs/) - 实际代码

| 文件/目录 | 用途 |
|-----------|------|
| `libs/media.py` | 媒体生成（TTS、图片、视频） |
| `libs/course.py` | 课程生成主逻辑 |
| `libs/pptx.py` | PPT 导出 |
| `libs/kling_api.py` | 可灵视频生成 API |
| `libs/video/cogvideo_api.py` | CogVideo 服务（独立运行） |
| `libs/video/cogvideo_text_to_video.py` | CogVideo 文生视频 |
| `libs/video/cogvideo_image_to_video.py` | CogVideo 图生视频 |
| `libs/video/download.py` | CogVideo 下载工具 |

### 3️⃣ 根目录 re-export 文件（向后兼容）

这些文件只有一行 re-export，实际代码在 libs/ 中：

| 文件 | 实际位置 |
|------|---------|
| `cogvideo_api.py` | → `libs/video/cogvideo_api.py` |
| `cogvideo_text_to_video.py` | → `libs/video/cogvideo_text_to_video.py` |
| `cogvideo_image_to_video.py` | → `libs/video/cogvideo_image_to_video.py` |
| `download_cogvideo.py` | → `libs/video/download.py` |
| `kling_api.py` | → `libs/kling_api.py` |
| `media_generation.py` | → `libs/media.py` |
| `course_generator.py` | → `libs/course.py` |
| `pptx_export.py` | → `libs/pptx.py` |
| `verify_ppt_templates.py` | → `libs/pptx.py` |
| `pptx_export.py` | PPT 导出功能 |
| `media_generation.py` | 媒体生成（TTS、图片） |

### 2️⃣ 外部 API 集成

| 文件 | 用途 |
|------|------|
| `kling_api.py` | 可灵视频生成 API |
| `cogvideo_api.py` | CogVideo 主 API |
| `cogvideo_text_to_video.py` | CogVideo 文生视频 |
| `cogvideo_image_to_video.py` | CogVideo 图生视频 |
| `download_cogvideo.py` | CogVideo 视频下载工具 |

### 3️⃣ 配置与数据库

| 文件/目录 | 用途 |
|-----------|------|
| `config/` | 所有配置 |
| `config/config.py` | 配置加载逻辑 |
| `config/.env` | 环境变量（API Key 等，私有） |
| `config/.env.example` | 环境变量模板 |
| `alembic.ini` | 数据库迁移配置 |
| `alembic/` | 迁移脚本目录 |
| `Navicat/setup_database.py` | 数据库初始化（MySQL/SQLite） |

### 4️⃣ API 模块（app/）

| 目录/文件 | 用途 |
|-----------|------|
| `app/api/` | RESTful API 路由 |
| `app/core/` | 核心配置（数据库、SSE） |
| `app/models/` | SQLAlchemy 模型 |
| `app/services/` | 业务逻辑服务层 |
| `app/prompts/` | API 层提示词 |
| `app/schemas/` | API 请求/响应 schema |
| `app/utils/` | 工具函数 |

### 5️⃣ 前端资源

| 目录/文件 | 用途 |
|-----------|------|
| `html/` | 所有 HTML 页面（20+ 个） |
| `css/` | 样式文件 |
| `js/` | JavaScript 文件 |
| `static/` | 静态资源（图片等） |
| `node_modules/` | npm 依赖 |
| `package.json` | npm 配置 |

### 6️⃣ 运行时存储

| 目录 | 用途 |
|------|------|
| `storage/courses/` | 生成的课程 JSON 数据 |
| `storage/task_storage/` | 异步任务状态 |
| `storage/state_storage/` | 学生会话状态 |
| `audio/` | TTS 生成的音频文件 |

### 7️⃣ 工具与测试

| 文件/目录 | 用途 |
|-----------|------|
| `tests/` | 单元测试 |
| `cogvideo_env/` | CogVideo 独立 Python 虚拟环境 |
| `verify_ppt_templates.py` | PPT 模板验证脚本 |

### 8️⃣ 文档

| 文件 | 用途 |
|------|------|
| `RUNNING_GUIDE.md` | **重要！** 给别人的运行指南 |
| `CODE_WIKI.md` | 项目代码说明文档 |
| `task_plan.md` | 任务计划 |
| `代码同步操作手册.md` | 代码同步说明 |
| `视频生成本地模型部署步骤.md` | 视频模型本地部署 |

---

## 🔧 配置说明

### 环境变量（config/.env）

```env
# 讯飞 API（必须）
XUNFEI_API_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/v2/chat/completions
XUNFEI_API_KEY=你的API密钥

# 模型
MODEL_NAME=astron-code-latest

# 调试
APP_DEBUG=False
```

### 数据库

- **MySQL**：运行 `python Navicat/setup_database.py --backend=mysql`
- **SQLite**：运行 `python Navicat/setup_database.py --backend=sqlite`（默认）

---

## 📋 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp config/.env.example config/.env
# 编辑 config/.env 填入讯飞 API Key

# 3. 初始化数据库
python Navicat/setup_database.py

# 4. 启动服务
python main.py
```

访问 http://127.0.0.1:8000

---

## 📊 数据流向

```
用户浏览器
    ↓ HTTP/HTTPS
FastAPI (main.py)
    ↓
├── app/api/        # 路由处理
├── agents.py       # 智能体逻辑
├── llm_stream.py   # 调用讯飞 API
└── db.py           # 数据持久化
    ↓
MySQL / SQLite
```

---

## 🗂️ 各模块详细说明

### 智能体架构（agents.py）

- `MasterController` - 主控智能体，协调所有子智能体
- `ProfilerAgent` - 学情分析
- `PlannerAgent` - 学习路径规划
- `SocraticEvaluatorAgent` - 苏格拉底式教学
- `DocumentGeneratorAgent` - 文档生成
- `MindmapGeneratorAgent` - 思维导图生成
- `FlashcardAgent` - 闪卡生成

### API 模块（app/api/）

- `asr.py` - 语音识别
- `classroom.py` - 课堂管理
- `grading.py` - 代码评分
- `ppt.py` - PPT 操作
- `teacher_chat.py` - 教师聊天
- `tts.py` - 语音合成

### 服务层（app/services/）

- `asr/` - 语音识别提供商（百度、Whisper）
- `tts/` - 语音合成提供商（MiniMax、OpenAI兼容）
- `teacher/` - 教师智能体逻辑
- `ppt/` - PPT 生成/重新生成