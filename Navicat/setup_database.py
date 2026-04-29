"""
星识 (Star-Learn) 数据库初始化脚本
支持 MySQL 和 SQLite 双后端，一键建表
使用方法:
  python setup_database.py                  # 自动检测后端 (MySQL > SQLite)
  python setup_database.py --backend mysql   # 强制 MySQL
  python setup_database.py --backend sqlite  # 强制 SQLite
依赖:
  MySQL 模式: pip install pymysql
  SQLite 模式: 无需额外安装 (Python 内置)
"""
import sys
import os

# MySQL 配置
MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', '123456'),
    'charset': 'utf8mb4',
}
DATABASE_NAME = 'xingshi'

BACKEND = None
MYSQL_CONN = None
SQLITE_PATH = None


# ============================================================
# 所有建表 SQL (MySQL 语法)
# ============================================================

MYSQL_TABLES = [
    # ──────────────────────────────────────────────────────
    # 1. user - 用户认证
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        nickname VARCHAR(50) DEFAULT '',
        avatar VARCHAR(500) DEFAULT '',
        current_task VARCHAR(100) DEFAULT '大数据导论',
        preferred_language VARCHAR(20) DEFAULT 'python',
        theme VARCHAR(50) DEFAULT 'ocean',
        last_agent_id VARCHAR(50) DEFAULT '',
        last_login TIMESTAMP NULL DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 2. learning_records - 学习记录
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS learning_records (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        interaction_count INT DEFAULT 0,
        code_practice_time INT DEFAULT 0,
        socratic_pass_rate FLOAT DEFAULT 0.0,
        difficulty_level VARCHAR(20) DEFAULT 'basic',
        profile_json LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
        UNIQUE KEY uq_lr_user (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 3. learning_path - 学习路径
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS learning_path (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        path_json LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 4. user_profile - 用户画像
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_profile (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        profile_json LONGTEXT,
        evaluation_json LONGTEXT,
        last_grade_record TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 5. user_preferences - 用户偏好设置
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_preferences (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        preferences_json LONGTEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 6. user_garden - 花园/植物种植
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_garden (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        seeds INT DEFAULT 3,
        garden_json LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 7. user_pet - 宠物状态
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_pet (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        pet_json LONGTEXT,
        pet_game_json LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 8. user_achievements - 用户成就
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_achievements (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        achievements_json LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 9. user_stats - 统计数据 (starlearn_stats_*)
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_stats (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        stats_json LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 10. user_notifications - 通知
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        notifications_json LONGTEXT,
        last_update_time BIGINT DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 11. user_settings - 综合设置
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_settings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        settings_json LONGTEXT,
        weather_city VARCHAR(50) DEFAULT '',
        floating_alarm_x INT DEFAULT NULL,
        floating_alarm_y INT DEFAULT NULL,
        hub_theme VARCHAR(50) DEFAULT 'light',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 12. user_coding_state - 编程练习状态
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_coding_state (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        coding_state_json LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 13. user_weather_cache - 天气缓存
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_weather_cache (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        weather_json LONGTEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 14. user_focus_history - 专注历史
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_focus_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        focus_json LONGTEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 15. user_eco_data - 生态数据
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_eco_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        eco_data_json LONGTEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 16. user_projects - 架构项目
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_projects (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        projects_json LONGTEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 17. user_calendar_events - 日历事件
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_calendar_events (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        events_json LONGTEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 18. daily_routes - 每日学习路线
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS daily_routes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        route_date DATE NOT NULL,
        tasks_json LONGTEXT,
        completed_json LONGTEXT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
        UNIQUE KEY uq_user_date (user_id, route_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 19. knowledge_nodes - 知识节点（SM2间隔重复）
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS knowledge_nodes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        node_id VARCHAR(255) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        parent_id VARCHAR(255),
        level VARCHAR(50) DEFAULT 'leaf',
        icon VARCHAR(50) DEFAULT '📚',
        subject VARCHAR(100) DEFAULT '',
        is_active TINYINT DEFAULT 0,
        first_studied_at TIMESTAMP NULL,
        last_studied_at TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sm2_data_json TEXT,
        stats_json TEXT,
        position_x REAL DEFAULT 0,
        position_y REAL DEFAULT 0,
        INDEX idx_user_id (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 20. review_records - 复习记录（SM2）
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS review_records (
        id INT AUTO_INCREMENT PRIMARY KEY,
        record_id VARCHAR(255) NOT NULL UNIQUE,
        user_id INT NOT NULL,
        node_id VARCHAR(255) NOT NULL,
        review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        quality INT DEFAULT 0,
        response_time REAL DEFAULT 0,
        sm2_result_json TEXT,
        INDEX idx_user_node (user_id, node_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 21. telemetry_data - 遥测/行为数据
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS telemetry_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id VARCHAR(50) NOT NULL,
        context_id VARCHAR(100),
        event_type VARCHAR(100) NOT NULL,
        event_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_student (student_id),
        INDEX idx_context (context_id),
        INDEX idx_event (event_type),
        INDEX idx_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 22. study_sessions - 学习时段记录
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS study_sessions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        session_date DATE NOT NULL,
        duration_minutes INT DEFAULT 0,
        start_time TEXT,
        end_time TEXT,
        subject VARCHAR(100) DEFAULT '',
        node_id VARCHAR(255) DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
        INDEX idx_user_date (user_id, session_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 23. learning_goals - 学习目标
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS learning_goals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        goal_type VARCHAR(50) NOT NULL,
        title VARCHAR(255) DEFAULT '',
        target_value INT DEFAULT 0,
        current_value INT DEFAULT 0,
        unit VARCHAR(20) DEFAULT 'minutes',
        start_date DATE,
        end_date DATE,
        is_active TINYINT DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,

    # ──────────────────────────────────────────────────────
    # 24. weekly_summary - 周学习总结
    # ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS weekly_summary (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        week_start_date DATE NOT NULL,
        daily_minutes TEXT,
        hourly_distribution TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
        UNIQUE KEY uq_user_week (user_id, week_start_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]

# 表名列表（用于日志输出）
TABLE_NAMES = [
    "user",
    "learning_records",
    "learning_path",
    "user_profile",
    "user_preferences",
    "user_garden",
    "user_pet",
    "user_achievements",
    "user_stats",
    "user_notifications",
    "user_settings",
    "user_coding_state",
    "user_weather_cache",
    "user_focus_history",
    "user_eco_data",
    "user_projects",
    "user_calendar_events",
    "daily_routes",
    "knowledge_nodes",
    "review_records",
    "telemetry_data",
    "study_sessions",
    "learning_goals",
    "weekly_summary",
]


# ============================================================
# SQLite 建表 SQL（转换 MySQL 语法）
# ============================================================

def mysql_to_sqlite(sql):
    """将 MySQL CREATE TABLE 语句转换为 SQLite 兼容语法，返回 (sql, extra_indices)"""
    import re

    extra_indices = []

    # 1. 提取表名
    table_match = re.search(r'CREATE TABLE IF NOT EXISTS (\w+)', sql)
    table_name = table_match.group(1) if table_match else 'unknown'

    # 2. 提取并移除内联 INDEX 定义 (SQLite 不支持)
    # INDEX idx_name (col1, col2),
    inline_indices = re.findall(r'INDEX (\w+) \(([^)]+)\)', sql)
    for idx_name, cols in inline_indices:
        extra_indices.append(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({cols});")
    sql = re.sub(r',?\s*INDEX \w+ \([^)]+\)', '', sql)

    # 3. 提取并移除内联 UNIQUE KEY 定义
    inline_uniques = re.findall(r'UNIQUE KEY (\w+) \(([^)]+)\)', sql)
    for uq_name, cols in inline_uniques:
        extra_indices.append(f"CREATE UNIQUE INDEX IF NOT EXISTS {uq_name} ON {table_name} ({cols});")
    sql = re.sub(r',?\s*UNIQUE KEY \w+ \([^)]+\)', '', sql)

    # 4. 移除 MySQL 特有语法（先处理，避免干扰列级替换）
    # 移除 ENGINE/CHARSET/COLLATE
    sql = re.sub(r'\)\s*ENGINE=InnoDB[^;]*', ')', sql)

    # 移除 FOREIGN KEY 整行（包括 ON DELETE CASCADE）
    sql = re.sub(r',?\s*FOREIGN KEY\s*\([^)]+\)\s*REFERENCES\s+\w+\s*\([^)]+\)(\s+ON\s+DELETE\s+CASCADE)?', '', sql)

    # 移除独立的 UNIQUE KEY 定义（已在步骤3处理）
    sql = re.sub(r',?\s*UNIQUE\s+KEY\s+\w+\s*\([^)]+\)', '', sql)

    # 5. 主键转换（先处理 INT AUTO_INCREMENT PRIMARY KEY → 单主键）
    # INT AUTO_INCREMENT / INT AUTO_INCREMENT PRIMARY KEY → INTEGER PRIMARY KEY AUTOINCREMENT
    sql = re.sub(r'\bINT\s+AUTO_INCREMENT\s+PRIMARY\s+KEY\b', 'INTEGER PRIMARY KEY AUTOINCREMENT', sql)
    sql = re.sub(r'\bINT\s+NOT\s+NULL\s+AUTO_INCREMENT\b', 'INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT', sql)

    # 6. 时间戳转换（长的先替换）
    sql = sql.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
                      "TEXT DEFAULT (datetime('now','localtime'))")
    sql = sql.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                      "TEXT DEFAULT (datetime('now','localtime'))")
    sql = sql.replace("TIMESTAMP NULL DEFAULT NULL", "TEXT")

    # 7. 通用类型映射
    sql = sql.replace("AUTO_INCREMENT", "AUTOINCREMENT")
    sql = sql.replace("LONGTEXT", "TEXT")
    sql = sql.replace("BIGINT DEFAULT 0", "INTEGER DEFAULT 0")
    sql = sql.replace("BIGINT", "INTEGER")
    sql = sql.replace("INT NOT NULL UNIQUE", "INTEGER NOT NULL UNIQUE")
    sql = sql.replace("INT NOT NULL", "INTEGER NOT NULL")
    sql = re.sub(r'\bINT\s+DEFAULT\s+', 'INTEGER DEFAULT ', sql)
    sql = sql.replace("FLOAT DEFAULT 0.0", "REAL DEFAULT 0.0")
    sql = sql.replace("FLOAT", "REAL")
    sql = sql.replace("DATE NOT NULL", "TEXT NOT NULL")
    sql = re.sub(r'VARCHAR\s*\(\d+\)', 'TEXT', sql)

    # 清理：移除行尾多余逗号（SQLite 不允许尾随逗号）
    sql = re.sub(r',\s*\)', '\n)', sql)

    # 修复重复逗号
    sql = sql.replace(', ,', ',')

    # 清理多余空白行
    sql = re.sub(r'\n\s*\n', '\n', sql)
    sql = sql.strip()

    return sql, extra_indices


# ============================================================
# 后端检测
# ============================================================

def detect_backend():
    """检测可用的数据库后端"""
    global BACKEND

    if BACKEND:
        return BACKEND

    # 先尝试 MySQL
    try:
        import pymysql
        conn = pymysql.connect(**MYSQL_CONFIG)
        conn.close()
        BACKEND = 'mysql'
        return BACKEND
    except Exception:
        pass

    # 回退到 SQLite
    try:
        import sqlite3
        BACKEND = 'sqlite'
        return BACKEND
    except Exception:
        pass

    print("错误: 无法连接到任何数据库后端")
    print("  MySQL: pip install pymysql")
    print("  SQLite: Python 内置，无需安装")
    sys.exit(1)


# ============================================================
# MySQL 建表
# ============================================================

def ensure_user_columns(cursor, conn):
    """为已有的 user 表补加新字段（兼容旧版本数据库）"""
    new_columns = [
        ("preferred_language", "VARCHAR(20) DEFAULT 'python'"),
        ("theme", "VARCHAR(50) DEFAULT 'ocean'"),
        ("last_agent_id", "VARCHAR(50) DEFAULT ''"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]
    for col_name, col_def in new_columns:
        try:
            cursor.execute(f"SHOW COLUMNS FROM user LIKE '{col_name}'")
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_def}")
                conn.commit()
                print(f"  [OK] user.{col_name} 字段已添加")
        except Exception as e:
            print(f"  [WARN] 添加 user.{col_name} 失败: {e}")


def fix_foreign_keys(cursor, conn):
    """修复旧表的外键约束，确保所有外键都有 ON DELETE CASCADE"""
    # 查找所有引用 user(id) 的外键
    cursor.execute("""
        SELECT TABLE_NAME, CONSTRAINT_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE REFERENCED_TABLE_NAME = 'user'
          AND REFERENCED_COLUMN_NAME = 'id'
          AND TABLE_SCHEMA = %s
    """, (DATABASE_NAME,))
    fks = cursor.fetchall()
    for table_name, constraint_name in fks:
        try:
            # 检查是否已有 ON DELETE CASCADE
            cursor.execute("""
                SELECT DELETE_RULE
                FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS
                WHERE CONSTRAINT_NAME = %s AND CONSTRAINT_SCHEMA = %s
            """, (constraint_name, DATABASE_NAME))
            rule_row = cursor.fetchone()
            if rule_row and rule_row[0] == 'CASCADE':
                continue  # 已经是 CASCADE，跳过

            # 删除旧外键，重建带 CASCADE 的新外键
            cursor.execute(f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{constraint_name}`")
            cursor.execute(f"""
                ALTER TABLE `{table_name}`
                ADD CONSTRAINT `{constraint_name}`
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            """)
            conn.commit()
            print(f"  [OK] {table_name}.{constraint_name} 已修复为 ON DELETE CASCADE")
        except Exception as e:
            print(f"  [WARN] 修复 {table_name}.{constraint_name} 失败: {e}")


def setup_mysql():
    print("=" * 60)
    print("  星识 (Star-Learn) 数据库初始化 - MySQL 模式")
    print("=" * 60)
    print(f"  主机: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")
    print(f"  用户: {MYSQL_CONFIG['user']}")
    print(f"  数据库: {DATABASE_NAME}")
    print("-" * 60)

    try:
        import pymysql
    except ImportError:
        print("\n错误: 未安装 pymysql")
        print("请运行: pip install pymysql")
        sys.exit(1)

    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        # 创建数据库
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME} "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE {DATABASE_NAME}")
        print(f"  [OK] 数据库 '{DATABASE_NAME}' 就绪\n")

        # 确保 user 表有新增字段（兼容旧表）
        ensure_user_columns(cursor, conn)
        print()

        # 修复旧表外键约束
        fix_foreign_keys(cursor, conn)

        # 逐个建表
        success_count = 0
        for i, sql in enumerate(MYSQL_TABLES):
            table_name = TABLE_NAMES[i]
            try:
                cursor.execute(sql)
                print(f"  [OK] {table_name:30s} 就绪")
                success_count += 1
            except Exception as e:
                print(f"  [FAIL] {table_name:30s} 错误: {e}")

        conn.commit()
        print("-" * 60)
        print(f"  完成! {success_count}/{len(MYSQL_TABLES)} 张表创建成功")
        print(f"  数据库 '{DATABASE_NAME}' 初始化完成")
        print("=" * 60)

    except pymysql.err.OperationalError as e:
        print(f"\n连接 MySQL 失败: {e}")
        print("请检查:")
        print("  1) MySQL 服务是否已启动")
        print("  2) 用户名/密码是否正确 (默认 root/root)")
        print("  3) 端口是否正确 (默认 3306)")
        print(f"\n提示: 可使用 python setup_database.py --backend sqlite 切换到 SQLite")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


# ============================================================
# SQLite 建表
# ============================================================

def setup_sqlite():
    global SQLITE_PATH
    import sqlite3

    SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xingshi.db')

    print("=" * 60)
    print("  星识 (Star-Learn) 数据库初始化 - SQLite 模式")
    print("=" * 60)
    print(f"  数据库文件: {SQLITE_PATH}")
    print("-" * 60)

    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()

    # 启用外键 (SQLite 默认关闭)
    cursor.execute("PRAGMA foreign_keys = ON")

    # 开启 WAL 模式提高并发
    cursor.execute("PRAGMA journal_mode = WAL")

    success_count = 0
    for i, sql in enumerate(MYSQL_TABLES):
        table_name = TABLE_NAMES[i]
        try:
            sqlite_sql, extra_indices = mysql_to_sqlite(sql)
            cursor.execute(sqlite_sql)
            # 执行额外的索引创建语句
            for idx_sql in extra_indices:
                try:
                    cursor.execute(idx_sql)
                except Exception as e:
                    print(f"  [WARN] 索引创建跳过: {e}")
            print(f"  [OK] {table_name:30s} 就绪")
            success_count += 1
        except Exception as e:
            print(f"  [FAIL] {table_name:30s} 错误: {e}")

    conn.commit()
    conn.close()

    print("-" * 60)
    print(f"  完成! {success_count}/{len(MYSQL_TABLES)} 张表创建成功")
    print(f"  数据库文件: {SQLITE_PATH}")
    print("=" * 60)


# ============================================================
# 主入口
# ============================================================

def main():
    global BACKEND

    # 解析命令行参数
    args = sys.argv[1:]
    backend_arg = None
    for arg in args:
        if arg.startswith('--backend='):
            backend_arg = arg.split('=', 1)[1]
        elif arg == '--backend':
            idx = args.index(arg)
            if idx + 1 < len(args):
                backend_arg = args[idx + 1]

    if backend_arg:
        backend_arg = backend_arg.lower()
        if backend_arg not in ('mysql', 'sqlite', 'auto'):
            print(f"错误: 不支持的 backend 类型 '{backend_arg}'")
            print("可选值: mysql, sqlite, auto")
            sys.exit(1)
        if backend_arg == 'auto':
            detect_backend()
        else:
            BACKEND = backend_arg
    else:
        detect_backend()

    print(f"\n检测到后端: {BACKEND.upper()}\n")

    if BACKEND == 'mysql':
        setup_mysql()
    elif BACKEND == 'sqlite':
        setup_sqlite()

    # 如果是 SQLite，提示 db.py 后续会自动使用
    if BACKEND == 'sqlite':
        print("\n提示: SQLite 数据库文件位于项目根目录 'xingshi.db'")
        print("db.py 会自动检测并使用此文件")

    # 显示下一步
    print("\n下一步: 运行 python main.py 启动项目")


if __name__ == '__main__':
    main()
