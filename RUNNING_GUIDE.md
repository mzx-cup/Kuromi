# 星识 (Star-Learn) 伴学系统 - 快速上手指南

## 项目简介

星识是一个基于多智能体架构的智能教学辅助系统，为学生提供个性化的学习体验。支持智能对话、苏格拉底式教学、代码练习、学习路径规划等功能。

---

## 环境要求

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | ≥ 3.8 | 后端运行环境 |
| Node.js | ≥ 16 | 前端资源构建（可选） |
| MySQL | ≥ 5.7 | 数据库（可选，也可使用 SQLite） |

---

## 安装步骤

### 1. 克隆项目

```bash
git clone <项目地址>
cd 星识
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

主要依赖包括：
- `fastapi` - Web 框架
- `uvicorn` - ASGI 服务器
- `pydantic` - 数据验证
- `sqlalchemy` - ORM
- `pymysql` - MySQL 驱动
- `python-pptx` - PPT 处理

### 3. 配置环境变量

复制配置文件模板：

```bash
cp config/.env.example config/.env
```

编辑 `config/.env`，填入你的配置：

```env
# 讯飞 API 配置（必须）
XUNFEI_API_URL=https://maas-coding-api.cn-huabei-1.xf-yun.com/v2/chat/completions
XUNFEI_API_KEY=你的API密钥

# 模型名称
MODEL_NAME=astron-code-latest

# 调试模式（开发时设为 True）
APP_DEBUG=False
```

> **获取讯飞 API Key**：前往 [讯飞开放平台](https://console.xfyun.cn/) 注册并创建应用。

### 4. 初始化数据库

**方式一：使用 MySQL（推荐用于生产环境）**

确保 MySQL 服务正在运行，然后执行：

```bash
python Navicat/setup_database.py --backend=mysql
```

默认连接配置：
- 主机：`127.0.0.1`
- 端口：`3306`
- 用户名：`root`
- 密码：`root`
- 数据库名：`xingshi`

如需修改，可通过环境变量配置：
```bash
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=root
export MYSQL_PASSWORD=你的密码
python Navicat/setup_database.py --backend=mysql
```

**方式二：使用 SQLite（适合开发调试）**

```bash
python Navicat/setup_database.py --backend=sqlite
```

SQLite 数据库文件将创建在项目根目录：`xingshi.db`

---

## 启动项目

### 方式一：一键启动（推荐）

```bash
python main.py
```

### 方式二：使用 uvicorn

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- `--reload`：开发模式，热重载
- `--host 0.0.0.0`：允许外部访问
- `--port 8000`：默认端口

### 访问地址

启动成功后，打开浏览器访问：

| 地址 | 说明 |
|------|------|
| http://127.0.0.1:8000 | 主页面 |
| http://127.0.0.1:8000/docs | API 文档（Swagger） |

---

## 项目结构

```
星识/
├── main.py              # 应用入口
├── requirements.txt     # Python 依赖
├── alembic.ini          # 数据库迁移配置
├── db.py                # 数据库操作模块
├── agents.py            # 智能体实现
├── state.py             # 数据结构定义
├── llm_stream.py        # 大模型调用
├── proactive_tutor.py   # 主动辅导模块
├── task_manager.py      # 任务管理
├── config/              # 配置文件目录
│   ├── .env             # 环境变量（需创建）
│   └── .env.example     # 环境变量模板
├── Navicat/             # 数据库工具
│   └── setup_database.py
├── alembic/             # 数据库迁移脚本
├── app/                 # API 模块
│   ├── api/             # API 路由
│   ├── core/            # 核心配置
│   ├── models/          # 数据模型
│   ├── services/        # 服务层（ASR/TTS/教师）
│   └── prompts/         # 提示词模板
└── html/                # 前端页面
    ├── index.html       # 首页
    ├── login.html       # 登录
    ├── register.html    # 注册
    ├── hub.html         # 中枢主页
    ├── courses.html     # 课程中心
    ├── code.html        # 代码练习
    ├── socratic-ai.html # 苏格拉底教学
    └── ...              # 其他页面
```

---

## 主要功能入口

| 页面 | 文件 | 功能 |
|------|------|------|
| 登录 | `html/login.html` | 用户登录 |
| 注册 | `html/register.html` | 用户注册 |
| 中枢主页 | `html/hub.html` | 系统主界面 |
| 课程中心 | `html/courses.html` | 课程管理 |
| 代码练习 | `html/code.html` | 编程练习 |
| 苏格拉底 | `html/socratic-ai.html` | 苏格拉底式教学 |
| 学习进度 | `html/progress.html` | 进度跟踪 |
| 个人中心 | `html/personal.html` | 用户设置 |

---

## 数据库配置说明

### 使用现有 MySQL 数据库

如果已有 MySQL 数据库，修改 `config/.env`：

```env
DATABASE_URL=mysql+pymysql://用户名:密码@主机:端口/数据库名
```

### 使用 SQLite

默认配置即使用 SQLite，无需额外配置。数据库文件为 `xingshi.db`。

### 查看数据库

```bash
# 使用 sqlite3（SQLite）
sqlite3 xingshi.db ".tables"

# 使用 MySQL（需要 MySQL 客户端）
mysql -u root -p -e "USE xingshi; SHOW TABLES;"
```

---

## 常见问题

### 1. 启动报错 "Module not found"

```bash
pip install -r requirements.txt
```

### 2. 数据库连接失败

- 检查 MySQL 服务是否运行
- 确认用户名、密码、端口配置正确
- 或切换到 SQLite：`python Navicat/setup_database.py --backend=sqlite`

### 3. 讯飞 API 调用失败

- 检查 `XUNFEI_API_KEY` 是否正确
- 检查网络能否访问讯飞 API
- 确认 API 额度充足

### 4. CORS 跨域问题

项目已配置允许所有来源的 CORS，如需限制，修改 `main.py` 中的：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 改为你的前端地址
    ...
)
```

---

## 开发指南

### 运行开发服务器

```bash
uvicorn main:app --reload --port 8000
```

修改代码后会自动重载。

### 运行测试

```bash
pytest tests/
```

### 数据库迁移（使用 Alembic）

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

---

## API 文档

启动服务后访问 http://127.0.0.1:8000/docs 查看完整的 API 文档（Swagger UI）。

常用 API 端点：
- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `POST /api/v2/chat` - 智能对话
- `POST /api/v2/chat/stream` - 流式对话
- `POST /api/run-code` - 运行代码
- `POST /api/v2/flashcard/generate` - 生成闪卡

---

## 技术支持

如遇到问题，请检查：
1. Python 版本（需要 ≥ 3.8）
2. 依赖是否完整安装
3. 配置文件是否正确
4. 数据库服务是否正常运行