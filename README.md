# 星识 Star-Learn

> **个人智能学习中枢** — 基于多智能体架构的智能教学辅助系统

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-Private-lightgrey)](#)

---

## 项目简介

**星识 (Star-Learn)** 是一个面向学生的 **AI 智能学习中枢**，融合多智能体编排、苏格拉底式教学、个性化学习路径规划、AI 课堂对话、代码练习、心流监测、知识图谱等能力，致力于让每个学习者拥有自己的"私人导师"。

### 核心能力

- 🧠 **多智能体编排**：MasterController 调度 Profiler、Planner、Document/Mindmap/Exercise/Video Generator、Resource Push、Evaluation、Socratic 等 10+ Agent
- 💬 **AI 课堂对话**：5 种教师 Persona（patient_tutor、socratic_questioner、energetic_lecturer、expert_mentor、caring_counselor），按 `socratic_intensity` 注入不同反问强度
- 🎯 **学习路径规划**：每日学习路线、SM2 间隔重复、知识节点图谱
- 💻 **代码工坊**：Monaco IDE、实时运行、AI 评审、批量出题、错题本
- 📚 **课程中心**：学科 → 课程 → 章节 → 子章节 四级结构，B站视频导入
- 🌱 **生态养成**：星宝宠物、植物林场、成就系统
- 🎙 **多媒体**：TTS（MiniMax）、ASR（百度/Whisper）、视频生成（可灵/CogVideo）
- 📊 **心流共振仪**：专注度监测 + 遥测数据可视化
- 🎨 **主题系统**：6 套主题 + 液态玻璃 + 3D 加载动画

---

## 快速开始

### 5 分钟跑起来

```bash
# 1. 克隆
git clone <repo-url>
cd Kuromi-main

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp config/.env.example config/.env
# 编辑 config/.env，至少填入 MINIMAX_API_KEY 和 MINIMAX_GROUP_ID

# 4. 初始化数据库（默认 SQLite，无需额外依赖）
python Navicat/setup_database.py

### 预置 Demo 内容

首次启动后，应用会自动从 `storage/seed/demo/` 加载演示内容，无需任何手动操作：

- **多个演示课程**（目前 5 门：Python / Web 前端 / 数据结构与算法 / AI 导论 / 线性代数），每门含完整富文本讲义 + 思维导图
- **多个演示课堂**（对应每门课程的 PPT），所有用户（含未登录）都能直接打开

所有用户可见 🎁 DEMO 课程，课堂页显示"演示课堂"横幅。

### 修改 / 升级 Demo 内容

1. 编辑 `storage/seed/demo/*.json`
2. 在 `manifest.json` 里 bump `demo_version`（如 `2.0.0` → `2.0.1`）
3. 下次启动自动替换 demo 内容；用户私有数据完全不受影响

```bash
# 手动重置（不依赖启动）
python scripts/seed_demo.py --reset
# 查看当前状态
python scripts/seed_demo.py --check
```

详见 [storage/seed/demo/README.md](storage/seed/demo/README.md)。

# 5. 启动服务
python main.py
# 或：python scripts/start_server.py
```

打开浏览器访问：**http://127.0.0.1:8000**

API 文档：**http://127.0.0.1:8000/docs**

---

## 详细文档

| 文档 | 说明 |
|------|------|
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | **生产环境部署**（Nginx / Systemd / Docker） |
| [docs/RUNNING_GUIDE.md](docs/RUNNING_GUIDE.md) | 上手指南与功能介绍 |
| [docs/PROJECT_MAP.md](docs/PROJECT_MAP.md) | 功能 → 代码完整地图 |
| [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) | 项目结构说明 |
| [docs/CODE_WIKI.md](docs/CODE_WIKI.md) | 代码百科 |
| [docs/SLICE_STATUS.md](docs/SLICE_STATUS.md) | 各模块进度状态 |
| [docs/sql/README.md](docs/sql/README.md) | SQL 初始化脚本说明 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.104 + Uvicorn 0.24 |
| ORM | SQLAlchemy 2.0（async）+ Alembic 1.13 |
| 数据校验 | Pydantic 2.x + pydantic-settings |
| 数据库 | MySQL 5.7+ / SQLite 3（异步驱动 aiosqlite / asyncmy / aiomysql） |
| Agent 编排 | LangGraph 0.2 + langgraph-checkpoint-mysql |
| 缓存 / 队列 | Redis 7（可选） |
| 向量库 | Qdrant 1.9（可选） |
| LLM | MiniMax（默认）/ 讯飞大模型 |
| TTS | MiniMax TTS（speech-2.8-hd）/ OpenAI 兼容 |
| ASR | 百度短语音 / Whisper WASM |
| 视频生成 | 可灵 Kling / CogVideo（本地） |
| 前端 | 原生 HTML/CSS/JS（无构建），Monaco Editor（CDN） |
| 测试 | pytest（后端）+ Vitest / Playwright（前端） |

---

## 项目结构

```
Kuromi-main/
├── main.py                    # FastAPI 应用入口
├── db.py                      # 传统 pymysql 数据库操作（用户、进度等）
├── state.py                   # Pydantic 数据模型
├── agents.py                  # 多智能体实现（MasterController 等）
├── agent_utils.py             # 智能体工具函数
├── llm_stream.py              # LLM 流式调用封装
├── proactive_tutor.py         # 主动辅导模块
├── task_manager.py            # 异步任务管理
├── prompts/                   # 提示词模板整合（含 snippets + templates）
│
├── app/                       # API + ORM 模块
│   ├── api/                   # 路由：asr / classroom / grading / ppt / teacher_chat / tts
│   ├── core/                  # 配置、数据库连接、健康检查
│   ├── models/                # SQLAlchemy 模型（User/Course/ClassroomSession/...）
│   ├── schemas/               # Pydantic Schema
│   ├── services/              # 服务层（teacher / ppt / tts / asr）
│   └── prompts/               # API 层提示词
│
├── scripts/                   # 工具脚本
│   ├── start_server.py        # 简易启动脚本
│   └── ...
│
├── libs/                      # 工具库
│   ├── video/                 # CogVideo 视频生成
│   ├── kling_api.py           # 可灵视频
│   ├── media.py               # TTS/图片/视频
│   ├── course.py              # 课程生成
│   └── pptx.py                # PPT 导出
│
├── config/                    # 配置中心
│   ├── config.py              # Pydantic Settings
│   ├── .env                   # 实际环境变量（不提交）
│   └── .env.example           # 环境变量模板
│
├── alembic/                   # 数据库迁移脚本
├── alembic.ini
├── Navicat/                   # 数据库工具
│   └── setup_database.py      # 一键建表（MySQL/SQLite）
│
├── docs/sql/                  # SQL 初始化脚本（离线/容器场景）
│   ├── init_mysql.sql
│   ├── init_sqlite.sql
│   └── drop_all.sql
│
├── html/                      # 前端 HTML 页面（20+）
├── css/                       # 样式
├── js/                        # 前端逻辑
├── static/                    # 静态资源
│
├── storage/                   # 运行时数据
├── audio/                     # TTS 输出
├── spool/                     # Agent 行为日志（KB）
│
├── tests/                     # 测试
├── scripts/                   # 工具脚本
├── packaging/                 # 打包相关
│
├── requirements.txt           # Python 依赖
├── package.json               # 前端测试依赖
├── docker-compose.dev.yml     # 开发环境 Qdrant + Redis
├── DEPLOYMENT.md              # 部署文档 ⭐
├── README.md                  # 本文件
└── 代码同步操作手册.md         # 代码同步说明
```

---

## 数据库

项目支持两种数据库后端：

| 后端 | 适用场景 | 命令 |
|------|---------|------|
| SQLite（默认） | 开发 / 单机 / 演示 | `python Navicat/setup_database.py --backend=sqlite` |
| MySQL 5.7+ | 生产环境 | `python Navicat/setup_database.py --backend=mysql` |
| SQL 文件 | 离线 / K8s / Docker | `mysql < docs/sql/init_mysql.sql` |
| Alembic | ORM 模型变更 | `alembic upgrade head` |

数据库共 **35 张表**，覆盖用户认证、学习记录、知识图谱、AI 对话、课堂会话、闪卡、生态养成、媒体缓存等。

详见 [DEPLOYMENT.md 第 4 节](DEPLOYMENT.md#四数据库初始化详解) 与 [docs/sql/README.md](docs/sql/README.md)。

---

## 部署

### 开发环境

```bash
python main.py --reload
# 或
uvicorn main:app --reload --port 8000
```

### 生产环境（推荐）

```bash
# 1. 安装依赖到虚拟环境
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. 配置环境
cp config/.env.example config/.env && vim config/.env

# 3. 初始化数据库（MySQL）
export MYSQL_USER=starlearn
export MYSQL_PASSWORD=secret
python Navicat/setup_database.py --backend=mysql

# 4. 启动（Systemd）
sudo systemctl enable --now starlearn

# 5. Nginx 反向代理（详见 DEPLOYMENT.md §3.9）
```

完整步骤见 [DEPLOYMENT.md](DEPLOYMENT.md)。

### Docker

```bash
docker compose -f docker-compose.dev.yml up -d   # 仅启动 Qdrant + Redis
docker build -t starlearn . && docker run -d --name starlearn -p 8000:8000 starlearn
```

---

## 测试

### 后端

```bash
pytest tests/
# 单元测试
pytest tests/ -k "unit"
# 集成测试
pytest tests/ -k "integration"
```

### 前端

```bash
npm install
npm run test:unit        # Vitest
npm run test:e2e         # Playwright
npm run test:a11y        # 无障碍测试
npm run test:all         # 全部
```

---

## 配置项速查

完整列表见 [DEPLOYMENT.md 附录 A](DEPLOYMENT.md#十附录环境变量清单)。

**必填**：
- `XUNFEI_API_KEY`（讯飞） / `MINIMAX_API_KEY` + `MINIMAX_GROUP_ID`（MiniMax） 二选一

**生产环境必改**：
- `DATABASE_URL` → MySQL URL
- `APP_DEBUG=False`

**可选服务**（不开则相关功能降级）：
- `KLING_*`：可灵视频生成
- `BAIDU_ASR_*`：百度语音识别
- Qdrant / Redis（通过 Docker 启动）

---

## 常见问题

- **启动报错 ModuleNotFoundError** → `pip install -r requirements.txt`
- **数据库连接失败** → 检查 `.env` 的 `DATABASE_URL`；或切换 SQLite
- **LLM 401/超时** → 检查 API Key 与网络
- **SSE 流断开** → Nginx 必须设置 `proxy_buffering off`
- **静态资源 404** → 检查 Nginx `location` 路径

更多：[DEPLOYMENT.md §9 常见问题排查](DEPLOYMENT.md#九常见问题排查)

---

## 贡献者

- 项目维护：StarLearn Team
- 设计 / 实现：见 [CODE_WIKI.md](CODE_WIKI.md)

## 许可证

本项目为内部项目，未经授权禁止外传。

---

> 最后更新：2026-07-20