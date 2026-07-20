# SQL 初始化脚本说明

> 本目录存放 **纯 SQL 格式** 的数据库初始化文件，用于 **离线部署**、**容器初始化**、**K8s InitContainer** 等场景。
> 对于普通部署，请直接使用 `python Navicat/setup_database.py` 脚本（更智能、可自动兼容旧表）。

## 文件清单

| 文件 | 后端 | 说明 |
|------|------|------|
| `init_mysql.sql` | MySQL 5.7+ / 8.0 | 标准 MySQL 初始化脚本 |
| `init_sqlite.sql` | SQLite 3 | SQLite 初始化脚本（语法转换后） |
| `drop_all.sql` | MySQL | 危险！删除数据库所有表（仅限测试环境） |

## 使用方法

### MySQL

```bash
# 1. 创建数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS xingshi \
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. 执行初始化脚本
mysql -u starlearn -p xingshi < init_mysql.sql

# 3. 验证
mysql -u starlearn -p xingshi -e "SHOW TABLES;" | head -20
```

### SQLite

```bash
# 方式一：通过 sqlite3 CLI
sqlite3 xingshi_v2.db < init_sqlite.sql

# 方式二：通过 Python
python -c "
import sqlite3
with open('init_sqlite.sql', 'r', encoding='utf-8') as f:
    sql = f.read()
conn = sqlite3.connect('xingshi_v2.db')
conn.executescript(sql)
conn.close()
print('OK')
"
```

## 容器 / K8s 集成示例

### Dockerfile（MySQL）

```dockerfile
FROM mysql:8.0
COPY init_mysql.sql /docker-entrypoint-initdb.d/
ENV MYSQL_DATABASE=xingshi
ENV MYSQL_USER=starlearn
ENV MYSQL_PASSWORD=secret
ENV MYSQL_ROOT_PASSWORD=rootsecret
```

启动容器时自动执行 `/docker-entrypoint-initdb.d/*.sql`。

### K8s InitContainer

```yaml
initContainers:
  - name: init-db
    image: mysql:8.0
    command: ["sh", "-c"]
    args:
      - |
        apt-get update && apt-get install -y default-mysql-client
        mysql -h mysql -u root -p"$MYSQL_ROOT_PASSWORD" \
          -e "CREATE DATABASE IF NOT EXISTS xingshi \
              CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        mysql -h mysql -u root -p"$MYSQL_ROOT_PASSWORD" xingshi < /sql/init_mysql.sql
    volumeMounts:
      - name: sql-scripts
        mountPath: /sql
  - name: app
    image: starlearn:1.0.0
    # ...
volumes:
  - name: sql-scripts
    configMap:
      name: starlearn-sql
```

## 表结构总览

脚本会创建 34 张表，主要分类：

| 类别 | 表 |
|------|---|
| 用户与认证 | `user`, `user_profile`, `user_preferences`, `user_settings`, `user_evaluations` |
| 学习记录 | `learning_records`, `learning_path`, `learning_goals`, `study_sessions`, `weekly_summary` |
| 知识体系 | `knowledge_nodes`, `review_records` |
| 用户生态 | `user_garden`, `user_pet`, `user_achievements`, `user_stats`, `user_notifications`, `user_eco_data`, `user_calendar_events` |
| 用户扩展 | `user_weather_cache`, `user_focus_history`, `user_projects`, `user_coding_state` |
| 课程与课堂 | `classroom_records`, `classroom_sessions`, `course_generation_status`, `quiz_records`, `agent_turn_records` |
| 闪卡 | `user_flashcard_progress`, `user_flashcard_sessions` |
| AI 对话 | `messages`, `conversation_summaries`, `user_memories`, `daily_routes`, `telemetry_data` |

## 注意事项

- MySQL 脚本使用 `CREATE TABLE IF NOT EXISTS`，**幂等可重复执行**。
- SQLite 脚本外键默认关闭（SQLite 限制），如需启用外键，请在使用前执行 `PRAGMA foreign_keys = ON;`。
- 字符集：MySQL 全部 `utf8mb4`，SQLite 默认 UTF-8。
- 大字段（`LONGTEXT`）存储 JSON / 学习画像 / 课程完整数据。
- 不要在生产环境执行 `drop_all.sql`。

## 更新策略

每次新增 / 修改表结构：

1. 修改 `Navicat/setup_database.py` 中的 `MYSQL_TABLES` 列表（源真相）。
2. 同步更新本目录下的 `init_mysql.sql` 与 `init_sqlite.sql`。
3. （可选）创建 Alembic 迁移：`alembic revision --autogenerate -m "..."`。

> 最后更新：2026-07-20