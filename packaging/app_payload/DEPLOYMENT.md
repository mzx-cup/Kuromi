# 星识 (Star-Learn) 部署文档

> 本文档面向运维/部署工程师，涵盖 **生产环境部署**、**开发环境搭建**、**数据库初始化**、**常见问题排查** 等完整流程。

---

## 目录

- [一、项目简介](#一项目简介)
- [二、环境要求](#二环境要求)
- [三、生产环境部署](#三生产环境部署)
  - [3.1 部署架构](#31-部署架构)
  - [3.2 服务器准备](#32-服务器准备)
  - [3.3 代码获取](#33-代码获取)
  - [3.4 依赖安装](#34-依赖安装)
  - [3.5 数据库部署](#35-数据库部署)
  - [3.6 知识中台组件（Qdrant + Redis）](#36-知识中台组件qdrant--redis)
  - [3.7 环境变量配置](#37-环境变量配置)
  - [3.8 应用启动](#38-应用启动)
  - [3.9 反向代理（Nginx）](#39-反向代理nginx)
  - [3.10 Systemd 服务](#310-systemd-服务)
  - [3.11 HTTPS 证书（Let's Encrypt）](#311-https-证书lets-encrypt)
- [四、数据库初始化详解](#四数据库初始化详解)
  - [4.1 MySQL 模式](#41-mysql-模式)
  - [4.2 SQLite 模式](#42-sqlite-模式)
  - [4.3 SQL 初始化脚本（离线/容器场景）](#43-sql-初始化脚本离线容器场景)
  - [4.4 Alembic 迁移](#44-alembic-迁移)
- [五、Docker / Docker Compose 部署](#五docker--docker-compose-部署)
- [六、升级与回滚](#六升级与回滚)
- [七、监控与日志](#七监控与日志)
- [八、备份策略](#八备份策略)
- [九、常见问题排查](#九常见问题排查)
- [十、附录：环境变量清单](#十附录环境变量清单)

---

## 一、项目简介

**星识 (Star-Learn)** 是一个基于多智能体架构的智能教学辅助系统，提供智能对话、苏格拉底式教学、代码练习、学习路径规划、AI 课堂、课程中心、心流监测等功能。

**技术栈**：

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.104 + Uvicorn |
| 前端 | 原生 HTML/CSS/JavaScript（无需构建），可选 Monaco Editor |
| 数据库 | MySQL 5.7+ / SQLite 3（默认 SQLite） |
| ORM | SQLAlchemy 2.0（异步） + Alembic |
| 向量库 | Qdrant 1.9（知识检索，可选） |
| 缓存 | Redis 7（可灵/Qdrant 缓存，可选） |
| LLM | MiniMax / 讯飞（Xunfei） |
| 媒体 | 可灵 Kling、CogVideo（视频），MiniMax TTS（语音合成），百度 ASR（语音识别） |

---

## 二、环境要求

### 2.1 最低配置

| 资源 | 开发环境 | 生产环境（单节点） | 生产环境（集群） |
|------|---------|--------------------|------------------|
| CPU | 2 核 | 4 核 | 8 核+ |
| 内存 | 4 GB | 8 GB | 16 GB+ |
| 磁盘 | 10 GB | 50 GB（含媒体） | 200 GB+ SSD |
| 带宽 | 5 Mbps | 20 Mbps | 100 Mbps+ |

### 2.2 软件依赖

| 软件 | 版本 | 说明 |
|------|------|------|
| Python | ≥ 3.9（推荐 3.10 / 3.11） | 后端运行时 |
| pip | ≥ 23 | 包管理 |
| MySQL | ≥ 5.7（推荐 8.0） | 主数据库（生产） |
| SQLite | 3.x（Python 内置） | 主数据库（开发/单机） |
| Qdrant | 1.9.x（Docker） | 向量数据库（可选） |
| Redis | 7.x（Docker） | 缓存（可选） |
| Node.js | ≥ 18（可选） | 仅用于 Playwright/Vitest 前端测试 |
| Nginx | ≥ 1.18（推荐） | 反向代理 |
| Systemd | Linux 发行版默认 | 进程托管 |
| FFmpeg | 最新版（可选） | 视频处理/转码 |

> ⚠️ **注意**：CogVideo 与 Whisper 等本地模型对硬件要求较高，建议独立 GPU 节点运行（不在本文档范围）。

### 2.3 操作系统

- **Linux**：Ubuntu 22.04 LTS / Debian 11 / CentOS 8+ / Rocky Linux 9+（生产推荐）
- **macOS**：13+（开发推荐）
- **Windows**：10/11 + WSL2（开发推荐）

---

## 三、生产环境部署

### 3.1 部署架构

```
                ┌─────────────────────────────────────┐
                │            Nginx (80/443)          │
                │  - 反向代理 / TLS 终止 / 静态资源  │
                └──────────────┬──────────────────────┘
                               │
                ┌──────────────▼──────────────────────┐
                │   Star-Learn App (Uvicorn 8000)    │
                │   - FastAPI + 多 Agent 编排        │
                │   - SSE 流式对话 / 异步任务        │
                └────┬─────────────────────┬─────────┘
                     │                     │
        ┌────────────▼──────┐   ┌──────────▼──────────┐
        │  MySQL 8.0        │   │  Qdrant 1.9 + Redis 7│
        │  (主数据库)        │   │  (向量/缓存/调度)    │
        └───────────────────┘   └─────────────────────┘
```

### 3.2 服务器准备

#### Ubuntu / Debian

```bash
# 1) 系统更新
sudo apt update && sudo apt upgrade -y

# 2) 安装系统依赖
sudo apt install -y python3 python3-pip python3-venv \
                    build-essential libssl-dev libffi-dev \
                    nginx git curl wget ffmpeg \
                    default-libmysqlclient-dev pkg-config

# 3) 创建应用用户（不使用 root 运行）
sudo useradd -r -m -s /bin/bash starlearn
sudo mkdir -p /opt/starlearn
sudo chown starlearn:starlearn /opt/starlearn
```

#### CentOS / Rocky

```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-devel \
                    gcc gcc-c++ make openssl-devel \
                    nginx git curl wget ffmpeg \
                    mysql-devel pkgconfig
sudo useradd -r -m -s /bin/bash starlearn
sudo mkdir -p /opt/starlearn && sudo chown starlearn:starlearn /opt/starlearn
```

### 3.3 代码获取

```bash
# 切换到应用用户
sudo -iu starlearn

# 方式一：从 Git 拉取（推荐）
cd /opt/starlearn
git clone <your-repo-url> app
cd app

# 方式二：上传代码包（scp / rsync）
# rsync -avz --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
#     ./local-path/ starlearn@server:/opt/starlearn/app/
```

### 3.4 依赖安装

```bash
# 创建虚拟环境（强烈推荐）
cd /opt/starlearn/app
python3 -m venv .venv
source .venv/bin/activate

# 升级 pip
pip install --upgrade pip wheel setuptools

# 安装 Python 依赖
pip install -r requirements.txt

# 验证安装
python -c "import fastapi, sqlalchemy, alembic; print('OK')"
```

### 3.5 数据库部署

#### MySQL 部署（生产推荐）

```bash
# Ubuntu/Debian
sudo apt install -y mysql-server
sudo systemctl enable --now mysql

# 初始化安全
sudo mysql_secure_installation
```

创建数据库与用户：

```sql
-- 登录 MySQL
mysql -u root -p

-- 创建数据库（utf8mb4 完整字符集）
CREATE DATABASE IF NOT EXISTS xingshi
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- 创建专用用户
CREATE USER 'starlearn'@'localhost' IDENTIFIED BY 'YourStrongPassword!';
GRANT ALL PRIVILEGES ON xingshi.* TO 'starlearn'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### 配置 MySQL 远程访问（可选）

```bash
sudo sed -i 's/^bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf
sudo systemctl restart mysql
```

> ⚠️ 生产环境请开启防火墙，仅放行可信 IP 访问 3306。

### 3.6 知识中台组件（Qdrant + Redis）

> 这些组件是 **可选的**。如果只用基础对话与教学功能，可以跳过这一步。

```bash
# 使用 docker-compose.dev.yml（开发版）
docker compose -f docker-compose.dev.yml up -d

# 或生产环境建议使用各自的 systemd / K8s 部署
docker run -d --name qdrant -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant:v1.9.0
docker run -d --name redis -p 6379:6379 redis:7.2-alpine
```

### 3.7 环境变量配置

复制示例文件并填写生产配置：

```bash
cp config/.env.example config/.env
chmod 600 config/.env   # 仅所有者可读写
```

编辑 `config/.env`，**关键变量**：

```ini
# ─── LLM API 凭证（必需）───
XUNFEI_API_KEY=your_xunfei_api_key
MINIMAX_API_KEY=your_minimax_api_key
MINIMAX_GROUP_ID=your_group_id

# ─── 数据库 ───
# MySQL 示例
DATABASE_URL=mysql+aiomysql://starlearn:YourStrongPassword!@127.0.0.1:3306/xingshi
# 同步版本（Alembic 用）
DATABASE_URL_SYNC=mysql+pymysql://starlearn:YourStrongPassword!@127.0.0.1:3306/xingshi
# LangGraph 检查点存储
CHECKPOINT_DB_URL=mysql+pymysql://starlearn:YourStrongPassword!@127.0.0.1:3306/xingshi

# ─── 知识中台 ───
KB_QDRANT_MASTER_HOST=127.0.0.1
KB_QDRANT_PORT=6333
KB_REDIS_HOST=127.0.0.1
KB_REDIS_PORT=6379

# ─── 应用 ───
APP_DEBUG=False
KUROMI_DEBUG=False
```

完整变量清单见本文档 [附录 A](#十附录环境变量清单)。

### 3.8 应用启动

#### 方式一：直接启动（验证用）

```bash
cd /opt/starlearn/app
source .venv/bin/activate
python start_server.py    # 监听 127.0.0.1:8000
```

#### 方式二：Uvicorn 启动（推荐开发）

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers
```

#### 方式三：Systemd 托管（生产推荐）

见 [3.10 Systemd 服务](#310-systemd-服务)。

#### 数据库初始化（首次启动前必做）

```bash
cd /opt/starlearn/app

# MySQL 模式
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=starlearn
export MYSQL_PASSWORD='YourStrongPassword!'
python Navicat/setup_database.py --backend=mysql

# 或 SQLite 模式（默认）
python Navicat/setup_database.py --backend=sqlite
```

应用启动时会自动调用 `app.core.database.init_db()` 创建 ORM 表（双重保险）。

### 3.9 反向代理（Nginx）

创建 `/etc/nginx/sites-available/starlearn`：

```nginx
upstream starlearn_app {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name your.domain.com;

    client_max_body_size 200M;     # 支持大文件上传（音频/视频）

    # 静态资源（前端）
    location /static/ {
        alias /opt/starlearn/app/static/;
        expires 30d;
        access_log off;
    }
    location /html/ {
        alias /opt/starlearn/app/html/;
        expires 1h;
    }
    location /css/ {
        alias /opt/starlearn/app/css/;
        expires 30d;
        access_log off;
    }
    location /js/ {
        alias /opt/starlearn/app/js/;
        expires 30d;
        access_log off;
    }
    location /storage/ {
        alias /opt/starlearn/app/storage/;
        internal;  # 不允许直接访问，应用层鉴权
    }
    location /audio/ {
        alias /opt/starlearn/app/audio/;
        internal;
    }

    # SSE / API
    location /api/ {
        proxy_pass http://starlearn_app;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 关键：禁用缓冲、长连接
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # 首页 / 根路径
    location / {
        proxy_pass http://starlearn_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/starlearn /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3.10 Systemd 服务

创建 `/etc/systemd/system/starlearn.service`：

```ini
[Unit]
Description=Star-Learn (StarLearn) FastAPI Service
After=network.target mysql.service docker.service
Wants=mysql.service

[Service]
Type=simple
User=starlearn
Group=starlearn
WorkingDirectory=/opt/starlearn/app
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONUTF8=1"
EnvironmentFile=/opt/starlearn/app/config/.env
ExecStart=/opt/starlearn/app/.venv/bin/uvicorn main:app \
    --host 127.0.0.1 --port 8000 \
    --workers 4 \
    --proxy-headers \
    --log-level info
Restart=always
RestartSec=5
LimitNOFILE=65535

# 安全加固
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/starlearn/app/storage /opt/starlearn/app/audio /opt/starlearn/app/spool

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now starlearn
sudo systemctl status starlearn
sudo journalctl -u starlearn -f    # 跟踪日志
```

### 3.11 HTTPS 证书（Let's Encrypt）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com
# 自动续期已由 certbot.timer 配置
sudo systemctl status certbot.timer
```

---

## 四、数据库初始化详解

项目支持 **3 种数据库初始化方式**，任选其一即可：

| 方式 | 命令 | 适用场景 |
|------|------|---------|
| 一键脚本 | `python Navicat/setup_database.py --backend=mysql` | 99% 场景（推荐） |
| SQL 文件 | `mysql < docs/sql/init_mysql.sql` | 离线/容器初始化 |
| Alembic 迁移 | `alembic upgrade head` | 增量迁移 |

### 4.1 MySQL 模式

```bash
# 配置连接（也可放进环境变量）
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306
export MYSQL_USER=starlearn
export MYSQL_PASSWORD='YourStrongPassword!'

# 运行初始化（自动创建数据库 xingshi + 34 张表）
python Navicat/setup_database.py --backend=mysql
```

脚本会执行：

1. 创建数据库 `xingshi`（utf8mb4 字符集）
2. 为旧版 `user` 表补加新字段（向后兼容）
3. 修复旧表外键约束（确保 `ON DELETE CASCADE`）
4. 逐表执行 `CREATE TABLE IF NOT EXISTS`，**幂等**

成功输出示例：

```
============================================================
  星识 (Star-Learn) 数据库初始化 - MySQL 模式
============================================================
  主机: 127.0.0.1:3306
  用户: starlearn
  数据库: xingshi
------------------------------------------------------------
  [OK] 数据库 'xingshi' 就绪
  [OK] user                            就绪
  [OK] learning_records                就绪
  ...
  [OK] agent_turn_records              就绪
------------------------------------------------------------
  完成! 34/34 张表创建成功
```

### 4.2 SQLite 模式

无需任何额外依赖，Python 内置支持：

```bash
python Navicat/setup_database.py --backend=sqlite
```

默认数据库文件：`Navicat/xingshi.db`（脚本会自动开启 WAL 模式提高并发）。

如果应用使用 `app/core/config.py` 默认的 `xingshi_v2.db`，可手动复制或重命名：

```bash
cp Navicat/xingshi.db ./xingshi_v2.db
```

### 4.3 SQL 初始化脚本（离线/容器场景）

> 适合 **K8s InitContainer**、**Dockerfile 初始化**、**离线部署** 等场景。

#### MySQL 初始化

```bash
# 先创建数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS xingshi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 执行 SQL 脚本
mysql -u starlearn -p xingshi < docs/sql/init_mysql.sql
```

#### SQLite 初始化

```bash
sqlite3 xingshi_v2.db < docs/sql/init_sqlite.sql
```

详见 [docs/sql/README.md](sql/README.md)。

### 4.4 Alembic 迁移

项目使用 Alembic 管理 SQLAlchemy ORM 模型的版本变更。

```bash
# 1) 设置数据库 URL
export DATABASE_URL_SYNC=mysql+pymysql://starlearn:password@127.0.0.1:3306/xingshi
# 或修改 alembic.ini 中的 sqlalchemy.url

# 2) 查看当前版本
alembic current

# 3) 升级到最新版本
alembic upgrade head

# 4) 创建新迁移（开发时）
alembic revision --autogenerate -m "add_new_table"

# 5) 回滚一个版本
alembic downgrade -1
```

迁移文件位于 `alembic/versions/`：

- `b01b4224a404_initial_*.py` — 初始迁移（users/courses/classroom 等）
- `20260529_add_subjects_chapters_subchapters.py` — 课程中心表结构

---

## 五、Docker / Docker Compose 部署

### 5.1 单容器（应用 + SQLite）

`Dockerfile`（参考）：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential default-libmysqlclient-dev pkg-config \
        ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 数据卷
VOLUME ["/app/storage", "/app/audio", "/app/spool"]

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# 初始化数据库后启动
CMD ["sh", "-c", "python Navicat/setup_database.py --backend=sqlite && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers"]
```

构建并运行：

```bash
docker build -t starlearn:1.0.0 .
docker run -d --name starlearn \
    -p 8000:8000 \
    -v $(pwd)/storage:/app/storage \
    -v $(pwd)/audio:/app/audio \
    --env-file config/.env \
    --restart unless-stopped \
    starlearn:1.0.0
```

### 5.2 Compose 全栈（含 MySQL + Qdrant + Redis）

`docker-compose.yml`（生产级示例）：

```yaml
version: "3.9"

services:
  mysql:
    image: mysql:8.0
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: xingshi
      MYSQL_USER: starlearn
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "127.0.0.1:3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.9.0
    restart: always
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "127.0.0.1:6333:6333"

  redis:
    image: redis:7.2-alpine
    restart: always
    volumes:
      - redis_data:/data
    ports:
      - "127.0.0.1:6379:6379"

  app:
    build: .
    restart: always
    depends_on:
      mysql:
        condition: service_healthy
    environment:
      DATABASE_URL: mysql+aiomysql://starlearn:${MYSQL_PASSWORD}@mysql:3306/xingshi
      DATABASE_URL_SYNC: mysql+pymysql://starlearn:${MYSQL_PASSWORD}@mysql:3306/xingshi
      CHECKPOINT_DB_URL: mysql+pymysql://starlearn:${MYSQL_PASSWORD}@mysql:3306/xingshi
      KB_QDRANT_MASTER_HOST: qdrant
      KB_REDIS_HOST: redis
    env_file:
      - config/.env
    volumes:
      - ./storage:/app/storage
      - ./audio:/app/audio
    ports:
      - "127.0.0.1:8000:8000"

volumes:
  mysql_data:
  qdrant_data:
  redis_data:
```

启动：

```bash
docker compose up -d
docker compose logs -f app
```

---

## 六、升级与回滚

### 6.1 标准升级流程

```bash
# 1) 备份
sudo -iu starlearn
cd /opt/starlearn
./scripts/backup.sh    # 或手动 mysqldump

# 2) 拉取新代码
cd app
git pull origin main   # 或上传新代码

# 3) 更新依赖
source .venv/bin/activate
pip install -r requirements.txt

# 4) 执行数据库迁移
alembic upgrade head
# 若使用 MySQL 旧表，可能需手动跑 setup_database.py 兼容新字段

# 5) 重启服务
sudo systemctl restart starlearn

# 6) 验证
curl -fsS http://127.0.0.1:8000/api/health
sudo journalctl -u starlearn --since "1 minute ago" -p err
```

### 6.2 回滚

```bash
# 1) 代码回滚
cd /opt/starlearn/app
git checkout <previous-tag>

# 2) 数据库回滚
alembic downgrade -1    # 回退一个版本

# 3) 重启
sudo systemctl restart starlearn
```

### 6.3 蓝绿部署（零停机）

1. 部署 v2 到 `:8001`
2. Nginx 上游切到 v2
3. 监控 v2 正常后下线 v1
4. 失败则切回 v1

---

## 七、监控与日志

### 7.1 日志位置

| 日志 | 路径 |
|------|------|
| Systemd 应用日志 | `journalctl -u starlearn` |
| Uvicorn 启动日志 | `/opt/starlearn/app/uvicorn.log` |
| Nginx 访问日志 | `/var/log/nginx/access.log` |
| Nginx 错误日志 | `/var/log/nginx/error.log` |
| MySQL 慢日志 | `/var/log/mysql/mysql-slow.log` |
| Agent 行为日志（spool） | `/opt/starlearn/app/spool/agent_log/` |

### 7.2 健康检查端点

| 端点 | 说明 |
|------|------|
| `GET /api/health` | 基础存活检查 |
| `GET /docs` | Swagger UI（含全部 API 状态） |

### 7.3 关键监控指标

- **应用进程**：CPU / 内存 / 句柄数（`LimitNOFILE`）
- **MySQL**：连接数（`SHOW STATUS LIKE 'Threads_connected'`）、慢查询
- **Qdrant**：集合大小、检索延迟
- **Redis**：内存使用、命中率
- **磁盘**：storage / audio / spool 目录

### 7.4 推荐接入 Prometheus + Grafana

```bash
# 安装 node_exporter
sudo apt install -y prometheus-node-exporter
sudo systemctl enable --now prometheus-node-exporter

# 安装 mysqld_exporter
sudo apt install -y prometheus-mysqld-exporter
```

---

## 八、备份策略

### 8.1 数据库备份

#### MySQL（每日全量 + binlog）

`/opt/starlearn/scripts/backup.sh`：

```bash
#!/bin/bash
set -e
BACKUP_DIR=/opt/starlearn/backups/db
mkdir -p "$BACKUP_DIR"
TS=$(date +%Y%m%d_%H%M%S)
mysqldump -u starlearn -p"$MYSQL_PASSWORD" \
    --single-transaction --routines --triggers --events \
    xingshi | gzip > "$BACKUP_DIR/xingshi_${TS}.sql.gz"
# 仅保留 14 天
find "$BACKUP_DIR" -mtime +14 -name "*.sql.gz" -delete
```

```bash
chmod +x /opt/starlearn/scripts/backup.sh
# 加入 crontab
crontab -e
# 每天凌晨 3 点
0 3 * * * /opt/starlearn/scripts/backup.sh >> /var/log/starlearn-backup.log 2>&1
```

#### SQLite

```bash
sqlite3 xingshi_v2.db ".backup '/opt/starlearn/backups/sqlite/xingshi_$(date +%Y%m%d).db'"
```

### 8.2 应用数据备份

```bash
tar -czf /opt/starlearn/backups/storage_$(date +%Y%m%d).tar.gz \
    -C /opt/starlearn/app storage audio
```

### 8.3 恢复

```bash
# MySQL
gunzip < /opt/starlearn/backups/db/xingshi_20260720_030000.sql.gz | mysql -u starlearn -p xingshi

# SQLite
cp /opt/starlearn/backups/sqlite/xingshi_20260720.db /opt/starlearn/app/xingshi_v2.db
```

---

## 九、常见问题排查

### 9.1 启动报错 "Address already in use"

```bash
sudo lsof -i :8000
# 或
sudo fuser -k 8000/tcp
# 然后重启
sudo systemctl restart starlearn
```

### 9.2 数据库连接失败

```bash
# 检查 MySQL
sudo systemctl status mysql
mysql -u starlearn -p -h 127.0.0.1 -e "SELECT 1;"

# 检查环境变量
grep DATABASE_URL /opt/starlearn/app/config/.env

# 检查连接池是否耗尽
mysql -u root -p -e "SHOW STATUS LIKE 'Threads_connected';"
```

### 9.3 Alembic 迁移卡住 / 版本不一致

```bash
# 查看当前版本
alembic current

# 强制 stamp 到指定版本（紧急修复）
alembic stamp head

# 重建数据库（破坏性）
alembic downgrade base
alembic upgrade head
```

### 9.4 SSE 流断开 / 502 Bad Gateway

- 检查 Nginx `proxy_buffering off`
- 检查 `proxy_read_timeout` ≥ 3600s
- 检查 Uvicorn `--proxy-headers` 是否启用

### 9.5 静态资源 404

确认 Nginx `location` 路径与文件实际位置一致：

```bash
ls -la /opt/starlearn/app/html /opt/starlearn/app/css /opt/starlearn/app/js
```

### 9.6 端口被防火墙拦截

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow from <trusted-ip> to any port 3306

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 9.7 LLM API 调用超时 / 401

- 检查 `XUNFEI_API_KEY` / `MINIMAX_API_KEY` 是否有效
- 检查网络能否访问 `https://api.minimax.chat`
- 检查账户余额

---

## 十、附录：环境变量清单

### A. LLM / 媒体 API

| 变量 | 必填 | 说明 |
|------|------|------|
| `XUNFEI_API_URL` | 否 | 讯飞 API 地址 |
| `XUNFEI_API_KEY` | **是** | 讯飞 API Key |
| `MODEL_NAME` | 否 | 讯飞模型名，默认 `astron-code-latest` |
| `MINIMAX_API_URL` | 否 | MiniMax API 地址 |
| `MINIMAX_API_KEY` | **是** | MiniMax API Key |
| `MINIMAX_GROUP_ID` | 是 | MiniMax Group ID（TTS 需要） |
| `MINIMAX_MODEL_NAME` | 否 | 默认 `MiniMax-Text-01` |
| `MINIMAX_IMAGE_MODEL` | 否 | 默认 `image-01` |
| `MINIMAX_VIDEO_MODEL` | 否 | 默认 `video-01` |
| `MINIMAX_TTS_MODEL` | 否 | 默认 `speech-2.8-hd` |
| `BAIDU_ASR_APP_ID` | 否 | 百度语音识别 App ID |
| `BAIDU_ASR_API_KEY` | 否 | 百度语音识别 API Key |
| `BAIDU_ASR_SECRET_KEY` | 否 | 百度语音识别 Secret Key |
| `KLING_API_URL` | 否 | 可灵 API 地址 |
| `KLING_ACCESS_KEY` | 否 | 可灵 Access Key |
| `KLING_SECRET_KEY` | 否 | 可灵 Secret Key |

### B. 数据库

| 变量 | 必填 | 说明 |
|------|------|------|
| `DATABASE_URL` | 否 | 主数据库 URL（默认 SQLite 异步） |
| `DATABASE_URL_SYNC` | 否 | 同步版本（Alembic 用） |
| `CHECKPOINT_DB_URL` | 否 | LangGraph 检查点库 |
| `MYSQL_HOST` | 否 | Navicat 脚本用，默认 `127.0.0.1` |
| `MYSQL_PORT` | 否 | 默认 `3306` |
| `MYSQL_USER` | 否 | 默认 `root` |
| `MYSQL_PASSWORD` | 否 | 默认 `root` |

### C. 知识中台（KB）

| 变量 | 必填 | 说明 |
|------|------|------|
| `KB_QDRANT_MASTER_HOST` | 否 | 默认 `localhost` |
| `KB_QDRANT_REPLICA_HOST` | 否 | 默认 `localhost` |
| `KB_QDRANT_PORT` | 否 | 默认 `6333` |
| `KB_REDIS_HOST` | 否 | 默认 `localhost` |
| `KB_REDIS_PORT` | 否 | 默认 `6379` |
| `KB_HEALTH_CHECK_INTERVAL_S` | 否 | 默认 `10` |
| `KB_BEHAVIOR_LOG_SPOOL_DIR` | 否 | Agent 行为日志目录 |
| `KB_READ_BACKEND_PERCENTAGE` | 否 | 灰度切流 0-100 |
| `KB_DUAL_WRITE_LEGACY` | 否 | 是否双写旧版 |

### D. 应用 / 调试

| 变量 | 必填 | 说明 |
|------|------|------|
| `APP_DEBUG` / `KUROMI_DEBUG` | 否 | 默认 `False` |
| `STARLEARN_USER_ENV` | 否 | 自定义 .env 路径（打包安装器使用） |

---

## 联系与支持

- **项目仓库**：见 Git 仓库 README
- **API 文档**：启动后访问 `http://<host>:8000/docs`
- **日志**：`journalctl -u starlearn -f`

> 最后更新：2026-07-20