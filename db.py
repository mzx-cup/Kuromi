import json
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# MySQL 配置
MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', 'root'),
    'database': 'xingshi',
    'charset': 'utf8mb4',
}

# SQLite 数据库路径
SQLITE_PATH = os.environ.get('SQLITE_PATH', os.path.join(BASE_DIR, 'xingshi.db'))

# 后端类型: 'mysql', 'sqlite', 'json'
DB_BACKEND = os.environ.get('STARLEARN_DB_BACKEND', 'auto')
_initialized = False
_effective_backend = None

LOCAL_STORAGE_PATH = os.path.join(BASE_DIR, 'local_storage.json')


def _detect_backend():
    """自动检测可用的数据库后端：MySQL > SQLite > JSON"""
    global _effective_backend
    if _effective_backend:
        return _effective_backend

    if DB_BACKEND in ('mysql', 'sqlite', 'json'):
        _effective_backend = DB_BACKEND
        return _effective_backend

    # auto 模式：依次尝试
    try:
        import pymysql
        conn = pymysql.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database'],
        )
        conn.close()
        _effective_backend = 'mysql'
        return 'mysql'
    except Exception:
        pass

    # 检查 SQLite 文件或尝试创建
    try:
        import sqlite3
        # 如果文件已存在直接使用，否则尝试连接验证可用性
        conn = sqlite3.connect(SQLITE_PATH)
        conn.close()
        _effective_backend = 'sqlite'
        return 'sqlite'
    except Exception:
        pass

    _effective_backend = 'json'
    return 'json'


@contextmanager
def get_db():
    """获取数据库连接上下文，自动选择 MySQL / SQLite / JSON fallback"""
    backend = _detect_backend()
    conn = None
    cursor = None

    if backend == 'mysql':
        try:
            import pymysql
            conn = pymysql.connect(**MYSQL_CONFIG)
            yield conn
            return
        except Exception as e:
            print(f"MySQL 连接失败: {e}, 尝试 SQLite...")

    if backend == 'sqlite' or (backend == 'mysql' and conn is None):
        try:
            import sqlite3
            conn = sqlite3.connect(SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            return
        except Exception as e:
            print(f"SQLite 连接失败: {e}, 使用本地存储")

    # 最终 fallback: JSON 文件
    yield None


def load_local_storage():
    """加载本地 JSON 存储"""
    if os.path.exists(LOCAL_STORAGE_PATH):
        try:
            with open(LOCAL_STORAGE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        'users': [], 'learning_records': [], 'learning_paths': [],
        'user_profiles': [], 'user_preferences': {}, 'user_gardens': [],
        'user_pets': [], 'user_achievements': [], 'user_stats': [],
        'user_notifications': [], 'user_settings': [], 'user_coding_states': [],
        'user_weather_caches': [], 'user_focus_histories': [], 'user_eco_data': [],
        'user_projects': [], 'user_calendar_events': [], 'daily_routes': [],
        'user_login_records': [], 'user_evaluations': [], 'user_memories': [],
    }


def save_local_storage(data):
    """保存到本地 JSON 存储"""
    try:
        with open(LOCAL_STORAGE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存本地存储失败: {e}")


def _get_json_record(storage, table_key, user_id):
    """在 JSON fallback 中查找 user_id 对应的记录"""
    for record in storage.get(table_key, []):
        if record.get('user_id') == user_id:
            return record
    return None


# ============================================================
# 用户认证
# ============================================================

def get_user_by_username(username):
    with get_db() as conn:
        if conn is not None:
            try:
                if _is_mysql(conn):
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
                    user = cursor.fetchone()
                    cursor.close()
                    return user
                else:
                    # SQLite
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
                    row = cursor.fetchone()
                    cursor.close()
                    return dict(row) if row else None
            except Exception as e:
                print(f"数据库查询失败: {e}")

        storage = load_local_storage()
        for user in storage.get('users', []):
            if user.get('username') == username:
                return user
        return None


def create_user(username, hashed_password, avatar='', nickname=''):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                sql = """INSERT INTO user (username, password, avatar, nickname)
                         VALUES (?, ?, ?, ?)""" if _is_sqlite(conn) else \
                      """INSERT INTO user (username, password, avatar, nickname)
                         VALUES (%s, %s, %s, %s)"""
                cursor.execute(sql, (username, hashed_password, avatar, nickname))
                conn.commit()
                user_id = cursor.lastrowid
                if _is_sqlite(conn):
                    # SQLite: lastrowid 直接可用
                    pass
                else:
                    user_id = cursor.lastrowid
                cursor.close()
                return user_id
            except Exception as e:
                print(f"数据库插入失败: {e}")

        # JSON fallback
        storage = load_local_storage()
        user_id = len(storage.get('users', [])) + 1
        new_user = {
            'id': user_id, 'username': username, 'password': hashed_password,
            'avatar': avatar, 'nickname': nickname, 'current_task': '大数据导论',
            'preferred_language': 'python', 'theme': 'ocean', 'last_agent_id': '',
            'created_at': 'local', 'last_login': 'local',
        }
        storage['users'] = storage.get('users', []) + [new_user]
        save_local_storage(storage)
        return user_id


def update_user_nickname(user_id, nickname):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("UPDATE user SET nickname = ? WHERE id = ?", (nickname, user_id))
                else:
                    cursor.execute("UPDATE user SET nickname = %s WHERE id = %s", (nickname, user_id))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库更新失败: {e}")

        storage = load_local_storage()
        for user in storage.get('users', []):
            if user.get('id') == user_id:
                user['nickname'] = nickname
                save_local_storage(storage)
                break


def update_user_avatar(user_id, avatar):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("UPDATE user SET avatar = ? WHERE id = ?", (avatar, user_id))
                else:
                    cursor.execute("UPDATE user SET avatar = %s WHERE id = %s", (avatar, user_id))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库更新失败: {e}")

        storage = load_local_storage()
        for user in storage.get('users', []):
            if user.get('id') == user_id:
                user['avatar'] = avatar
                save_local_storage(storage)
                break


def update_user_task(user_id, task):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("UPDATE user SET current_task = ? WHERE id = ?", (task, user_id))
                else:
                    cursor.execute("UPDATE user SET current_task = %s WHERE id = %s", (task, user_id))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库更新失败: {e}")

        storage = load_local_storage()
        for user in storage.get('users', []):
            if user.get('id') == user_id:
                user['current_task'] = task
                save_local_storage(storage)
                break


def update_last_login(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        "UPDATE user SET last_login = datetime('now','localtime') WHERE id = ?",
                        (user_id,)
                    )
                else:
                    cursor.execute("UPDATE user SET last_login = NOW() WHERE id = %s", (user_id,))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库更新失败: {e}")

        storage = load_local_storage()
        for user in storage.get('users', []):
            if user.get('id') == user_id:
                user['last_login'] = 'local'
                save_local_storage(storage)
                break


def ensure_login_records_table(conn):
    """Create the login audit table when the active database supports SQL."""
    if conn is None:
        return

    cursor = conn.cursor()
    if _is_sqlite(conn):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_login_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT NOT NULL,
                success INTEGER DEFAULT 0,
                failure_reason TEXT DEFAULT '',
                ip_address TEXT DEFAULT '',
                user_agent TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_login_records_user ON user_login_records (user_id, created_at)"
        )
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_login_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                username VARCHAR(50) NOT NULL,
                success TINYINT DEFAULT 0,
                failure_reason VARCHAR(255) DEFAULT '',
                ip_address VARCHAR(64) DEFAULT '',
                user_agent VARCHAR(512) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_login_user (user_id, created_at),
                CONSTRAINT fk_login_user FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    conn.commit()
    cursor.close()


def ensure_theme_prefs_column(conn):
    """Add theme_prefs JSON column to user table if missing."""
    if conn is None:
        return
    cursor = conn.cursor()
    if _is_sqlite(conn):
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN theme_prefs TEXT DEFAULT ''")
        except:
            pass  # column already exists
    else:
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN theme_prefs JSON DEFAULT NULL")
        except:
            pass
    conn.commit()
    cursor.close()


def record_login_event(user_id, username, success, failure_reason='', ip_address='', user_agent=''):
    """Persist a login attempt without storing raw credentials."""
    username = username or ''
    failure_reason = failure_reason or ''
    ip_address = ip_address or ''
    user_agent = (user_agent or '')[:512]

    with get_db() as conn:
        if conn is not None:
            try:
                ensure_login_records_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """
                        INSERT INTO user_login_records
                            (user_id, username, success, failure_reason, ip_address, user_agent)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (user_id, username, 1 if success else 0, failure_reason, ip_address, user_agent)
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO user_login_records
                            (user_id, username, success, failure_reason, ip_address, user_agent)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (user_id, username, 1 if success else 0, failure_reason, ip_address, user_agent)
                    )
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"登录记录写入失败: {e}")

        storage = load_local_storage()
        records = storage.get('user_login_records', [])
        records.append({
            'id': len(records) + 1,
            'user_id': user_id,
            'username': username,
            'success': bool(success),
            'failure_reason': failure_reason,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
        storage['user_login_records'] = records
        save_local_storage(storage)


def update_user_meta(user_id, preferred_language=None, theme=None, last_agent_id=None):
    """更新用户元数据（语言、主题、最近代理）"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                updates = []
                params = []
                if preferred_language is not None:
                    updates.append("preferred_language = ?" if _is_sqlite(conn) else "preferred_language = %s")
                    params.append(preferred_language)
                if theme is not None:
                    updates.append("theme = ?" if _is_sqlite(conn) else "theme = %s")
                    params.append(theme)
                if last_agent_id is not None:
                    updates.append("last_agent_id = ?" if _is_sqlite(conn) else "last_agent_id = %s")
                    params.append(last_agent_id)
                if updates:
                    params.append(user_id)
                    sql = f"UPDATE user SET {', '.join(updates)} WHERE id = {'?' if _is_sqlite(conn) else '%s'}"
                    cursor.execute(sql, tuple(params))
                    conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库更新失败: {e}")

        storage = load_local_storage()
        for user in storage.get('users', []):
            if user.get('id') == user_id:
                if preferred_language is not None:
                    user['preferred_language'] = preferred_language
                if theme is not None:
                    user['theme'] = theme
                if last_agent_id is not None:
                    user['last_agent_id'] = last_agent_id
                save_local_storage(storage)
                break


def delete_user(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("DELETE FROM user WHERE id = ?", (user_id,))
                else:
                    cursor.execute("DELETE FROM user WHERE id = %s", (user_id,))
                conn.commit()
                affected = cursor.rowcount
                cursor.close()
                return affected > 0
            except Exception as e:
                print(f"数据库删除失败: {e}")
                return False

        storage = load_local_storage()
        original_length = len(storage.get('users', []))
        storage['users'] = [u for u in storage.get('users', []) if u.get('id') != user_id]
        for key in ('learning_records', 'learning_paths', 'user_profiles',
                     'user_gardens', 'user_pets', 'user_achievements', 'user_stats',
                     'user_notifications', 'user_settings', 'user_coding_states',
                     'user_weather_caches', 'user_focus_histories', 'user_eco_data',
                     'user_projects', 'user_calendar_events', 'daily_routes'):
            storage[key] = [r for r in storage.get(key, []) if r.get('user_id') != user_id]
        save_local_storage(storage)
        return len(storage.get('users', [])) < original_length


# ============================================================
# 学习记录
# ============================================================

def get_learning_record(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT * FROM learning_records WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT * FROM learning_records WHERE user_id = %s", (user_id,))
                record = cursor.fetchone()
                cursor.close()
                return dict(record) if record and _is_sqlite(conn) else record
            except Exception as e:
                print(f"数据库查询失败: {e}")

        return _get_json_record(load_local_storage(), 'learning_records', user_id)


def save_learning_record(user_id, interaction_count, code_practice_time,
                         socratic_pass_rate, difficulty_level, profile_json):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("""
                        INSERT INTO learning_records
                        (user_id, interaction_count, code_practice_time, socratic_pass_rate, difficulty_level, profile_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET
                            interaction_count=excluded.interaction_count,
                            code_practice_time=excluded.code_practice_time,
                            socratic_pass_rate=excluded.socratic_pass_rate,
                            difficulty_level=excluded.difficulty_level,
                            profile_json=excluded.profile_json
                    """, (user_id, interaction_count, code_practice_time, socratic_pass_rate, difficulty_level, profile_json))
                else:
                    cursor.execute("""
                        INSERT INTO learning_records
                        (user_id, interaction_count, code_practice_time, socratic_pass_rate, difficulty_level, profile_json)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            interaction_count=%s, code_practice_time=%s, socratic_pass_rate=%s,
                            difficulty_level=%s, profile_json=%s
                    """, (user_id, interaction_count, code_practice_time, socratic_pass_rate,
                          difficulty_level, profile_json,
                          interaction_count, code_practice_time, socratic_pass_rate,
                          difficulty_level, profile_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for record in storage.get('learning_records', []):
            if record.get('user_id') == user_id:
                record.update({
                    'interaction_count': interaction_count,
                    'code_practice_time': code_practice_time,
                    'socratic_pass_rate': socratic_pass_rate,
                    'difficulty_level': difficulty_level,
                    'profile_json': profile_json,
                })
                save_local_storage(storage)
                return
        storage['learning_records'].append({
            'id': len(storage.get('learning_records', [])) + 1,
            'user_id': user_id,
            'interaction_count': interaction_count,
            'code_practice_time': code_practice_time,
            'socratic_pass_rate': socratic_pass_rate,
            'difficulty_level': difficulty_level,
            'profile_json': profile_json,
            'updated_at': 'local',
        })
        save_local_storage(storage)


# ============================================================
# 用户评估指标历史 (user_evaluations)
# ============================================================

def _ensure_user_evaluations_table(conn):
    cursor = conn.cursor()
    if _is_sqlite(conn):
        cursor.execute("""CREATE TABLE IF NOT EXISTS user_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            interaction_count INTEGER DEFAULT 0,
            socratic_pass_rate REAL DEFAULT 0.0,
            difficulty_level TEXT DEFAULT 'basic',
            code_practice_time INTEGER DEFAULT 0,
            focus_time_today INTEGER DEFAULT 0,
            flashcards_studied INTEGER DEFAULT 0,
            streak_days INTEGER DEFAULT 0,
            eval_json TEXT,
            record_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, record_date)
        )""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_evaluations_user_date ON user_evaluations (user_id, record_date)")
    else:
        import pymysql
        cursor.execute("""CREATE TABLE IF NOT EXISTS user_evaluations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            interaction_count INT DEFAULT 0,
            socratic_pass_rate FLOAT DEFAULT 0.0,
            difficulty_level VARCHAR(20) DEFAULT 'basic',
            code_practice_time INT DEFAULT 0,
            focus_time_today INT DEFAULT 0,
            flashcards_studied INT DEFAULT 0,
            streak_days INT DEFAULT 0,
            eval_json LONGTEXT,
            record_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_eval_user_date (user_id, record_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
        try:
            cursor.execute("CREATE INDEX idx_user_evaluations_user_date ON user_evaluations (user_id, record_date)")
        except Exception:
            pass  # 索引可能已存在
    conn.commit()
    cursor.close()


def get_user_evaluation(user_id, record_date=None):
    if record_date is None:
        from datetime import date
        record_date = date.today().isoformat()
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_user_evaluations_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        "SELECT * FROM user_evaluations WHERE user_id = ? AND record_date = ?",
                        (user_id, record_date),
                    )
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        "SELECT * FROM user_evaluations WHERE user_id = %s AND record_date = %s",
                        (user_id, record_date),
                    )
                record = cursor.fetchone()
                cursor.close()
                return dict(record) if record and _is_sqlite(conn) else record
            except Exception as e:
                print(f"[DB] 查询 user_evaluations 失败: {e}")

        # fallback to local storage
        storage = load_local_storage()
        for rec in storage.get('user_evaluations', []):
            if rec.get('user_id') == user_id and rec.get('record_date') == record_date:
                return rec
        return None


def save_user_evaluation_fields(user_id, record_date, interaction_count=None,
                         socratic_pass_rate=None, difficulty_level=None,
                         code_practice_time=None, focus_time_today=None,
                         flashcards_studied=None, streak_days=None,
                         eval_json=None):
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_user_evaluations_table(conn)
                cursor = conn.cursor()
                # 先查询现有值，None 字段保持原值
                if _is_sqlite(conn):
                    cursor.execute(
                        "SELECT * FROM user_evaluations WHERE user_id = ? AND record_date = ?",
                        (user_id, record_date),
                    )
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        "SELECT * FROM user_evaluations WHERE user_id = %s AND record_date = %s",
                        (user_id, record_date),
                    )
                existing = cursor.fetchone()
                if existing:
                    existing = dict(existing) if _is_sqlite(conn) else existing
                else:
                    existing = {}

                def _val(key, new_val, default=0):
                    if new_val is not None:
                        return new_val
                    return existing.get(key, default)

                vals = {
                    'interaction_count': _val('interaction_count', interaction_count, 0),
                    'socratic_pass_rate': _val('socratic_pass_rate', socratic_pass_rate, 0.0),
                    'difficulty_level': _val('difficulty_level', difficulty_level, 'basic'),
                    'code_practice_time': _val('code_practice_time', code_practice_time, 0),
                    'focus_time_today': _val('focus_time_today', focus_time_today, 0),
                    'flashcards_studied': _val('flashcards_studied', flashcards_studied, 0),
                    'streak_days': _val('streak_days', streak_days, 0),
                    'eval_json': eval_json if eval_json is not None else existing.get('eval_json'),
                }

                if _is_sqlite(conn):
                    cursor.execute("""
                        INSERT INTO user_evaluations
                        (user_id, record_date, interaction_count, socratic_pass_rate,
                         difficulty_level, code_practice_time, focus_time_today,
                         flashcards_studied, streak_days, eval_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(user_id, record_date) DO UPDATE SET
                            interaction_count=excluded.interaction_count,
                            socratic_pass_rate=excluded.socratic_pass_rate,
                            difficulty_level=excluded.difficulty_level,
                            code_practice_time=excluded.code_practice_time,
                            focus_time_today=excluded.focus_time_today,
                            flashcards_studied=excluded.flashcards_studied,
                            streak_days=excluded.streak_days,
                            eval_json=excluded.eval_json
                    """, (user_id, record_date, vals['interaction_count'],
                          vals['socratic_pass_rate'], vals['difficulty_level'],
                          vals['code_practice_time'], vals['focus_time_today'],
                          vals['flashcards_studied'], vals['streak_days'],
                          vals['eval_json']))
                else:
                    cursor.execute("""
                        INSERT INTO user_evaluations
                        (user_id, record_date, interaction_count, socratic_pass_rate,
                         difficulty_level, code_practice_time, focus_time_today,
                         flashcards_studied, streak_days, eval_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            interaction_count=%s,
                            socratic_pass_rate=%s,
                            difficulty_level=%s,
                            code_practice_time=%s,
                            focus_time_today=%s,
                            flashcards_studied=%s,
                            streak_days=%s,
                            eval_json=%s
                    """, (user_id, record_date, vals['interaction_count'],
                          vals['socratic_pass_rate'], vals['difficulty_level'],
                          vals['code_practice_time'], vals['focus_time_today'],
                          vals['flashcards_studied'], vals['streak_days'],
                          vals['eval_json'],
                          vals['interaction_count'], vals['socratic_pass_rate'],
                          vals['difficulty_level'], vals['code_practice_time'],
                          vals['focus_time_today'], vals['flashcards_studied'],
                          vals['streak_days'], vals['eval_json']))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"[DB] 保存 user_evaluations 失败: {e}")

        # fallback to local storage
        storage = load_local_storage()
        found = False
        for rec in storage.get('user_evaluations', []):
            if rec.get('user_id') == user_id and rec.get('record_date') == record_date:
                if interaction_count is not None:
                    rec['interaction_count'] = interaction_count
                if socratic_pass_rate is not None:
                    rec['socratic_pass_rate'] = socratic_pass_rate
                if difficulty_level is not None:
                    rec['difficulty_level'] = difficulty_level
                if code_practice_time is not None:
                    rec['code_practice_time'] = code_practice_time
                if focus_time_today is not None:
                    rec['focus_time_today'] = focus_time_today
                if flashcards_studied is not None:
                    rec['flashcards_studied'] = flashcards_studied
                if streak_days is not None:
                    rec['streak_days'] = streak_days
                if eval_json is not None:
                    rec['eval_json'] = eval_json
                found = True
                break
        if not found:
            storage['user_evaluations'].append({
                'user_id': user_id,
                'record_date': record_date,
                'interaction_count': interaction_count or 0,
                'socratic_pass_rate': socratic_pass_rate or 0.0,
                'difficulty_level': difficulty_level or 'basic',
                'code_practice_time': code_practice_time or 0,
                'focus_time_today': focus_time_today or 0,
                'flashcards_studied': flashcards_studied or 0,
                'streak_days': streak_days or 0,
                'eval_json': eval_json,
            })
        save_local_storage(storage)


# ============================================================
# 学习路径
# ============================================================

def _ensure_learning_path_table(conn):
    """自动创建 learning_path 表，并补全缺失的列"""
    try:
        cursor = conn.cursor()
        if _is_sqlite(conn):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_path (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    path_json TEXT,
                    generated_at TEXT,
                    reasoning TEXT,
                    data_sources TEXT,
                    confidence REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_learning_path_user ON learning_path (user_id)")
            # 检查并补全缺失列（SQLite）
            cursor.execute("PRAGMA table_info(learning_path)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            col_defs = [
                ("generated_at", "TEXT"),
                ("reasoning", "TEXT"),
                ("data_sources", "TEXT"),
                ("confidence", "REAL DEFAULT 0.0"),
            ]
            for col_name, col_type in col_defs:
                if col_name not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE learning_path ADD COLUMN {col_name} {col_type}")
                    except Exception:
                        pass
        else:
            import pymysql
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_path (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL UNIQUE,
                    path_json LONGTEXT,
                    generated_at DATETIME DEFAULT NULL,
                    reasoning TEXT DEFAULT NULL,
                    data_sources JSON DEFAULT NULL,
                    confidence FLOAT DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            # 检查并补全缺失列（MySQL）
            cursor.execute("SHOW COLUMNS FROM learning_path")
            existing_cols = {row[0] for row in cursor.fetchall()}
            col_defs = [
                ("generated_at", "DATETIME DEFAULT NULL"),
                ("reasoning", "TEXT DEFAULT NULL"),
                ("data_sources", "JSON DEFAULT NULL"),
                ("confidence", "FLOAT DEFAULT 0.0"),
            ]
            for col_name, col_type in col_defs:
                if col_name not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE learning_path ADD COLUMN {col_name} {col_type}")
                    except Exception:
                        pass
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"[_ensure_learning_path_table] 建表/补列失败: {e}")


def _create_index_mysql(cursor, index_name, table_name, column_name):
    """MySQL 兼容的索引创建（忽略已存在错误）"""
    try:
        cursor.execute(f"CREATE INDEX {index_name} ON {table_name} ({column_name})")
    except Exception as e:
        err_str = str(e).lower()
        if 'duplicate key name' in err_str or 'already exists' in err_str or err_str.startswith('1061'):
            pass  # 索引已存在，忽略
        else:
            raise


def _ensure_learning_path_nodes_table(conn):
    """自动创建 learning_path_nodes 表，用于追踪每个知识点的独立状态"""
    try:
        cursor = conn.cursor()
        if _is_sqlite(conn):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_path_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    node_id TEXT NOT NULL,
                    node_topic TEXT,
                    status TEXT DEFAULT 'locked',
                    mastery_score REAL DEFAULT 0.0,
                    rule_verified INTEGER DEFAULT 0,
                    llm_verified INTEGER DEFAULT 0,
                    completion_source TEXT,
                    interaction_count INTEGER DEFAULT 0,
                    last_quiz_score REAL,
                    last_quiz_at TEXT,
                    code_task_passed INTEGER DEFAULT 0,
                    classroom_progress_pct REAL DEFAULT 0.0,
                    evidence_json TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, node_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lpn_user ON learning_path_nodes (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_lpn_node ON learning_path_nodes (node_id)")
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_path_nodes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    node_id VARCHAR(255) NOT NULL,
                    node_topic VARCHAR(255),
                    status VARCHAR(32) DEFAULT 'locked',
                    mastery_score FLOAT DEFAULT 0.0,
                    rule_verified TINYINT DEFAULT 0,
                    llm_verified TINYINT DEFAULT 0,
                    completion_source VARCHAR(64),
                    interaction_count INT DEFAULT 0,
                    last_quiz_score FLOAT,
                    last_quiz_at DATETIME,
                    code_task_passed TINYINT DEFAULT 0,
                    classroom_progress_pct FLOAT DEFAULT 0.0,
                    evidence_json JSON,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_node (user_id, node_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            _create_index_mysql(cursor, "idx_lpn_user", "learning_path_nodes", "user_id")
            _create_index_mysql(cursor, "idx_lpn_node", "learning_path_nodes", "node_id")
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"[_ensure_learning_path_nodes_table] 建表失败: {e}")


def get_learning_path_nodes(user_id):
    """获取学生的所有知识点节点状态"""
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_learning_path_nodes_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        "SELECT * FROM learning_path_nodes WHERE user_id = ? ORDER BY updated_at DESC",
                        (user_id,)
                    )
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        "SELECT * FROM learning_path_nodes WHERE user_id = %s ORDER BY updated_at DESC",
                        (user_id,)
                    )
                rows = cursor.fetchall()
                cursor.close()
                result = []
                for row in rows:
                    node = dict(row) if _is_sqlite(conn) else row
                    if node.get('evidence_json') and isinstance(node['evidence_json'], str):
                        try:
                            node['evidence_json'] = json.loads(node['evidence_json'])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    result.append(node)
                return result
            except Exception as e:
                print(f"[get_learning_path_nodes] 查询失败: {e}")
    return []


def get_learning_path_node(user_id, node_id):
    """获取单个知识点节点状态"""
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_learning_path_nodes_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        "SELECT * FROM learning_path_nodes WHERE user_id = ? AND node_id = ?",
                        (user_id, node_id)
                    )
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        "SELECT * FROM learning_path_nodes WHERE user_id = %s AND node_id = %s",
                        (user_id, node_id)
                    )
                row = cursor.fetchone()
                cursor.close()
                if row:
                    node = dict(row) if _is_sqlite(conn) else row
                    if node.get('evidence_json') and isinstance(node['evidence_json'], str):
                        try:
                            node['evidence_json'] = json.loads(node['evidence_json'])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    return node
            except Exception as e:
                print(f"[get_learning_path_node] 查询失败: {e}")
    return None


def save_learning_path_node(user_id, node_data):
    """保存/更新单个知识点节点状态"""
    from datetime import datetime
    node_id = node_data.get('node_id')
    if not node_id:
        print("[save_learning_path_node] node_id 不能为空")
        return False

    evidence_json = None
    if node_data.get('evidence_json'):
        evidence_json = json.dumps(node_data['evidence_json'], ensure_ascii=False)

    try:
        with get_db() as conn:
            if conn is not None:
                _ensure_learning_path_nodes_table(conn)
                cursor = conn.cursor()
                updated_at = datetime.now().isoformat()
                fields = [
                    'node_topic', 'status', 'mastery_score', 'rule_verified',
                    'llm_verified', 'completion_source', 'interaction_count',
                    'last_quiz_score', 'last_quiz_at', 'code_task_passed',
                    'classroom_progress_pct', 'evidence_json', 'updated_at'
                ]
                values = [
                    node_data.get('node_topic'),
                    node_data.get('status', 'locked'),
                    node_data.get('mastery_score', 0.0),
                    1 if node_data.get('rule_verified') else 0,
                    1 if node_data.get('llm_verified') else 0,
                    node_data.get('completion_source'),
                    node_data.get('interaction_count', 0),
                    node_data.get('last_quiz_score'),
                    node_data.get('last_quiz_at'),
                    1 if node_data.get('code_task_passed') else 0,
                    node_data.get('classroom_progress_pct', 0.0),
                    evidence_json,
                    updated_at,
                ]
                if _is_sqlite(conn):
                    placeholders = ','.join(['?'] * len(values))
                    cursor.execute(f"""
                        INSERT INTO learning_path_nodes
                        (user_id, node_id, {','.join(fields)})
                        VALUES (?, ?, {placeholders})
                        ON CONFLICT(user_id, node_id) DO UPDATE SET
                            {','.join(f'{f}=excluded.{f}' for f in fields)}
                    """, [user_id, node_id] + values)
                else:
                    placeholders = ','.join(['%s'] * len(values))
                    update_set = ','.join(f'{f}=%s' for f in fields)
                    cursor.execute(f"""
                        INSERT INTO learning_path_nodes
                        (user_id, node_id, {','.join(fields)})
                        VALUES (%s, %s, {placeholders})
                        ON DUPLICATE KEY UPDATE {update_set}
                    """, [user_id, node_id] + values + values)
                conn.commit()
                cursor.close()
                return True
    except Exception as e:
        print(f"[save_learning_path_node] 保存失败: {e}")
    return False


def batch_update_learning_path_nodes(user_id, nodes_list):
    """批量更新知识点节点状态"""
    success_count = 0
    for node in nodes_list:
        node['user_id'] = user_id
        if save_learning_path_node(user_id, node):
            success_count += 1
    return success_count


def sync_path_to_nodes(user_id, path_json):
    """将学习路径同步到节点追踪表（初始化或补全缺失节点）"""
    if not isinstance(path_json, list):
        return 0

    from datetime import datetime
    updated = 0
    existing_nodes = {n['node_id']: n for n in get_learning_path_nodes(user_id)}

    def _sync_node(node, parent_id=None):
        nonlocal updated
        topic = node.get('topic') or node.get('name') or node.get('title')
        if not topic:
            return
        # 生成 node_id：如果有预定义的 id 就用，否则基于 topic 生成
        node_id = node.get('id') or node.get('node_id')
        if not node_id:
            # 基于 topic 生成 slug 作为 node_id
            import re
            slug = re.sub(r'[^\w一-鿿]+', '_', topic).strip('_').lower()
            node_id = f"topic:{slug}" if not parent_id else f"{parent_id}:{slug}"

        if node_id not in existing_nodes:
            save_learning_path_node(user_id, {
                'node_id': node_id,
                'node_topic': topic,
                'status': node.get('status', 'locked'),
                'mastery_score': 0.0,
                'updated_at': datetime.now().isoformat(),
            })
            updated += 1
        else:
            # 如果路径中的状态与节点表不一致，以节点表为准（节点表更精确）
            pass

        # 同步 children
        for child in node.get('children', []):
            child['node_id'] = child.get('node_id') or child.get('id')
            _sync_node(child, parent_id=node_id)

    for node in path_json:
        _sync_node(node)

    return updated


def get_learning_path(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_learning_path_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT * FROM learning_path WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT * FROM learning_path WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if not row:
                    return None
                result = dict(row) if _is_sqlite(conn) else row
                # 自动解析 JSON 字段
                for field in ('path_json', 'data_sources'):
                    val = result.get(field)
                    if isinstance(val, str) and val:
                        try:
                            result[field] = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            pass
                return result
            except Exception as e:
                print(f"数据库查询失败: {e}")

        return _get_json_record(load_local_storage(), 'learning_paths', user_id)


def save_learning_path(user_id, path_json, reasoning=None, data_sources=None, confidence=0.0):
    """保存学习路径，支持元数据字段（reasoning, data_sources, confidence）。"""
    from datetime import datetime
    generated_at = datetime.now().isoformat()
    data_sources_json = json.dumps(data_sources, ensure_ascii=False) if data_sources else None
    path_str = json.dumps(path_json, ensure_ascii=False) if isinstance(path_json, (list, dict)) else path_json

    try:
        with get_db() as conn:
            if conn is not None:
                try:
                    _ensure_learning_path_table(conn)
                    cursor = conn.cursor()
                    if _is_sqlite(conn):
                        cursor.execute(
                            """INSERT INTO learning_path
                               (user_id, path_json, generated_at, reasoning, data_sources, confidence)
                               VALUES (?, ?, ?, ?, ?, ?)
                               ON CONFLICT(user_id) DO UPDATE SET
                                   path_json=excluded.path_json,
                                   generated_at=excluded.generated_at,
                                   reasoning=excluded.reasoning,
                                   data_sources=excluded.data_sources,
                                   confidence=excluded.confidence""",
                            (user_id, path_str, generated_at, reasoning, data_sources_json, confidence))
                    else:
                        cursor.execute(
                            """INSERT INTO learning_path
                               (user_id, path_json, generated_at, reasoning, data_sources, confidence)
                               VALUES (%s, %s, %s, %s, %s, %s)
                               ON DUPLICATE KEY UPDATE
                                   path_json=%s,
                                   generated_at=%s,
                                   reasoning=%s,
                                   data_sources=%s,
                                   confidence=%s""",
                            (user_id, path_str, generated_at, reasoning, data_sources_json, confidence,
                             path_str, generated_at, reasoning, data_sources_json, confidence))
                    conn.commit()
                    cursor.close()
                    return
                except Exception as e:
                    err_str = str(e).lower()
                    # 如果列不存在，回退到只保存基本字段
                    if "unknown column" in err_str or "column" in err_str:
                        try:
                            # MySQL 事务失败需要先 rollback
                            if hasattr(conn, 'rollback'):
                                conn.rollback()
                            cursor2 = conn.cursor()
                            cursor2.execute(
                                """INSERT INTO learning_path (user_id, path_json)
                                   VALUES (%s, %s)
                                   ON DUPLICATE KEY UPDATE path_json=%s""",
                                (user_id, path_str, path_str))
                            conn.commit()
                            cursor2.close()
                            print(f"[save_learning_path] 列不存在，回退保存基本字段: {e}")
                            return
                        except Exception as e2:
                            print(f"[save_learning_path] 回退也失败: {e2}")
                    else:
                        print(f"[save_learning_path] 数据库保存失败: {e}")
    except Exception as outer_e:
        print(f"[save_learning_path] 外层异常: {outer_e}")

    # 数据库不可用或保存失败，回退到本地 JSON 存储
    try:
        storage = load_local_storage()
        for path in storage.get('learning_paths', []):
            if path.get('user_id') == user_id:
                path['path_json'] = path_str
                path['generated_at'] = generated_at
                path['reasoning'] = reasoning
                path['data_sources'] = data_sources
                path['confidence'] = confidence
                save_local_storage(storage)
                return
        storage['learning_paths'].append({
            'id': len(storage.get('learning_paths', [])) + 1,
            'user_id': user_id, 'path_json': path_str,
            'generated_at': generated_at, 'reasoning': reasoning,
            'data_sources': data_sources, 'confidence': confidence,
            'updated_at': 'local',
        })
        save_local_storage(storage)
    except Exception as json_e:
        print(f"[save_learning_path] JSON 回退也失败: {json_e}")


# ============================================================
# 用户长期记忆（user_memories）
# ============================================================

def _ensure_user_memories_table(conn):
    """自动创建 user_memories 表（如果不存在）。"""
    try:
        cursor = conn.cursor()
        if _is_sqlite(conn):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL DEFAULT 'fact',
                    content TEXT NOT NULL,
                    source TEXT,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TEXT,
                    access_count INTEGER DEFAULT 1,
                    confirmed INTEGER DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories (user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_memories_type ON user_memories (memory_type)")
        else:
            import pymysql
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_memories (
                    id VARCHAR(64) NOT NULL PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    memory_type VARCHAR(20) NOT NULL DEFAULT 'fact',
                    content TEXT NOT NULL,
                    source TEXT,
                    confidence FLOAT DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP NULL DEFAULT NULL,
                    access_count INT DEFAULT 1,
                    confirmed TINYINT DEFAULT 0,
                    INDEX idx_user_memories_user_id (user_id),
                    INDEX idx_user_memories_type (memory_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"[_ensure_user_memories_table] 建表失败（可能已存在）: {e}")


def save_user_memory(memory_id, user_id, memory_type, content, source=None, confidence=0.8):
    """保存单条用户记忆。数据库不可用时回退到本地 JSON。"""
    from datetime import datetime
    now = datetime.now().isoformat(sep=' ', timespec='seconds')
    db_ok = False
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_user_memories_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_memories
                           (id, user_id, memory_type, content, source, confidence, created_at, updated_at, access_count, confirmed)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0)""",
                        (memory_id, str(user_id), memory_type, content, source or 'auto', confidence, now, now))
                else:
                    cursor.execute(
                        """INSERT INTO user_memories
                           (id, user_id, memory_type, content, source, confidence, created_at, updated_at, access_count, confirmed)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, 0)""",
                        (memory_id, str(user_id), memory_type, content, source or 'auto', confidence, now, now))
                conn.commit()
                cursor.close()
                db_ok = True
            except Exception as e:
                print(f"[save_user_memory] 保存记忆失败，将回退到本地存储: {e}")
    if db_ok:
        return True
    # 本地 JSON 回退
    try:
        storage = load_local_storage()
        if 'user_memories' not in storage:
            storage['user_memories'] = []
        storage['user_memories'].append({
            'id': memory_id, 'user_id': str(user_id), 'memory_type': memory_type,
            'content': content, 'source': source or 'auto', 'confidence': confidence,
            'created_at': now, 'updated_at': now, 'last_accessed': None,
            'access_count': 1, 'confirmed': 0,
        })
        save_local_storage(storage)
        return True
    except Exception as e:
        print(f"[save_user_memory] 本地存储也失败: {e}")
        return False


def update_user_memory(memory_id, content=None, confidence=None):
    """更新已有记忆的内容和置信度。数据库不可用时回退到本地 JSON。"""
    from datetime import datetime
    now = datetime.now().isoformat(sep=' ', timespec='seconds')
    db_ok = False
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_user_memories_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    if content is not None and confidence is not None:
                        cursor.execute(
                            "UPDATE user_memories SET content=?, confidence=?, updated_at=? WHERE id=?",
                            (content, confidence, now, memory_id))
                    elif content is not None:
                        cursor.execute(
                            "UPDATE user_memories SET content=?, updated_at=? WHERE id=?",
                            (content, now, memory_id))
                    elif confidence is not None:
                        cursor.execute(
                            "UPDATE user_memories SET confidence=?, updated_at=? WHERE id=?",
                            (confidence, now, memory_id))
                else:
                    if content is not None and confidence is not None:
                        cursor.execute(
                            "UPDATE user_memories SET content=%s, confidence=%s, updated_at=%s WHERE id=%s",
                            (content, confidence, now, memory_id))
                    elif content is not None:
                        cursor.execute(
                            "UPDATE user_memories SET content=%s, updated_at=%s WHERE id=%s",
                            (content, now, memory_id))
                    elif confidence is not None:
                        cursor.execute(
                            "UPDATE user_memories SET confidence=%s, updated_at=%s WHERE id=%s",
                            (confidence, now, memory_id))
                conn.commit()
                cursor.close()
                db_ok = True
            except Exception as e:
                print(f"[update_user_memory] 更新记忆失败，将回退到本地存储: {e}")
    if db_ok:
        return True
    # 本地 JSON 回退
    try:
        storage = load_local_storage()
        if 'user_memories' not in storage:
            storage['user_memories'] = []
        for mem in storage.get('user_memories', []):
            if mem.get('id') == memory_id:
                if content is not None:
                    mem['content'] = content
                if confidence is not None:
                    mem['confidence'] = confidence
                mem['updated_at'] = now
                save_local_storage(storage)
                return True
        return False
    except Exception as e:
        print(f"[update_user_memory] 本地存储也失败: {e}")
        return False


def confirm_user_memory(memory_id, confirmed=True):
    """用户确认或否认某条记忆。数据库不可用时回退到本地 JSON。"""
    db_ok = False
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_user_memories_table(conn)
                cursor = conn.cursor()
                val = 1 if confirmed else 0
                if _is_sqlite(conn):
                    cursor.execute(
                        "UPDATE user_memories SET confirmed=? WHERE id=?",
                        (val, memory_id))
                else:
                    cursor.execute(
                        "UPDATE user_memories SET confirmed=%s WHERE id=%s",
                        (val, memory_id))
                conn.commit()
                cursor.close()
                db_ok = True
            except Exception as e:
                print(f"[confirm_user_memory] 确认记忆失败，将回退到本地存储: {e}")
    if db_ok:
        return True
    # 本地 JSON 回退
    try:
        storage = load_local_storage()
        if 'user_memories' not in storage:
            storage['user_memories'] = []
        for mem in storage.get('user_memories', []):
            if mem.get('id') == memory_id:
                mem['confirmed'] = 1 if confirmed else 0
                save_local_storage(storage)
                return True
        return False
    except Exception as e:
        print(f"[confirm_user_memory] 本地存储也失败: {e}")
        return False


def delete_user_memory(memory_id):
    """删除单条记忆。数据库不可用时回退到本地 JSON。"""
    db_ok = False
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_user_memories_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("DELETE FROM user_memories WHERE id=?", (memory_id,))
                else:
                    cursor.execute("DELETE FROM user_memories WHERE id=%s", (memory_id,))
                conn.commit()
                cursor.close()
                db_ok = True
            except Exception as e:
                print(f"[delete_user_memory] 删除记忆失败，将回退到本地存储: {e}")
    if db_ok:
        return True
    # 本地 JSON 回退
    try:
        storage = load_local_storage()
        if 'user_memories' not in storage:
            storage['user_memories'] = []
        original_len = len(storage.get('user_memories', []))
        storage['user_memories'] = [m for m in storage.get('user_memories', []) if m.get('id') != memory_id]
        save_local_storage(storage)
        return len(storage['user_memories']) < original_len
    except Exception as e:
        print(f"[delete_user_memory] 本地存储也失败: {e}")
        return False


def get_user_memories(user_id, memory_type=None, limit=100):
    """获取用户的所有记忆（或指定类型的记忆）。数据库不可用时回退到本地 JSON。"""
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_user_memories_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    if memory_type:
                        cursor.execute(
                            """SELECT id, user_id, memory_type, content, source, confidence,
                                      created_at, updated_at, last_accessed, access_count, confirmed
                               FROM user_memories WHERE user_id=? AND memory_type=?
                               ORDER BY updated_at DESC LIMIT ?""",
                            (str(user_id), memory_type, limit))
                    else:
                        cursor.execute(
                            """SELECT id, user_id, memory_type, content, source, confidence,
                                      created_at, updated_at, last_accessed, access_count, confirmed
                               FROM user_memories WHERE user_id=?
                               ORDER BY updated_at DESC LIMIT ?""",
                            (str(user_id), limit))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    if memory_type:
                        cursor.execute(
                            """SELECT id, user_id, memory_type, content, source, confidence,
                                      created_at, updated_at, last_accessed, access_count, confirmed
                               FROM user_memories WHERE user_id=%s AND memory_type=%s
                               ORDER BY updated_at DESC LIMIT %s""",
                            (str(user_id), memory_type, limit))
                    else:
                        cursor.execute(
                            """SELECT id, user_id, memory_type, content, source, confidence,
                                      created_at, updated_at, last_accessed, access_count, confirmed
                               FROM user_memories WHERE user_id=%s
                               ORDER BY updated_at DESC LIMIT %s""",
                            (str(user_id), limit))
                rows = cursor.fetchall()
                cursor.close()
                result = []
                for r in rows:
                    row = dict(r) if _is_sqlite(conn) else r
                    result.append(row)
                return result
            except Exception as e:
                print(f"[get_user_memories] 查询记忆失败，将回退到本地存储: {e}")
    # 本地 JSON 回退
    try:
        storage = load_local_storage()
        if 'user_memories' not in storage:
            storage['user_memories'] = []
        memories = storage.get('user_memories', [])
        result = [m for m in memories if m.get('user_id') == str(user_id)]
        if memory_type:
            result = [m for m in result if m.get('memory_type') == memory_type]
        # 按 updated_at 降序（简单字符串比较）
        result.sort(key=lambda x: x.get('updated_at') or '', reverse=True)
        return result[:limit]
    except Exception as e:
        print(f"[get_user_memories] 本地存储也失败: {e}")
        return []


def bump_memory_access(memory_id):
    """增加记忆的访问计数。数据库不可用时回退到本地 JSON。"""
    from datetime import datetime
    now = datetime.now().isoformat(sep=' ', timespec='seconds')
    db_ok = False
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_user_memories_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        "UPDATE user_memories SET access_count=access_count+1, last_accessed=? WHERE id=?",
                        (now, memory_id))
                else:
                    cursor.execute(
                        "UPDATE user_memories SET access_count=access_count+1, last_accessed=%s WHERE id=%s",
                        (now, memory_id))
                conn.commit()
                cursor.close()
                db_ok = True
            except Exception as e:
                print(f"[bump_memory_access] 更新访问计数失败，将回退到本地存储: {e}")
    if db_ok:
        return True
    # 本地 JSON 回退
    try:
        storage = load_local_storage()
        if 'user_memories' not in storage:
            storage['user_memories'] = []
        for mem in storage.get('user_memories', []):
            if mem.get('id') == memory_id:
                mem['access_count'] = (mem.get('access_count') or 0) + 1
                mem['last_accessed'] = now
                save_local_storage(storage)
                return True
        return False
    except Exception as e:
        print(f"[bump_memory_access] 本地存储也失败: {e}")
        return False


# ============================================================
# 学情数据查询（供学习路径生成使用）
# ============================================================

def _ensure_quiz_records_table(conn):
    """自动创建 quiz_records 表"""
    try:
        cursor = conn.cursor()
        if _is_sqlite(conn):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quiz_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    classroom_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    quiz_id TEXT DEFAULT '',
                    score REAL DEFAULT 0.0,
                    total INTEGER DEFAULT 0,
                    passed INTEGER DEFAULT 0,
                    answers TEXT,
                    feedback TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_qr_student ON quiz_records (student_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_qr_classroom ON quiz_records (classroom_id)")
        else:
            import pymysql
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quiz_records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    classroom_id VARCHAR(64) NOT NULL,
                    student_id VARCHAR(64) NOT NULL,
                    quiz_id VARCHAR(64) NOT NULL DEFAULT '',
                    score FLOAT DEFAULT 0.0,
                    total INT DEFAULT 0,
                    passed TINYINT DEFAULT 0,
                    answers JSON DEFAULT NULL,
                    feedback JSON DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_qr_student (student_id),
                    INDEX idx_qr_classroom (classroom_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"[_ensure_quiz_records_table] 建表失败（可能已存在）: {e}")


def _ensure_classroom_sessions_table(conn):
    """自动创建 classroom_sessions 表"""
    try:
        cursor = conn.cursor()
        if _is_sqlite(conn):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS classroom_sessions (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    course_id TEXT DEFAULT '',
                    course_data TEXT,
                    current_scene_index INTEGER DEFAULT 0,
                    visited_scenes TEXT,
                    quiz_answers TEXT,
                    chat_history TEXT,
                    time_spent INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    teacher_persona TEXT DEFAULT 'expert_mentor',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cs_student ON classroom_sessions (student_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cs_updated ON classroom_sessions (updated_at)")
        else:
            import pymysql
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS classroom_sessions (
                    id VARCHAR(64) NOT NULL PRIMARY KEY,
                    student_id VARCHAR(64) NOT NULL,
                    course_id VARCHAR(64) NOT NULL DEFAULT '',
                    course_data JSON DEFAULT NULL,
                    current_scene_index INT DEFAULT 0,
                    visited_scenes JSON DEFAULT NULL,
                    quiz_answers JSON DEFAULT NULL,
                    chat_history JSON DEFAULT NULL,
                    time_spent INT DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'active',
                    teacher_persona VARCHAR(32) NOT NULL DEFAULT 'expert_mentor',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_cs_student (student_id),
                    INDEX idx_cs_updated (updated_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"[_ensure_classroom_sessions_table] 建表失败（可能已存在）: {e}")


def get_recent_quizzes(user_id, limit=20):
    """获取学生最近 N 条测验记录。"""
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_quiz_records_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """SELECT quiz_id, score, total, passed, answers, feedback, created_at
                           FROM quiz_records WHERE student_id = ?
                           ORDER BY created_at DESC LIMIT ?""",
                        (user_id, limit))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        """SELECT quiz_id, score, total, passed, answers, feedback, created_at
                           FROM quiz_records WHERE student_id = %s
                           ORDER BY created_at DESC LIMIT %s""",
                        (user_id, limit))
                rows = cursor.fetchall()
                cursor.close()
                return [dict(r) if _is_sqlite(conn) else r for r in rows] if rows else []
            except Exception as e:
                err = str(e).lower()
                if "doesn't exist" in err or "doesn" in err:
                    return []  # 表不存在时静默返回空列表
                print(f"查询 quiz_records 失败: {e}")
    return []


def get_recent_classrooms(user_id, limit=10):
    """获取学生最近 N 次课堂会话记录。"""
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_classroom_sessions_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """SELECT id, course_id, current_scene_index, visited_scenes,
                                  quiz_answers, time_spent, status, teacher_persona, created_at, updated_at
                           FROM classroom_sessions WHERE student_id = ?
                           ORDER BY updated_at DESC LIMIT ?""",
                        (user_id, limit))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        """SELECT id, course_id, current_scene_index, visited_scenes,
                                  quiz_answers, time_spent, status, teacher_persona, created_at, updated_at
                           FROM classroom_sessions WHERE student_id = %s
                           ORDER BY updated_at DESC LIMIT %s""",
                        (user_id, limit))
                rows = cursor.fetchall()
                cursor.close()
                result = []
                for r in rows:
                    row = dict(r) if _is_sqlite(conn) else r
                    # 解析 JSON 字段
                    for field in ('visited_scenes', 'quiz_answers'):
                        val = row.get(field)
                        if isinstance(val, str) and val:
                            try:
                                row[field] = json.loads(val)
                            except (json.JSONDecodeError, TypeError):
                                pass
                    result.append(row)
                return result
            except Exception as e:
                err = str(e).lower()
                if "doesn't exist" in err or "doesn" in err:
                    return []  # 表不存在时静默返回空列表
                print(f"查询 classroom_sessions 失败: {e}")
    return []


def get_recent_messages_summary(user_id, limit=30):
    """获取学生最近 N 条消息，用于提取近期学习主题。"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """SELECT role, content, message_type, metadata, created_at
                           FROM messages WHERE student_id = ?
                           ORDER BY created_at DESC LIMIT ?""",
                        (user_id, limit))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        """SELECT role, content, message_type, metadata, created_at
                           FROM messages WHERE student_id = %s
                           ORDER BY created_at DESC LIMIT %s""",
                        (user_id, limit))
                rows = cursor.fetchall()
                cursor.close()
                result = []
                for r in rows:
                    row = dict(r) if _is_sqlite(conn) else r
                    for field in ('metadata',):
                        val = row.get(field)
                        if isinstance(val, str) and val:
                            try:
                                row[field] = json.loads(val)
                            except (json.JSONDecodeError, TypeError):
                                pass
                    result.append(row)
                return result
            except Exception as e:
                print(f"查询 messages 失败: {e}")
    return []


def get_conversation_summary(user_id):
    """获取学生的会话摘要（最近3条）。"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """SELECT session_id, summary_text, key_facts, message_count, last_message_at
                           FROM conversation_summaries WHERE student_id = ?
                           ORDER BY last_message_at DESC LIMIT 3""",
                        (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        """SELECT session_id, summary_text, key_facts, message_count, last_message_at
                           FROM conversation_summaries WHERE student_id = %s
                           ORDER BY last_message_at DESC LIMIT 3""",
                        (user_id,))
                rows = cursor.fetchall()
                cursor.close()
                result = []
                for r in rows:
                    row = dict(r) if _is_sqlite(conn) else r
                    for field in ('key_facts',):
                        val = row.get(field)
                        if isinstance(val, str) and val:
                            try:
                                row[field] = json.loads(val)
                            except (json.JSONDecodeError, TypeError):
                                pass
                    result.append(row)
                return result
            except Exception as e:
                print(f"查询 conversation_summaries 失败: {e}")
    return []


# ============================================================
# 消息存储与对话历史（记忆系统）
# ============================================================

def _ensure_messages_table(conn):
    """自动创建 messages 和 conversation_summaries 表（如果不存在）。"""
    try:
        cursor = conn.cursor()
        if _is_sqlite(conn):
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    message_type TEXT NOT NULL DEFAULT 'text',
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_time ON messages (session_id, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_student_time ON messages (student_id, created_at)")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    session_id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    summary_text TEXT NOT NULL DEFAULT '',
                    key_facts TEXT,
                    message_count INTEGER NOT NULL DEFAULT 0,
                    last_message_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            import pymysql
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id VARCHAR(64) NOT NULL PRIMARY KEY,
                    session_id VARCHAR(64) NOT NULL,
                    student_id VARCHAR(64) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content LONGTEXT NOT NULL,
                    message_type VARCHAR(20) NOT NULL DEFAULT 'text',
                    metadata LONGTEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP NULL DEFAULT NULL,
                    INDEX idx_messages_session_time (session_id, created_at),
                    INDEX idx_messages_student_time (student_id, created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    session_id VARCHAR(64) NOT NULL PRIMARY KEY,
                    student_id VARCHAR(64) NOT NULL,
                    summary_text LONGTEXT NOT NULL,
                    key_facts LONGTEXT,
                    message_count INT NOT NULL DEFAULT 0,
                    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_conversation_summaries_student_id (student_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"[_ensure_messages_table] 建表失败（可能已存在）: {e}")


def save_message(session_id, student_id, role, content, message_type="text", metadata=None):
    """保存单条消息到 messages 表。
    
    Args:
        session_id: 会话ID（如页面标签ID）
        student_id: 学生ID
        role: user | assistant | system
        content: 消息内容
        message_type: text | action | link | image | tool_call
        metadata: 扩展元数据字典
    """
    import uuid
    msg_id = f"msg_{uuid.uuid4().hex[:16]}"
    meta_str = json.dumps(metadata, ensure_ascii=False) if metadata else None
    now = datetime.now().isoformat(sep=' ', timespec='seconds')
    
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_messages_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO messages (id, session_id, student_id, role, content, message_type, metadata, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (msg_id, str(session_id), str(student_id), role, content, message_type, meta_str, now))
                else:
                    cursor.execute(
                        """INSERT INTO messages (id, session_id, student_id, role, content, message_type, metadata, created_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (msg_id, str(session_id), str(student_id), role, content, message_type, meta_str, now))
                conn.commit()
                cursor.close()
                return msg_id
            except Exception as e:
                print(f"保存消息失败: {e}")
    return None


def get_conversation_messages(session_id, student_id=None, limit=20, before_id=None):
    """获取指定会话的历史消息（按时间正序，用于构建LLM上下文）。
    
    Returns:
        list[dict]: [{role, content, created_at}, ...]
    """
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_messages_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    if student_id:
                        cursor.execute(
                            """SELECT role, content, message_type, metadata, created_at
                               FROM messages 
                               WHERE session_id = ? AND student_id = ? AND deleted_at IS NULL
                               ORDER BY created_at DESC LIMIT ?""",
                            (str(session_id), str(student_id), limit))
                    else:
                        cursor.execute(
                            """SELECT role, content, message_type, metadata, created_at
                               FROM messages 
                               WHERE session_id = ? AND deleted_at IS NULL
                               ORDER BY created_at DESC LIMIT ?""",
                            (str(session_id), limit))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    if student_id:
                        cursor.execute(
                            """SELECT role, content, message_type, metadata, created_at
                               FROM messages 
                               WHERE session_id = %s AND student_id = %s AND deleted_at IS NULL
                               ORDER BY created_at DESC LIMIT %s""",
                            (str(session_id), str(student_id), limit))
                    else:
                        cursor.execute(
                            """SELECT role, content, message_type, metadata, created_at
                               FROM messages 
                               WHERE session_id = %s AND deleted_at IS NULL
                               ORDER BY created_at DESC LIMIT %s""",
                            (str(session_id), limit))
                rows = cursor.fetchall()
                cursor.close()
                result = []
                for r in rows:
                    row = dict(r) if _is_sqlite(conn) else r
                    for field in ('metadata',):
                        val = row.get(field)
                        if isinstance(val, str) and val:
                            try:
                                row[field] = json.loads(val)
                            except (json.JSONDecodeError, TypeError):
                                pass
                    result.append(row)
                # 转为正序（旧→新），适合构建LLM messages 数组
                result.reverse()
                return result
            except Exception as e:
                print(f"查询对话历史失败: {e}")
    return []


# ============================================================
# 用户画像
# ============================================================

def save_user_profile(user_id, profile_json, evaluation_json, last_grade_record=None):
    grade_str = json.dumps(last_grade_record, ensure_ascii=False) if last_grade_record else None
    profile_str = json.dumps(profile_json, ensure_ascii=False) if isinstance(profile_json, dict) else profile_json
    eval_str = json.dumps(evaluation_json, ensure_ascii=False) if isinstance(evaluation_json, dict) else evaluation_json
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_profile (user_id, profile_json, evaluation_json, last_grade_record)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET
                               profile_json=excluded.profile_json,
                               evaluation_json=excluded.evaluation_json,
                               last_grade_record=excluded.last_grade_record""",
                        (user_id, profile_str, eval_str, grade_str))
                else:
                    cursor.execute(
                        """INSERT INTO user_profile (user_id, profile_json, evaluation_json, last_grade_record)
                           VALUES (%s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                               profile_json=%s, evaluation_json=%s, last_grade_record=%s""",
                        (user_id, profile_str, eval_str, grade_str,
                         profile_str, eval_str, grade_str))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for profile in storage.get('user_profiles', []):
            if profile.get('user_id') == user_id:
                profile['profile_json'] = profile_json
                profile['evaluation_json'] = evaluation_json
                if last_grade_record:
                    profile['last_grade_record'] = last_grade_record
                save_local_storage(storage)
                return
        storage['user_profiles'].append({
            'id': len(storage.get('user_profiles', [])) + 1,
            'user_id': user_id, 'profile_json': profile_json,
            'evaluation_json': evaluation_json, 'last_grade_record': last_grade_record,
            'updated_at': 'local',
        })
        save_local_storage(storage)


def get_user_profile(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT * FROM user_profile WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT * FROM user_profile WHERE user_id = %s", (user_id,))
                profile = cursor.fetchone()
                cursor.close()
                if profile:
                    if not isinstance(profile, dict):
                        profile = dict(profile)
                    for field in ('profile_json', 'evaluation_json', 'last_grade_record'):
                        val = profile.get(field)
                        if isinstance(val, str) and val:
                            try:
                                profile[field] = json.loads(val)
                            except (json.JSONDecodeError, TypeError):
                                pass
                return profile
            except Exception as e:
                print(f"数据库查询失败: {e}")

        return _get_json_record(load_local_storage(), 'user_profiles', user_id)


# ============================================================
# 学生画像（6维度）
# ============================================================

def get_student_portrait(user_id: int) -> dict | None:
    """获取学生的6维画像，从 user_profile.profile_json.learning_portrait 读取"""
    profile = get_user_profile(user_id)
    if not profile:
        return None
    profile_json = profile.get('profile_json', {})
    if isinstance(profile_json, str):
        try:
            profile_json = json.loads(profile_json)
        except (json.JSONDecodeError, TypeError):
            return None
    portrait = profile_json.get('learning_portrait')
    if portrait:
        return portrait
    return None


def save_student_portrait(user_id: int, portrait: dict) -> bool:
    """保存学生的6维画像到 user_profile.profile_json.learning_portrait"""
    from datetime import datetime
    portrait['last_synced'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    profile = get_user_profile(user_id)
    if profile:
        profile_json = profile.get('profile_json', {})
        if isinstance(profile_json, str):
            try:
                profile_json = json.loads(profile_json)
            except (json.JSONDecodeError, TypeError):
                profile_json = {}
    else:
        profile_json = {}

    profile_json['learning_portrait'] = portrait

    evaluation_json = profile.get('evaluation_json', {})
    if isinstance(evaluation_json, str):
        try:
            evaluation_json = json.loads(evaluation_json)
        except (json.JSONDecodeError, TypeError):
            evaluation_json = {}

    save_user_profile(user_id, profile_json, evaluation_json)
    return True


# ============================================================
# 用户评估指标持久化
# ============================================================

def save_user_evaluation(user_id, evaluation_data):
    """保存用户每日评估指标到 user_evaluations 表，同一天只保留一条记录（增量合并更新）。"""
    from datetime import date
    record_date = date.today().isoformat()

    def _get(d, key, default=None):
        return d.get(key, default) if isinstance(d, dict) else default

    new_interaction_count = _get(evaluation_data, 'interactionCount')
    new_socratic_pass_rate = _get(evaluation_data, 'socraticPassRate')
    new_difficulty_level = _get(evaluation_data, 'difficultyLevel')
    new_code_practice_time = _get(evaluation_data, 'codePracticeTime')
    new_focus_time_today = _get(evaluation_data, 'focusTimeToday')
    new_flashcards_studied = _get(evaluation_data, 'flashcardsStudied')
    new_streak_days = _get(evaluation_data, 'streakDays')
    new_eval_json = json.dumps(evaluation_data, ensure_ascii=False) if isinstance(evaluation_data, dict) else str(evaluation_data)

    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_user_evaluations_table(conn)
                cursor = conn.cursor()
                # 先读取现有值，None 字段保持原值
                if _is_sqlite(conn):
                    cursor.execute(
                        "SELECT * FROM user_evaluations WHERE user_id = ? AND record_date = ?",
                        (user_id, record_date),
                    )
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        "SELECT * FROM user_evaluations WHERE user_id = %s AND record_date = %s",
                        (user_id, record_date),
                    )
                existing = cursor.fetchone()
                if existing:
                    existing = dict(existing) if _is_sqlite(conn) else existing
                else:
                    existing = {}

                def _merge(key, new_val, default=0):
                    return new_val if new_val is not None else existing.get(key, default)

                interaction_count = _merge('interaction_count', new_interaction_count, 0)
                socratic_pass_rate = _merge('socratic_pass_rate', new_socratic_pass_rate, 0.0)
                difficulty_level = _merge('difficulty_level', new_difficulty_level, 'basic')
                code_practice_time = _merge('code_practice_time', new_code_practice_time, 0)
                focus_time_today = _merge('focus_time_today', new_focus_time_today, 0)
                flashcards_studied = _merge('flashcards_studied', new_flashcards_studied, 0)
                streak_days = _merge('streak_days', new_streak_days, 0)
                eval_json = new_eval_json if evaluation_data else existing.get('eval_json')

                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_evaluations
                           (user_id, interaction_count, socratic_pass_rate, difficulty_level,
                            code_practice_time, focus_time_today, flashcards_studied, streak_days,
                            eval_json, record_date)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(user_id, record_date) DO UPDATE SET
                               interaction_count=excluded.interaction_count,
                               socratic_pass_rate=excluded.socratic_pass_rate,
                               difficulty_level=excluded.difficulty_level,
                               code_practice_time=excluded.code_practice_time,
                               focus_time_today=excluded.focus_time_today,
                               flashcards_studied=excluded.flashcards_studied,
                               streak_days=excluded.streak_days,
                               eval_json=excluded.eval_json""",
                        (user_id, interaction_count, socratic_pass_rate, difficulty_level,
                         code_practice_time, focus_time_today, flashcards_studied, streak_days,
                         eval_json, record_date))
                else:
                    cursor.execute(
                        """INSERT INTO user_evaluations
                           (user_id, interaction_count, socratic_pass_rate, difficulty_level,
                            code_practice_time, focus_time_today, flashcards_studied, streak_days,
                            eval_json, record_date)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                               interaction_count=%s,
                               socratic_pass_rate=%s,
                               difficulty_level=%s,
                               code_practice_time=%s,
                               focus_time_today=%s,
                               flashcards_studied=%s,
                               streak_days=%s,
                               eval_json=%s""",
                        (user_id, interaction_count, socratic_pass_rate, difficulty_level,
                         code_practice_time, focus_time_today, flashcards_studied, streak_days,
                         eval_json, record_date,
                         interaction_count, socratic_pass_rate, difficulty_level,
                         code_practice_time, focus_time_today, flashcards_studied, streak_days,
                         eval_json))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"保存 user_evaluations 失败: {e}")
                return False
    return False


def get_user_evaluation_history(user_id, days=7):
    """获取用户最近 N 天的评估指标历史。"""
    with get_db() as conn:
        if conn is not None:
            try:
                _ensure_user_evaluations_table(conn)
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """SELECT interaction_count, socratic_pass_rate, difficulty_level,
                                  code_practice_time, focus_time_today, flashcards_studied,
                                  streak_days, eval_json, record_date
                           FROM user_evaluations
                           WHERE user_id = ?
                           ORDER BY record_date DESC
                           LIMIT ?""",
                        (user_id, days))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        """SELECT interaction_count, socratic_pass_rate, difficulty_level,
                                  code_practice_time, focus_time_today, flashcards_studied,
                                  streak_days, eval_json, record_date
                           FROM user_evaluations
                           WHERE user_id = %s
                           ORDER BY record_date DESC
                           LIMIT %s""",
                        (user_id, days))
                rows = cursor.fetchall()
                cursor.close()
                return rows if rows else []
            except Exception as e:
                print(f"查询 user_evaluations 失败: {e}")
                return []
    return []


# ============================================================
# 用户偏好设置
# ============================================================

def get_user_preferences(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT preferences_json FROM user_preferences WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT preferences_json FROM user_preferences WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    val = row['preferences_json'] if isinstance(row, dict) else row[0]
                    if isinstance(val, str):
                        try:
                            return json.loads(val)
                        except Exception:
                            return {}
                    return val or {}
            except Exception as e:
                print(f"数据库查询失败: {e}")

        storage = load_local_storage()
        return storage.get('user_preferences', {}).get(str(user_id), {})


def save_user_preferences(user_id, preferences):
    prefs_json = json.dumps(preferences, ensure_ascii=False)
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_preferences (user_id, preferences_json) VALUES (?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET preferences_json=excluded.preferences_json""",
                        (user_id, prefs_json))
                else:
                    cursor.execute(
                        """INSERT INTO user_preferences (user_id, preferences_json) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE preferences_json=%s""",
                        (user_id, prefs_json, prefs_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        storage['user_preferences'] = storage.get('user_preferences', {})
        storage['user_preferences'][str(user_id)] = preferences
        save_local_storage(storage)


# ============================================================
# 花园 / 植物
# ============================================================

def get_user_garden(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT seeds, garden_json FROM user_garden WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT seeds, garden_json FROM user_garden WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    if isinstance(row, dict):
                        result = {'seeds': row.get('seeds', 0), 'garden_json': row.get('garden_json', '{}')}
                    else:
                        result = {'seeds': row[0], 'garden_json': row[1] if row[1] else '{}'}
                    if isinstance(result['garden_json'], str):
                        try:
                            result['garden_data'] = json.loads(result['garden_json'])
                        except Exception:
                            result['garden_data'] = {}
                    return result
            except Exception as e:
                print(f"数据库查询失败: {e}")

        return _get_json_record(load_local_storage(), 'user_gardens', user_id)


def save_user_garden(user_id, seeds, garden_data):
    garden_json = json.dumps(garden_data, ensure_ascii=False) if isinstance(garden_data, dict) else garden_data
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_garden (user_id, seeds, garden_json) VALUES (?, ?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET
                               seeds=excluded.seeds, garden_json=excluded.garden_json""",
                        (user_id, seeds, garden_json))
                else:
                    cursor.execute(
                        """INSERT INTO user_garden (user_id, seeds, garden_json) VALUES (%s, %s, %s)
                           ON DUPLICATE KEY UPDATE seeds=%s, garden_json=%s""",
                        (user_id, seeds, garden_json, seeds, garden_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for g in storage.get('user_gardens', []):
            if g.get('user_id') == user_id:
                g['seeds'] = seeds
                g['garden_json'] = garden_json
                save_local_storage(storage)
                return
        storage['user_gardens'].append({
            'id': len(storage.get('user_gardens', [])) + 1,
            'user_id': user_id, 'seeds': seeds, 'garden_json': garden_json,
        })
        save_local_storage(storage)


# ============================================================
# 宠物
# ============================================================

def get_user_pet(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT pet_json, pet_game_json FROM user_pet WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT pet_json, pet_game_json FROM user_pet WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    if isinstance(row, dict):
                        pet_json = row.get('pet_json', '{}')
                        game_json = row.get('pet_game_json', '{}')
                    else:
                        pet_json = row[0] if row[0] else '{}'
                        game_json = row[1] if row[1] else '{}'
                    return {
                        'pet': json.loads(pet_json) if isinstance(pet_json, str) else pet_json,
                        'pet_game': json.loads(game_json) if isinstance(game_json, str) else game_json,
                    }
            except Exception as e:
                print(f"数据库查询失败: {e}")

        return _get_json_record(load_local_storage(), 'user_pets', user_id)


def save_user_pet(user_id, pet_data=None, pet_game_data=None):
    pet_json = json.dumps(pet_data, ensure_ascii=False) if isinstance(pet_data, dict) else (pet_data or '{}')
    game_json = json.dumps(pet_game_data, ensure_ascii=False) if isinstance(pet_game_data, dict) else (pet_game_data or '{}')
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_pet (user_id, pet_json, pet_game_json) VALUES (?, ?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET
                               pet_json=excluded.pet_json, pet_game_json=excluded.pet_game_json""",
                        (user_id, pet_json, game_json))
                else:
                    cursor.execute(
                        """INSERT INTO user_pet (user_id, pet_json, pet_game_json) VALUES (%s, %s, %s)
                           ON DUPLICATE KEY UPDATE pet_json=%s, pet_game_json=%s""",
                        (user_id, pet_json, game_json, pet_json, game_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for p in storage.get('user_pets', []):
            if p.get('user_id') == user_id:
                if pet_data is not None:
                    p['pet_json'] = pet_json
                if pet_game_data is not None:
                    p['pet_game_json'] = game_json
                save_local_storage(storage)
                return
        storage['user_pets'].append({
            'id': len(storage.get('user_pets', [])) + 1,
            'user_id': user_id, 'pet_json': pet_json, 'pet_game_json': game_json,
        })
        save_local_storage(storage)


# ============================================================
# 成就
# ============================================================

def get_user_achievements(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT achievements_json FROM user_achievements WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT achievements_json FROM user_achievements WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    val = row['achievements_json'] if isinstance(row, dict) else row[0]
                    return json.loads(val) if isinstance(val, str) else val
            except Exception as e:
                print(f"数据库查询失败: {e}")

        record = _get_json_record(load_local_storage(), 'user_achievements', user_id)
        return record.get('achievements_json', {}) if record else {}


def save_user_achievements(user_id, achievements_data):
    achievements_json = json.dumps(achievements_data, ensure_ascii=False) if isinstance(achievements_data, dict) else achievements_data
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_achievements (user_id, achievements_json) VALUES (?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET achievements_json=excluded.achievements_json""",
                        (user_id, achievements_json))
                else:
                    cursor.execute(
                        """INSERT INTO user_achievements (user_id, achievements_json) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE achievements_json=%s""",
                        (user_id, achievements_json, achievements_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for a in storage.get('user_achievements', []):
            if a.get('user_id') == user_id:
                a['achievements_json'] = achievements_json
                save_local_storage(storage)
                return
        storage['user_achievements'].append({
            'id': len(storage.get('user_achievements', [])) + 1,
            'user_id': user_id, 'achievements_json': achievements_json,
        })
        save_local_storage(storage)


# ============================================================
# 统计数据
# ============================================================

def get_user_stats(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT stats_json FROM user_stats WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT stats_json FROM user_stats WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    val = row['stats_json'] if isinstance(row, dict) else row[0]
                    return json.loads(val) if isinstance(val, str) else val
            except Exception as e:
                print(f"数据库查询失败: {e}")

        record = _get_json_record(load_local_storage(), 'user_stats', user_id)
        return record.get('stats_json', {}) if record else {}


def save_user_stats(user_id, stats_data):
    stats_json = json.dumps(stats_data, ensure_ascii=False)
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_stats (user_id, stats_json) VALUES (?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET stats_json=excluded.stats_json""",
                        (user_id, stats_json))
                else:
                    cursor.execute(
                        """INSERT INTO user_stats (user_id, stats_json) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE stats_json=%s""",
                        (user_id, stats_json, stats_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for s in storage.get('user_stats', []):
            if s.get('user_id') == user_id:
                s['stats_json'] = stats_json
                save_local_storage(storage)
                return
        storage['user_stats'].append({
            'id': len(storage.get('user_stats', [])) + 1,
            'user_id': user_id, 'stats_json': stats_json,
        })
        save_local_storage(storage)


# ============================================================
# 通知
# ============================================================

def get_user_notifications(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT notifications_json, last_update_time FROM user_notifications WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT notifications_json, last_update_time FROM user_notifications WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    if isinstance(row, dict):
                        notif_json = row.get('notifications_json', '[]')
                        last_update = row.get('last_update_time', 0)
                    else:
                        notif_json = row[0] if row[0] else '[]'
                        last_update = row[1] if row[1] else 0
                    return {
                        'notifications': json.loads(notif_json) if isinstance(notif_json, str) else notif_json,
                        'last_update_time': last_update,
                    }
            except Exception as e:
                print(f"数据库查询失败: {e}")

        record = _get_json_record(load_local_storage(), 'user_notifications', user_id)
        if record:
            return {
                'notifications': record.get('notifications_json', []),
                'last_update_time': record.get('last_update_time', 0),
            }
        return {'notifications': [], 'last_update_time': 0}


def save_user_notifications(user_id, notifications_data, last_update_time=None):
    notif_json = json.dumps(notifications_data, ensure_ascii=False) if not isinstance(notifications_data, str) else notifications_data
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                now_ms = int(datetime.now().timestamp() * 1000) if last_update_time is None else last_update_time
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_notifications (user_id, notifications_json, last_update_time)
                           VALUES (?, ?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET
                               notifications_json=excluded.notifications_json,
                               last_update_time=excluded.last_update_time""",
                        (user_id, notif_json, now_ms))
                else:
                    cursor.execute(
                        """INSERT INTO user_notifications (user_id, notifications_json, last_update_time)
                           VALUES (%s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                               notifications_json=%s, last_update_time=%s""",
                        (user_id, notif_json, now_ms, notif_json, now_ms))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for n in storage.get('user_notifications', []):
            if n.get('user_id') == user_id:
                n['notifications_json'] = notif_json
                if last_update_time is not None:
                    n['last_update_time'] = last_update_time
                save_local_storage(storage)
                return
        storage['user_notifications'].append({
            'id': len(storage.get('user_notifications', [])) + 1,
            'user_id': user_id, 'notifications_json': notif_json,
            'last_update_time': last_update_time or int(datetime.now().timestamp() * 1000),
        })
        save_local_storage(storage)


# ============================================================
# 综合设置
# ============================================================

def get_user_settings(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        "SELECT settings_json, weather_city, floating_alarm_x, floating_alarm_y, hub_theme FROM user_settings WHERE user_id = ?",
                        (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        "SELECT settings_json, weather_city, floating_alarm_x, floating_alarm_y, hub_theme FROM user_settings WHERE user_id = %s",
                        (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    if isinstance(row, dict):
                        return {
                            'settings': json.loads(row.get('settings_json', '{}')) if isinstance(row.get('settings_json', ''), str) else row.get('settings_json', {}),
                            'weather_city': row.get('weather_city', ''),
                            'floating_alarm_x': row.get('floating_alarm_x'),
                            'floating_alarm_y': row.get('floating_alarm_y'),
                            'hub_theme': row.get('hub_theme', ''),
                        }
                    else:
                        return {
                            'settings': json.loads(row[0]) if row[0] else {},
                            'weather_city': row[1] if row[1] else '',
                            'floating_alarm_x': row[2],
                            'floating_alarm_y': row[3],
                            'hub_theme': row[4] if row[4] else '',
                        }
            except Exception as e:
                print(f"数据库查询失败: {e}")

        record = _get_json_record(load_local_storage(), 'user_settings', user_id)
        if record:
            return {
                'settings': record.get('settings_json', {}),
                'weather_city': record.get('weather_city', ''),
                'floating_alarm_x': record.get('floating_alarm_x'),
                'floating_alarm_y': record.get('floating_alarm_y'),
                'hub_theme': record.get('hub_theme', ''),
            }
        return {'settings': {}, 'weather_city': '', 'floating_alarm_x': None, 'floating_alarm_y': None, 'hub_theme': ''}


def save_user_settings(user_id, settings_data=None, weather_city=None,
                       floating_alarm_x=None, floating_alarm_y=None, hub_theme=None):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    # 先查是否存在
                    cursor.execute("SELECT id FROM user_settings WHERE user_id = ?", (user_id,))
                    existing = cursor.fetchone()
                    if existing:
                        updates = []
                        params = []
                        if settings_data is not None:
                            updates.append("settings_json = ?")
                            params.append(json.dumps(settings_data, ensure_ascii=False))
                        if weather_city is not None:
                            updates.append("weather_city = ?")
                            params.append(weather_city)
                        if floating_alarm_x is not None:
                            updates.append("floating_alarm_x = ?")
                            params.append(floating_alarm_x)
                        if floating_alarm_y is not None:
                            updates.append("floating_alarm_y = ?")
                            params.append(floating_alarm_y)
                        if hub_theme is not None:
                            updates.append("hub_theme = ?")
                            params.append(hub_theme)
                        if updates:
                            params.append(user_id)
                            cursor.execute(f"UPDATE user_settings SET {', '.join(updates)} WHERE user_id = ?", params)
                    else:
                        sj = json.dumps(settings_data, ensure_ascii=False) if settings_data is not None else '{}'
                        cursor.execute(
                            "INSERT INTO user_settings (user_id, settings_json, weather_city, floating_alarm_x, floating_alarm_y, hub_theme) VALUES (?, ?, ?, ?, ?, ?)",
                            (user_id, sj, weather_city or '', floating_alarm_x, floating_alarm_y, hub_theme or ''))
                else:
                    sj = json.dumps(settings_data, ensure_ascii=False) if settings_data is not None else '{}'
                    wc = weather_city or ''
                    ht = hub_theme or ''
                    cursor.execute(
                        """INSERT INTO user_settings (user_id, settings_json, weather_city, floating_alarm_x, floating_alarm_y, hub_theme)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                               settings_json=VALUES(settings_json), weather_city=VALUES(weather_city),
                               floating_alarm_x=VALUES(floating_alarm_x), floating_alarm_y=VALUES(floating_alarm_y),
                               hub_theme=VALUES(hub_theme)""",
                        (user_id, sj, wc, floating_alarm_x, floating_alarm_y, ht))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for s in storage.get('user_settings', []):
            if s.get('user_id') == user_id:
                if settings_data is not None:
                    s['settings_json'] = settings_data
                if weather_city is not None:
                    s['weather_city'] = weather_city
                if floating_alarm_x is not None:
                    s['floating_alarm_x'] = floating_alarm_x
                if floating_alarm_y is not None:
                    s['floating_alarm_y'] = floating_alarm_y
                if hub_theme is not None:
                    s['hub_theme'] = hub_theme
                save_local_storage(storage)
                return
        storage['user_settings'].append({
            'id': len(storage.get('user_settings', [])) + 1,
            'user_id': user_id,
            'settings_json': settings_data or {},
            'weather_city': weather_city or '',
            'floating_alarm_x': floating_alarm_x,
            'floating_alarm_y': floating_alarm_y,
            'hub_theme': hub_theme or '',
        })
        save_local_storage(storage)


# ============================================================
# 编程状态
# ============================================================

def get_user_coding_state(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT coding_state_json FROM user_coding_state WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT coding_state_json FROM user_coding_state WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    val = row['coding_state_json'] if isinstance(row, dict) else row[0]
                    return json.loads(val) if isinstance(val, str) and val else val
            except Exception as e:
                print(f"数据库查询失败: {e}")

        record = _get_json_record(load_local_storage(), 'user_coding_states', user_id)
        return record.get('coding_state_json', {}) if record else None


def save_user_coding_state(user_id, coding_state_data):
    cs_json = json.dumps(coding_state_data, ensure_ascii=False) if not isinstance(coding_state_data, str) else coding_state_data
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_coding_state (user_id, coding_state_json) VALUES (?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET coding_state_json=excluded.coding_state_json""",
                        (user_id, cs_json))
                else:
                    cursor.execute(
                        """INSERT INTO user_coding_state (user_id, coding_state_json) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE coding_state_json=%s""",
                        (user_id, cs_json, cs_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for c in storage.get('user_coding_states', []):
            if c.get('user_id') == user_id:
                c['coding_state_json'] = cs_json
                save_local_storage(storage)
                return
        storage['user_coding_states'].append({
            'id': len(storage.get('user_coding_states', [])) + 1,
            'user_id': user_id, 'coding_state_json': cs_json,
        })
        save_local_storage(storage)


# ============================================================
# 天气缓存
# ============================================================

def get_user_weather_cache(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT weather_json FROM user_weather_cache WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT weather_json FROM user_weather_cache WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    val = row['weather_json'] if isinstance(row, dict) else row[0]
                    return json.loads(val) if isinstance(val, str) else val
            except Exception as e:
                print(f"数据库查询失败: {e}")

        record = _get_json_record(load_local_storage(), 'user_weather_caches', user_id)
        return record.get('weather_json', {}) if record else None


def save_user_weather_cache(user_id, weather_data):
    weather_json = json.dumps(weather_data, ensure_ascii=False) if not isinstance(weather_data, str) else weather_data
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_weather_cache (user_id, weather_json) VALUES (?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET weather_json=excluded.weather_json""",
                        (user_id, weather_json))
                else:
                    cursor.execute(
                        """INSERT INTO user_weather_cache (user_id, weather_json) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE weather_json=%s""",
                        (user_id, weather_json, weather_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for w in storage.get('user_weather_caches', []):
            if w.get('user_id') == user_id:
                w['weather_json'] = weather_json
                save_local_storage(storage)
                return
        storage['user_weather_caches'].append({
            'id': len(storage.get('user_weather_caches', [])) + 1,
            'user_id': user_id, 'weather_json': weather_json,
        })
        save_local_storage(storage)


def delete_user_weather_cache(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("DELETE FROM user_weather_cache WHERE user_id = ?", (user_id,))
                else:
                    cursor.execute("DELETE FROM user_weather_cache WHERE user_id = %s", (user_id,))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库删除失败: {e}")

        storage = load_local_storage()
        storage['user_weather_caches'] = [w for w in storage.get('user_weather_caches', []) if w.get('user_id') != user_id]
        save_local_storage(storage)


# ============================================================
# 专注历史
# ============================================================

def get_user_focus_history(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT focus_json FROM user_focus_history WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT focus_json FROM user_focus_history WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    val = row['focus_json'] if isinstance(row, dict) else row[0]
                    return json.loads(val) if isinstance(val, str) else val
            except Exception as e:
                print(f"数据库查询失败: {e}")

        record = _get_json_record(load_local_storage(), 'user_focus_histories', user_id)
        return record.get('focus_json', []) if record else []


def save_user_focus_history(user_id, focus_data):
    focus_json = json.dumps(focus_data, ensure_ascii=False) if not isinstance(focus_data, str) else focus_data
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_focus_history (user_id, focus_json) VALUES (?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET focus_json=excluded.focus_json""",
                        (user_id, focus_json))
                else:
                    cursor.execute(
                        """INSERT INTO user_focus_history (user_id, focus_json) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE focus_json=%s""",
                        (user_id, focus_json, focus_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for f in storage.get('user_focus_histories', []):
            if f.get('user_id') == user_id:
                f['focus_json'] = focus_json
                save_local_storage(storage)
                return
        storage['user_focus_histories'].append({
            'id': len(storage.get('user_focus_histories', [])) + 1,
            'user_id': user_id, 'focus_json': focus_json,
        })
        save_local_storage(storage)


# ============================================================
# 生态数据
# ============================================================

def get_user_eco_data(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT eco_data_json FROM user_eco_data WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT eco_data_json FROM user_eco_data WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    val = row['eco_data_json'] if isinstance(row, dict) else row[0]
                    return json.loads(val) if isinstance(val, str) else val
            except Exception as e:
                print(f"数据库查询失败: {e}")

        record = _get_json_record(load_local_storage(), 'user_eco_data', user_id)
        return record.get('eco_data_json', {}) if record else {}


def save_user_eco_data(user_id, eco_data_dict):
    eco_json = json.dumps(eco_data_dict, ensure_ascii=False) if not isinstance(eco_data_dict, str) else eco_data_dict
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_eco_data (user_id, eco_data_json) VALUES (?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET eco_data_json=excluded.eco_data_json""",
                        (user_id, eco_json))
                else:
                    cursor.execute(
                        """INSERT INTO user_eco_data (user_id, eco_data_json) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE eco_data_json=%s""",
                        (user_id, eco_json, eco_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for e in storage.get('user_eco_data', []):
            if e.get('user_id') == user_id:
                e['eco_data_json'] = eco_json
                save_local_storage(storage)
                return
        storage['user_eco_data'].append({
            'id': len(storage.get('user_eco_data', [])) + 1,
            'user_id': user_id, 'eco_data_json': eco_json,
        })
        save_local_storage(storage)


# ============================================================
# 胶囊卡片进度
# ============================================================

def save_flashcard_progress(user_id, card_data):
    """保存单张胶囊卡片进度（掌握度、收藏、难度、笔记）"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                is_mastered = card_data.get('is_mastered', 0)
                is_favorite = card_data.get('is_favorite', 0)
                difficulty = card_data.get('difficulty', 'medium')
                user_note = card_data.get('user_note', '')
                review_count = card_data.get('review_count', 0)
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_flashcard_progress
                           (user_id, card_hash, course_id, chapter_name, front_text, back_text, hint_text,
                            is_mastered, is_favorite, difficulty, user_note, review_count,
                            first_seen_at, last_reviewed_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'), datetime('now','localtime'))
                           ON CONFLICT(user_id, card_hash) DO UPDATE SET
                               is_mastered=excluded.is_mastered,
                               is_favorite=excluded.is_favorite,
                               difficulty=excluded.difficulty,
                               user_note=excluded.user_note,
                               review_count=excluded.review_count,
                               last_reviewed_at=datetime('now','localtime')""",
                        (user_id, card_data.get('card_hash', ''), card_data.get('course_id', 'bigdata'),
                         card_data.get('chapter_name', ''), card_data.get('front', ''), card_data.get('back', ''),
                         card_data.get('hint', ''), is_mastered, is_favorite, difficulty, user_note, review_count))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        """INSERT INTO user_flashcard_progress
                           (user_id, card_hash, course_id, chapter_name, front_text, back_text, hint_text,
                            is_mastered, is_favorite, difficulty, user_note, review_count,
                            first_seen_at, last_reviewed_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                           ON DUPLICATE KEY UPDATE
                               is_mastered=%s, is_favorite=%s, difficulty=%s,
                               user_note=%s, review_count=%s, last_reviewed_at=NOW()""",
                        (user_id, card_data.get('card_hash', ''), card_data.get('course_id', 'bigdata'),
                         card_data.get('chapter_name', ''), card_data.get('front', ''), card_data.get('back', ''),
                         card_data.get('hint', ''), is_mastered, is_favorite, difficulty, user_note, review_count,
                         is_mastered, is_favorite, difficulty, user_note, review_count))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"[DB] save_flashcard_progress failed: {e}")

        storage = load_local_storage()
        progress_list = storage.get('user_flashcard_progress', [])
        found = False
        for p in progress_list:
            if p.get('user_id') == user_id and p.get('card_hash') == card_data.get('card_hash'):
                p.update(card_data)
                found = True
                break
        if not found:
            progress_list.append({'user_id': user_id, **card_data})
        storage['user_flashcard_progress'] = progress_list
        save_local_storage(storage)


def get_flashcard_progress(user_id, course_id=None, chapter_name=None):
    """获取用户胶囊卡片进度列表"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    if course_id and chapter_name:
                        cursor.execute(
                            """SELECT * FROM user_flashcard_progress
                               WHERE user_id = ? AND course_id = ? AND chapter_name = ?""",
                            (user_id, course_id, chapter_name))
                    elif course_id:
                        cursor.execute(
                            "SELECT * FROM user_flashcard_progress WHERE user_id = ? AND course_id = ?",
                            (user_id, course_id))
                    else:
                        cursor.execute(
                            "SELECT * FROM user_flashcard_progress WHERE user_id = ?",
                            (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    if course_id and chapter_name:
                        cursor.execute(
                            """SELECT * FROM user_flashcard_progress
                               WHERE user_id = %s AND course_id = %s AND chapter_name = %s""",
                            (user_id, course_id, chapter_name))
                    elif course_id:
                        cursor.execute(
                            "SELECT * FROM user_flashcard_progress WHERE user_id = %s AND course_id = %s",
                            (user_id, course_id))
                    else:
                        cursor.execute(
                            "SELECT * FROM user_flashcard_progress WHERE user_id = %s",
                            (user_id,))
                rows = cursor.fetchall()
                cursor.close()
                result = []
                for row in rows:
                    if isinstance(row, dict):
                        result.append(row)
                    elif hasattr(row, 'keys'):
                        result.append({key: row[key] for key in row.keys()})
                    else:
                        result.append({
                            'card_hash': row[2], 'course_id': row[3], 'chapter_name': row[4],
                            'front_text': row[5], 'back_text': row[6], 'hint_text': row[7],
                            'is_mastered': row[8], 'is_favorite': row[9], 'difficulty': row[10],
                            'user_note': row[11], 'review_count': row[12],
                            'first_seen_at': row[13], 'last_reviewed_at': row[14],
                        })
                return result
            except Exception as e:
                print(f"[DB] get_flashcard_progress failed: {e}")

        storage = load_local_storage()
        progress_list = storage.get('user_flashcard_progress', [])
        result = []
        for p in progress_list:
            if p.get('user_id') != user_id:
                continue
            if course_id and p.get('course_id') != course_id:
                continue
            if chapter_name and p.get('chapter_name') != chapter_name:
                continue
            result.append(p)
        return result


def get_flashcard_stats(user_id):
    """获取用户胶囊学习统计"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                stats = {}
                if _is_sqlite(conn):
                    cursor.execute(
                        "SELECT COUNT(*) FROM user_flashcard_progress WHERE user_id = ?",
                        (user_id,))
                    stats['total_cards'] = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT COUNT(*) FROM user_flashcard_progress WHERE user_id = ? AND is_mastered = 1",
                        (user_id,))
                    stats['total_mastered'] = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT COUNT(*) FROM user_flashcard_progress WHERE user_id = ? AND is_favorite = 1",
                        (user_id,))
                    stats['total_favorited'] = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT COUNT(*) FROM user_flashcard_sessions WHERE user_id = ? AND session_date = date('now','localtime')",
                        (user_id,))
                    stats['today_sessions'] = cursor.fetchone()[0]
                    cursor.execute(
                        """SELECT SUM(cards_answered) FROM user_flashcard_sessions
                           WHERE user_id = ? AND session_date = date('now','localtime')""",
                        (user_id,))
                    row = cursor.fetchone()
                    stats['today_answered'] = row[0] or 0
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        "SELECT COUNT(*) as c FROM user_flashcard_progress WHERE user_id = %s",
                        (user_id,))
                    stats['total_cards'] = cursor.fetchone()['c']
                    cursor.execute(
                        "SELECT COUNT(*) as c FROM user_flashcard_progress WHERE user_id = %s AND is_mastered = 1",
                        (user_id,))
                    stats['total_mastered'] = cursor.fetchone()['c']
                    cursor.execute(
                        "SELECT COUNT(*) as c FROM user_flashcard_progress WHERE user_id = %s AND is_favorite = 1",
                        (user_id,))
                    stats['total_favorited'] = cursor.fetchone()['c']
                    cursor.execute(
                        "SELECT COUNT(*) as c FROM user_flashcard_sessions WHERE user_id = %s AND session_date = CURDATE()",
                        (user_id,))
                    stats['today_sessions'] = cursor.fetchone()['c']
                    cursor.execute(
                        """SELECT SUM(cards_answered) as s FROM user_flashcard_sessions
                           WHERE user_id = %s AND session_date = CURDATE()""",
                        (user_id,))
                    row = cursor.fetchone()
                    stats['today_answered'] = row['s'] or 0
                cursor.close()
                return stats
            except Exception as e:
                print(f"[DB] get_flashcard_stats failed: {e}")

        storage = load_local_storage()
        progress_list = storage.get('user_flashcard_progress', [])
        user_progress = [p for p in progress_list if p.get('user_id') == user_id]
        session_list = storage.get('user_flashcard_sessions', [])
        today = datetime.now().strftime('%Y-%m-%d')
        today_sessions = [s for s in session_list if s.get('user_id') == user_id and s.get('session_date') == today]
        return {
            'total_cards': len(user_progress),
            'total_mastered': sum(1 for p in user_progress if p.get('is_mastered')),
            'total_favorited': sum(1 for p in user_progress if p.get('is_favorite')),
            'today_sessions': len(today_sessions),
            'today_answered': sum(s.get('cards_answered', 0) for s in today_sessions),
        }


def save_flashcard_session(user_id, session_data):
    """保存一次胶囊学习会话"""
    session_json = json.dumps(session_data, ensure_ascii=False)
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_flashcard_sessions
                           (user_id, session_date, course_id, chapter_name, cards_total, cards_answered,
                            cards_mastered, cards_favorited, duration_seconds, session_json)
                           VALUES (?, date('now','localtime'), ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, session_data.get('course_id', 'bigdata'),
                         session_data.get('chapter_name', ''),
                         session_data.get('cards_total', 0),
                         session_data.get('cards_answered', 0),
                         session_data.get('cards_mastered', 0),
                         session_data.get('cards_favorited', 0),
                         session_data.get('duration_seconds', 0),
                         session_json))
                else:
                    import pymysql
                    cursor = conn.cursor()
                    cursor.execute(
                        """INSERT INTO user_flashcard_sessions
                           (user_id, session_date, course_id, chapter_name, cards_total, cards_answered,
                            cards_mastered, cards_favorited, duration_seconds, session_json)
                           VALUES (%s, CURDATE(), %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (user_id, session_data.get('course_id', 'bigdata'),
                         session_data.get('chapter_name', ''),
                         session_data.get('cards_total', 0),
                         session_data.get('cards_answered', 0),
                         session_data.get('cards_mastered', 0),
                         session_data.get('cards_favorited', 0),
                         session_data.get('duration_seconds', 0),
                         session_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"[DB] save_flashcard_session failed: {e}")

        storage = load_local_storage()
        session_list = storage.get('user_flashcard_sessions', [])
        session_list.append({
            'id': len(session_list) + 1,
            'user_id': user_id,
            'session_date': datetime.now().strftime('%Y-%m-%d'),
            **session_data,
        })
        storage['user_flashcard_sessions'] = session_list
        save_local_storage(storage)


def get_flashcard_sessions(user_id, limit=30):
    """获取用户最近的胶囊学习会话"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """SELECT * FROM user_flashcard_sessions WHERE user_id = ?
                           ORDER BY created_at DESC LIMIT ?""",
                        (user_id, limit))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        """SELECT * FROM user_flashcard_sessions WHERE user_id = %s
                           ORDER BY created_at DESC LIMIT %s""",
                        (user_id, limit))
                rows = cursor.fetchall()
                cursor.close()
                result = []
                for row in rows:
                    if isinstance(row, dict):
                        result.append(row)
                    elif hasattr(row, 'keys'):
                        result.append({key: row[key] for key in row.keys()})
                    else:
                        result.append({
                            'session_date': row[2], 'course_id': row[3], 'chapter_name': row[4],
                            'cards_total': row[5], 'cards_answered': row[6],
                            'cards_mastered': row[7], 'cards_favorited': row[8],
                            'duration_seconds': row[9], 'session_json': row[10],
                        })
                return result
            except Exception as e:
                print(f"[DB] get_flashcard_sessions failed: {e}")

        storage = load_local_storage()
        session_list = storage.get('user_flashcard_sessions', [])
        user_sessions = [s for s in session_list if s.get('user_id') == user_id]
        user_sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return user_sessions[:limit]


# ============================================================
# 全息知识生态 - SM2 间隔重复算法
# ============================================================

def calculate_sm2(quality, easiness_factor, interval, repetitions):
    """
    SM-2 间隔重复算法计算

    参数:
        quality: 回答质量 (0-5)
            0 - 完全忘记
            1 - 错误但看到答案后想起
            2 - 错误但感觉接近
            3 - 正确但困难
            4 - 正确且稍慢
            5 - 正确且立即想起
        easiness_factor: 简易度因子 (初始2.5, 最小1.3)
        interval: 当前间隔天数
        repetitions: 连续正确次数

    返回:
        (new_interval, new_ef, new_repetitions, next_review_date)
    """
    import datetime

    # 计算新的简易度因子
    # EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
    new_ef = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.3, new_ef)  # 最小1.3

    if quality < 3:
        # 回答不正确，重新开始
        new_repetitions = 0
        new_interval = 1
    else:
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = round(interval * new_ef)

    # 计算下次复习日期
    next_review = datetime.datetime.now() + datetime.timedelta(days=new_interval)

    return new_interval, new_ef, new_repetitions, next_review.isoformat()


def calculate_comprehensive_score(node_data):
    """
    计算知识节点的综合评分 (0-100)

    综合评分 = 正确率分 (50%) + 遗忘曲线分 (30%) + 学习深度分 (20%)

    参数:
        node_data: 包含 sm2_data 和 stats 的节点数据

    返回:
        综合评分 (0-100)
    """
    import datetime

    sm2 = node_data.get('sm2_data', {})
    stats = node_data.get('stats', {})

    # 1. 正确率分 (50%)
    total = stats.get('total_reviews', 0)
    correct = stats.get('correct_count', 0)
    if total > 0:
        accuracy_score = (correct / total) * 50
    else:
        accuracy_score = 25  # 没有记录时给个中间值

    # 2. 遗忘曲线分 (30%) - 距离下次复习越远越健康
    next_review_str = sm2.get('next_review')
    if next_review_str:
        try:
            next_review = datetime.datetime.fromisoformat(next_review_str.replace('Z', '+00:00'))
            now = datetime.datetime.now()
            days_until = (next_review - now).total_seconds() / 86400

            if days_until < 0:
                # 已过期 - 危险
                forgetting_curve_score = max(0, 30 + days_until * 5)
            elif days_until < 1:
                # 24小时内 - 警告
                forgetting_curve_score = 15 + days_until * 15
            elif days_until < 3:
                # 1-3天 - 正常
                forgetting_curve_score = 15 + (days_until - 1) * 7.5
            else:
                # 3天以上 - 优秀
                forgetting_curve_score = 30
        except:
            forgetting_curve_score = 15
    else:
        forgetting_curve_score = 15  # 没有复习记录

    # 3. 学习深度分 (20%) - 基于复习次数和EF
    reps = sm2.get('repetitions', 0)
    ef = sm2.get('easiness_factor', 2.5)
    depth_score = min(20, reps * 2 + (ef - 1.3) * 5)

    total_score = accuracy_score + forgetting_curve_score + depth_score
    return round(min(100, max(0, total_score)))


def get_node_status(node_data):
    """
    根据综合评分和复习时间判断节点状态

    返回: 'healthy', 'warning', 'danger'
    """
    import datetime

    score = calculate_comprehensive_score(node_data)
    sm2 = node_data.get('sm2_data', {})
    next_review_str = sm2.get('next_review')

    # 超过复习时间 → danger
    if next_review_str:
        try:
            next_review = datetime.datetime.fromisoformat(next_review_str.replace('Z', '+00:00'))
            now = datetime.datetime.now()
            if next_review < now:
                return 'danger'
        except:
            pass

    # 综合评分判断
    if score >= 70:
        return 'healthy'
    elif score >= 40:
        return 'warning'
    else:
        return 'danger'


def calculate_urgency_score(node_data):
    """
    基于艾宾浩斯遗忘曲线计算机器的紧迫性评分 (0-100)

    紧迫性评分 = 距离复习时间越近，评分越高
    - 已过期: 100 (最高紧迫)
    - 1天内: 95-99
    - 1-3天: 70-94
    - 3-7天: 30-69
    - 7天以上: 0-29

    参数:
        node_data: 包含 sm2_data 的节点数据

    返回:
        urgency_score (0-100), time_to_review (人类可读), hours_until (小时数)
    """
    import datetime

    sm2 = node_data.get('sm2_data', {})
    next_review_str = sm2.get('next_review')

    if not next_review_str:
        # 没有复习计划，默认为最不紧迫
        return 0, '未安排', float('inf')

    try:
        next_review = datetime.datetime.fromisoformat(next_review_str.replace('Z', '+00:00'))
        # 如果是带时区的datetime，转换为本地时间
        if next_review.tzinfo is not None:
            next_review = next_review.replace(tzinfo=None)

        now = datetime.datetime.now()
        hours_until = (next_review - now).total_seconds() / 3600

        if hours_until < 0:
            # 已过期 - 最高紧迫
            urgency = 100
            time_str = '已过期'
        elif hours_until < 1:
            # 不到1小时
            urgency = 98
            time_str = '不到1小时'
        elif hours_until < 24:
            # 1-24小时
            urgency = 95 - (hours_until / 24) * 5  # 95-90
            time_str = f'{int(hours_until)}小时'
        elif hours_until < 72:
            # 1-3天
            urgency = 90 - ((hours_until - 24) / 48) * 20  # 90-70
            time_str = f'{int(hours_until / 24)}天'
        elif hours_until < 168:
            # 3-7天
            urgency = 70 - ((hours_until - 72) / 96) * 40  # 70-30
            time_str = f'{int(hours_until / 24)}天'
        else:
            # 7天以上
            urgency = max(0, 30 - ((hours_until - 168) / 672) * 30)  # 30-0
            days = hours_until / 24
            if days < 14:
                time_str = f'{int(days)}天'
            elif days < 30:
                time_str = f'{int(days / 7)}周'
            else:
                time_str = f'{int(days / 30)}月'

        return round(urgency), time_str, hours_until

    except Exception as e:
        print(f"计算紧迫性评分失败: {e}")
        return 0, '未知', float('inf')


def get_knowledge_layout(user_id):
    """
    获取知识节点的遗忘曲线布局数据

    返回每个节点的:
    - position: 基于紧迫性的 X 坐标 (0-100)
    - Y坐标: 基于知识层级
    - urgency: 紧迫性评分
    - time_to_review: 距离下次复习的人类可读时间
    - connection_lines: 需要绘制的连接线

    返回:
        {
            'nodes': [...布局后的节点列表...],
            'tree_connections': [...父子连接线...],
            'ai_connections': [...AI分析的相关连接线...]
        }
    """
    import json as json_mod

    nodes = get_active_knowledge_nodes(user_id)

    if not nodes:
        return {'nodes': [], 'tree_connections': [], 'ai_connections': []}

    # 计算每个节点的位置和紧迫性
    level_y_map = {'root': 10, 'branch': 35, 'leaf': 60}

    layout_nodes = []
    tree_connections = []
    ai_connections = []

    for node in nodes:
        urgency, time_str, hours = calculate_urgency_score(node)
        level = node.get('level', 'leaf')
        y = level_y_map.get(level, 60)

        # 构建布局节点
        layout_node = {
            **node,
            'urgency': urgency,
            'urgency_x': urgency,  # 0-100, 左边=紧迫
            'position_y': y,
            'time_to_review': time_str,
            'hours_until_review': hours,
            'level_y': y
        }
        layout_nodes.append(layout_node)

        # 父子连接线
        parent_id = node.get('parent_id')
        if parent_id:
            tree_connections.append({
                'source': node.get('node_id'),
                'target': parent_id,
                'type': 'tree'
            })

        # AI分析的相关连接线
        related_str = node.get('related_node_ids', '[]')
        if isinstance(related_str, str):
            try:
                related_list = json_mod.loads(related_str)
            except:
                related_list = []
        else:
            related_list = related_str

        for rel in related_list:
            if rel.get('type') in ('prerequisite', 'related'):
                ai_connections.append({
                    'source': node.get('node_id'),
                    'target': rel.get('node_id'),
                    'type': rel.get('type'),
                    'strength': rel.get('strength', 0.5)
                })

    return {
        'nodes': layout_nodes,
        'tree_connections': tree_connections,
        'ai_connections': ai_connections
    }


def init_knowledge_tables():
    """初始化知识节点相关的数据表"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    # SQLite
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS knowledge_nodes (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            node_id TEXT NOT NULL UNIQUE,
                            name TEXT NOT NULL,
                            parent_id TEXT,
                            level TEXT DEFAULT 'leaf',
                            icon TEXT DEFAULT '📚',
                            subject TEXT DEFAULT '',
                            is_active INTEGER DEFAULT 0,
                            first_studied_at TEXT,
                            last_studied_at TEXT,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            sm2_data_json TEXT,
                            stats_json TEXT,
                            position_x REAL DEFAULT 0,
                            position_y REAL DEFAULT 0,
                            related_node_ids TEXT DEFAULT '[]',
                            ai_analyzed_at TEXT
                        )
                    """)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS review_records (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            record_id TEXT NOT NULL UNIQUE,
                            user_id INTEGER NOT NULL,
                            node_id TEXT NOT NULL,
                            review_date TEXT DEFAULT CURRENT_TIMESTAMP,
                            quality INTEGER DEFAULT 0,
                            response_time REAL DEFAULT 0,
                            sm2_result_json TEXT
                        )
                    """)
                else:
                    # MySQL
                    cursor.execute("""
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
                            related_node_ids TEXT DEFAULT '[]',
                            ai_analyzed_at TIMESTAMP NULL,
                            INDEX idx_user_id (user_id)
                        )
                    """)
                    cursor.execute("""
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
                        )
                    """)
                conn.commit()
                cursor.close()
            except Exception as e:
                print(f"初始化知识节点表失败: {e}")


def get_knowledge_nodes(user_id):
    """获取用户的所有知识节点"""
    init_knowledge_tables()

    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        "SELECT * FROM knowledge_nodes WHERE user_id = ?",
                        (user_id,))
                else:
                    cursor.execute(
                        "SELECT * FROM knowledge_nodes WHERE user_id = %s",
                        (user_id,))
                rows = cursor.fetchall()
                cursor.close()

                nodes = []
                for row in rows:
                    node = dict(row) if isinstance(row, dict) else {
                        'id': row[0], 'user_id': row[1], 'node_id': row[2],
                        'name': row[3], 'parent_id': row[4], 'level': row[5],
                        'icon': row[6], 'subject': row[7], 'is_active': row[8],
                        'first_studied_at': row[9], 'last_studied_at': row[10],
                        'created_at': row[11], 'sm2_data_json': row[12],
                        'stats_json': row[13], 'position_x': row[14], 'position_y': row[15],
                        'related_node_ids': row[16] if len(row) > 16 else '[]',
                        'ai_analyzed_at': row[17] if len(row) > 17 else None
                    }
                    # 解析 JSON 字段
                    import json as json_mod
                    if isinstance(node.get('sm2_data_json'), str):
                        node['sm2_data'] = json_mod.loads(node['sm2_data_json'])
                    else:
                        node['sm2_data'] = node.get('sm2_data_json', {})
                    if isinstance(node.get('stats_json'), str):
                        node['stats'] = json_mod.loads(node['stats_json'])
                    else:
                        node['stats'] = node.get('stats_json', {})
                    # 解析 related_node_ids
                    related_str = node.get('related_node_ids', '[]')
                    if isinstance(related_str, str):
                        try:
                            node['related_node_ids'] = json_mod.loads(related_str)
                        except:
                            node['related_node_ids'] = []
                    else:
                        node['related_node_ids'] = related_str if related_str else []
                    node['status'] = get_node_status(node)
                    nodes.append(node)
                return nodes
            except Exception as e:
                print(f"获取知识节点失败: {e}")

        # JSON fallback
        storage = load_local_storage()
        for u in storage.get('user_eco_data', []):
            if u.get('user_id') == user_id:
                return u.get('knowledge_nodes', [])
        return []


def get_active_knowledge_nodes(user_id):
    """
    获取用户已激活的知识节点（真正在学习的课程）
    根据学习记录中的课程主题过滤
    """
    import datetime

    # 获取用户的学习记录
    learning_record = get_learning_record(user_id)
    if not learning_record:
        return []

    # 从学习记录中获取课程信息
    profile_json = learning_record.get('profile_json', '{}')
    try:
        import json as json_mod
        profile = json_mod.loads(profile_json) if isinstance(profile_json, str) else profile_json
    except:
        profile = {}

    # 获取用户正在学习的课程主题
    studied_subjects = profile.get('subjects', [])
    if not studied_subjects:
        # 如果没有明确的主题，使用 difficulty_level 作为筛选
        difficulty = learning_record.get('difficulty_level', '')
        if difficulty:
            studied_subjects = [difficulty]

    # 获取所有知识节点
    all_nodes = get_knowledge_nodes(user_id)

    # 过滤：只返回激活的且属于已学课程的节点
    active_nodes = []
    for node in all_nodes:
        is_active = node.get('is_active', False)
        node_subject = node.get('subject', '')

        # 检查节点是否激活且属于已学课程
        if is_active and (not studied_subjects or node_subject in studied_subjects or not node_subject):
            active_nodes.append(node)

    return active_nodes


def activate_nodes_by_subjects(user_id, subjects):
    """
    根据课程主题激活知识节点
    """
    import json as json_mod

    if not subjects:
        return

    all_nodes = get_knowledge_nodes(user_id)
    now = datetime.datetime.now().isoformat()

    for node in all_nodes:
        if node.get('subject') in subjects:
            node['is_active'] = True
            if not node.get('first_studied_at'):
                node['first_studied_at'] = now
            node['last_studied_at'] = now
            save_knowledge_node(user_id, node)


def save_knowledge_node(user_id, node_data):
    """保存知识节点（创建或更新）"""
    import json as json_mod

    node_id = node_data.get('node_id')
    sm2_data = node_data.get('sm2_data', {})
    stats = node_data.get('stats', {})

    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                sm2_json = json_mod.dumps(sm2_data, ensure_ascii=False)
                stats_json = json_mod.dumps(stats, ensure_ascii=False)

                if _is_sqlite(conn):
                    cursor.execute("""
                        INSERT INTO knowledge_nodes
                        (user_id, node_id, name, parent_id, level, icon, sm2_data_json, stats_json, position_x, position_y)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(node_id) DO UPDATE SET
                            name=excluded.name, parent_id=excluded.parent_id, level=excluded.level,
                            icon=excluded.icon, sm2_data_json=excluded.sm2_data_json,
                            stats_json=excluded.stats_json, position_x=excluded.position_x, position_y=excluded.position_y
                    """, (
                        user_id, node_id, node_data.get('name', ''), node_data.get('parent_id'),
                        node_data.get('level', 'leaf'), node_data.get('icon', '📚'),
                        sm2_json, stats_json,
                        node_data.get('position_x', 0), node_data.get('position_y', 0)
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO knowledge_nodes
                        (user_id, node_id, name, parent_id, level, icon, sm2_data_json, stats_json, position_x, position_y)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            name=VALUES(name), parent_id=VALUES(parent_id), level=VALUES(level),
                            icon=VALUES(icon), sm2_data_json=VALUES(sm2_data_json),
                            stats_json=VALUES(stats_json), position_x=VALUES(position_x), position_y=VALUES(position_y)
                    """, (
                        user_id, node_id, node_data.get('name', ''), node_data.get('parent_id'),
                        node_data.get('level', 'leaf'), node_data.get('icon', '📚'),
                        sm2_json, stats_json,
                        node_data.get('position_x', 0), node_data.get('position_y', 0)
                    ))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"保存知识节点失败: {e}")
                return False

        # JSON fallback
        storage = load_local_storage()
        for u in storage.get('user_eco_data', []):
            if u.get('user_id') == user_id:
                nodes = u.get('knowledge_nodes', [])
                for i, n in enumerate(nodes):
                    if n.get('node_id') == node_id:
                        nodes[i] = node_data
                        u['knowledge_nodes'] = nodes
                        save_local_storage(storage)
                        return True
                nodes.append(node_data)
                u['knowledge_nodes'] = nodes
                save_local_storage(storage)
                return True
        return False


def update_node_relations(user_id, node_id, related_list, analyzed_at=None):
    """更新节点的关系数据

    参数:
        user_id: 用户ID
        node_id: 节点ID
        related_list: 关系列表 [{'node_id': 'xxx', 'type': 'prerequisite', 'strength': 0.9}, ...]
        analyzed_at: 分析时间（ISO格式字符串）
    """
    import json as json_mod

    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                related_json = json_mod.dumps(related_list, ensure_ascii=False)

                if _is_sqlite(conn):
                    cursor.execute("""
                        UPDATE knowledge_nodes
                        SET related_node_ids = ?, ai_analyzed_at = ?
                        WHERE user_id = ? AND node_id = ?
                    """, (related_json, analyzed_at, user_id, node_id))
                else:
                    cursor.execute("""
                        UPDATE knowledge_nodes
                        SET related_node_ids = %s, ai_analyzed_at = %s
                        WHERE user_id = %s AND node_id = %s
                    """, (related_json, analyzed_at, user_id, node_id))

                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"更新节点关系失败: {e}")
                return False

        # JSON fallback - 暂时不支持
        return False


def add_review_record(user_id, node_id, quality, response_time=0):
    """添加复习记录并更新节点的SM2数据"""
    import datetime
    import json as json_mod

    # 获取当前节点数据
    nodes = get_knowledge_nodes(user_id)
    node = None
    for n in nodes:
        if n.get('node_id') == node_id:
            node = n
            break

    if not node:
        return None

    sm2_data = node.get('sm2_data', {
        'easiness_factor': 2.5,
        'interval': 1,
        'repetitions': 0,
        'next_review': datetime.datetime.now().isoformat(),
        'last_review': None
    })
    stats = node.get('stats', {'total_reviews': 0, 'correct_count': 0, 'avg_response_time': 0})

    # 计算新的SM2值
    new_interval, new_ef, new_reps, next_review = calculate_sm2(
        quality,
        sm2_data.get('easiness_factor', 2.5),
        sm2_data.get('interval', 1),
        sm2_data.get('repetitions', 0)
    )

    # 更新SM2数据
    sm2_data['easiness_factor'] = new_ef
    sm2_data['interval'] = new_interval
    sm2_data['repetitions'] = new_reps
    sm2_data['next_review'] = next_review
    sm2_data['last_review'] = datetime.datetime.now().isoformat()

    # 更新统计
    stats['total_reviews'] = stats.get('total_reviews', 0) + 1
    if quality >= 3:
        stats['correct_count'] = stats.get('correct_count', 0) + 1
    current_avg = stats.get('avg_response_time', 0)
    total = stats['total_reviews']
    stats['avg_response_time'] = (current_avg * (total - 1) + response_time) / total

    # 保存更新后的节点
    node['sm2_data'] = sm2_data
    node['stats'] = stats
    save_knowledge_node(user_id, node)

    # 创建复习记录
    record_id = f"{node_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    sm2_result = {
        'new_interval': new_interval,
        'new_ef': new_ef,
        'new_reps': new_reps
    }

    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("""
                        INSERT INTO review_records (record_id, user_id, node_id, quality, response_time, sm2_result_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (record_id, user_id, node_id, quality, response_time, json_mod.dumps(sm2_result)))
                else:
                    cursor.execute("""
                        INSERT INTO review_records (record_id, user_id, node_id, quality, response_time, sm2_result_json)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (record_id, user_id, node_id, quality, response_time, json_mod.dumps(sm2_result)))
                conn.commit()
                cursor.close()
            except Exception as e:
                print(f"保存复习记录失败: {e}")

    return {
        'record_id': record_id,
        'node_id': node_id,
        'quality': quality,
        'sm2_result': sm2_result,
        'next_review': next_review
    }


def get_review_records(user_id, node_id=None, limit=50):
    """获取复习记录"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if node_id:
                    if _is_sqlite(conn):
                        cursor.execute(
                            "SELECT * FROM review_records WHERE user_id = ? AND node_id = ? ORDER BY review_date DESC LIMIT ?",
                            (user_id, node_id, limit))
                    else:
                        cursor.execute(
                            "SELECT * FROM review_records WHERE user_id = %s AND node_id = %s ORDER BY review_date DESC LIMIT %s",
                            (user_id, node_id, limit))
                else:
                    if _is_sqlite(conn):
                        cursor.execute(
                            "SELECT * FROM review_records WHERE user_id = ? ORDER BY review_date DESC LIMIT ?",
                            (user_id, limit))
                    else:
                        cursor.execute(
                            "SELECT * FROM review_records WHERE user_id = %s ORDER BY review_date DESC LIMIT %s",
                            (user_id, limit))
                rows = cursor.fetchall()
                cursor.close()

                records = []
                for row in rows:
                    r = dict(row) if isinstance(row, dict) else {
                        'id': row[0], 'record_id': row[1], 'user_id': row[2],
                        'node_id': row[3], 'review_date': row[4], 'quality': row[5],
                        'response_time': row[6], 'sm2_result_json': row[7]
                    }
                    if isinstance(r.get('sm2_result_json'), str):
                        import json as json_mod
                        r['sm2_result'] = json_mod.loads(r['sm2_result_json'])
                    records.append(r)
                return records
            except Exception as e:
                print(f"获取复习记录失败: {e}")

        return []


def get_pending_reviews(user_id):
    """获取需要复习的节点列表"""
    import datetime

    nodes = get_knowledge_nodes(user_id)
    pending = []

    for node in nodes:
        sm2 = node.get('sm2_data', {})
        next_review_str = sm2.get('next_review')
        if next_review_str:
            try:
                next_review = datetime.datetime.fromisoformat(next_review_str.replace('Z', '+00:00'))
                now = datetime.datetime.now()
                if next_review <= now:
                    pending.append({
                        'node_id': node.get('node_id'),
                        'name': node.get('name'),
                        'icon': node.get('icon', '📚'),
                        'next_review': next_review_str,
                        'status': 'overdue'
                    })
                elif (next_review - now).total_seconds() < 86400:  # 24小时内
                    pending.append({
                        'node_id': node.get('node_id'),
                        'name': node.get('name'),
                        'icon': node.get('icon', '📚'),
                        'next_review': next_review_str,
                        'status': 'due_soon'
                    })
            except:
                pass

    return pending


# ============================================================
# 架构项目
# ============================================================

def get_user_projects(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT projects_json FROM user_projects WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT projects_json FROM user_projects WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    val = row['projects_json'] if isinstance(row, dict) else row[0]
                    return json.loads(val) if isinstance(val, str) else val
            except Exception as e:
                print(f"数据库查询失败: {e}")

        record = _get_json_record(load_local_storage(), 'user_projects', user_id)
        return record.get('projects_json', []) if record else []


def save_user_projects(user_id, projects_data):
    projects_json = json.dumps(projects_data, ensure_ascii=False) if not isinstance(projects_data, str) else projects_data
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_projects (user_id, projects_json) VALUES (?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET projects_json=excluded.projects_json""",
                        (user_id, projects_json))
                else:
                    cursor.execute(
                        """INSERT INTO user_projects (user_id, projects_json) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE projects_json=%s""",
                        (user_id, projects_json, projects_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for p in storage.get('user_projects', []):
            if p.get('user_id') == user_id:
                p['projects_json'] = projects_json
                save_local_storage(storage)
                return
        storage['user_projects'].append({
            'id': len(storage.get('user_projects', [])) + 1,
            'user_id': user_id, 'projects_json': projects_json,
        })
        save_local_storage(storage)


# ============================================================
# 日历事件
# ============================================================

def get_user_calendar_events(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT events_json FROM user_calendar_events WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT events_json FROM user_calendar_events WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    val = row['events_json'] if isinstance(row, dict) else row[0]
                    return json.loads(val) if isinstance(val, str) else val
            except Exception as e:
                print(f"数据库查询失败: {e}")

        record = _get_json_record(load_local_storage(), 'user_calendar_events', user_id)
        return record.get('events_json', {}) if record else {}


def save_user_calendar_events(user_id, events_data):
    events_json = json.dumps(events_data, ensure_ascii=False) if not isinstance(events_data, str) else events_data
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO user_calendar_events (user_id, events_json) VALUES (?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET events_json=excluded.events_json""",
                        (user_id, events_json))
                else:
                    cursor.execute(
                        """INSERT INTO user_calendar_events (user_id, events_json) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE events_json=%s""",
                        (user_id, events_json, events_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for ce in storage.get('user_calendar_events', []):
            if ce.get('user_id') == user_id:
                ce['events_json'] = events_json
                save_local_storage(storage)
                return
        storage['user_calendar_events'].append({
            'id': len(storage.get('user_calendar_events', [])) + 1,
            'user_id': user_id, 'events_json': events_json,
        })
        save_local_storage(storage)


# ============================================================
# 每日学习路线
# ============================================================

def get_daily_route(user_id, route_date):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        "SELECT * FROM daily_routes WHERE user_id = ? AND route_date = ?",
                        (user_id, route_date))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        "SELECT * FROM daily_routes WHERE user_id = %s AND route_date = %s",
                        (user_id, route_date))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    if not isinstance(row, dict):
                        row = dict(row)
                    for field in ('tasks_json', 'completed_json'):
                        val = row.get(field)
                        if isinstance(val, str):
                            try:
                                row[field] = json.loads(val)
                            except Exception:
                                pass
                    return row
            except Exception as e:
                print(f"数据库查询失败: {e}")

        storage = load_local_storage()
        for route in storage.get('daily_routes', []):
            if route.get('user_id') == user_id and route.get('route_date') == route_date:
                return route
        return None


def save_daily_route(user_id, route_date, tasks, completed=None):
    tasks_json = json.dumps(tasks, ensure_ascii=False) if not isinstance(tasks, str) else tasks
    completed_json = json.dumps(completed or [], ensure_ascii=False)
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO daily_routes (user_id, route_date, tasks_json, completed_json)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT(user_id, route_date) DO UPDATE SET
                               tasks_json=excluded.tasks_json, completed_json=excluded.completed_json""",
                        (user_id, route_date, tasks_json, completed_json))
                else:
                    cursor.execute(
                        """INSERT INTO daily_routes (user_id, route_date, tasks_json, completed_json)
                           VALUES (%s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                               tasks_json=%s, completed_json=%s""",
                        (user_id, route_date, tasks_json, completed_json,
                         tasks_json, completed_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for route in storage.get('daily_routes', []):
            if route.get('user_id') == user_id and route.get('route_date') == route_date:
                route['tasks_json'] = tasks_json
                if completed is not None:
                    route['completed_json'] = completed_json
                save_local_storage(storage)
                return
        storage['daily_routes'].append({
            'id': len(storage.get('daily_routes', [])) + 1,
            'user_id': user_id, 'route_date': route_date,
            'tasks_json': tasks_json, 'completed_json': completed_json,
        })
        save_local_storage(storage)


def get_user_daily_routes(user_id, limit=30):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        "SELECT * FROM daily_routes WHERE user_id = ? ORDER BY route_date DESC LIMIT ?",
                        (user_id, limit))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(
                        "SELECT * FROM daily_routes WHERE user_id = %s ORDER BY route_date DESC LIMIT %s",
                        (user_id, limit))
                rows = cursor.fetchall()
                cursor.close()
                result = []
                for row in rows:
                    if not isinstance(row, dict):
                        row = dict(row)
                    for field in ('tasks_json', 'completed_json'):
                        val = row.get(field)
                        if isinstance(val, str):
                            try:
                                row[field] = json.loads(val)
                            except Exception:
                                pass
                    result.append(row)
                return result
            except Exception as e:
                print(f"数据库查询失败: {e}")

        storage = load_local_storage()
        routes = [r for r in storage.get('daily_routes', []) if r.get('user_id') == user_id]
        routes.sort(key=lambda r: r.get('route_date', ''), reverse=True)
        return routes[:limit]


# ============================================================
# 学习时段记录 (study_sessions)
# ============================================================

def save_study_session(user_id, session_data):
    """保存学习时段记录"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                import pymysql
                cursor = conn.cursor(pymysql.cursors.DictCursor)

                # 尝试更新已存在的记录（同一用户、同一日期、同一科目）
                session_date = session_data.get('session_date')
                subject = session_data.get('subject', '')
                start_time = session_data.get('start_time', '')
                end_time = session_data.get('end_time', '')
                duration = session_data.get('duration_minutes', 0)
                node_id = session_data.get('node_id', '')

                cursor.execute("""
                    SELECT id FROM study_sessions
                    WHERE user_id = %s AND session_date = %s AND subject = %s
                    LIMIT 1
                """, (user_id, session_date, subject))

                existing = cursor.fetchone()

                if existing:
                    # 更新已有记录，累加时长
                    cursor.execute("""
                        UPDATE study_sessions
                        SET duration_minutes = duration_minutes + %s,
                            end_time = %s
                        WHERE id = %s
                    """, (duration, end_time, existing['id']))
                else:
                    # 新增记录
                    cursor.execute("""
                        INSERT INTO study_sessions
                        (user_id, session_date, duration_minutes, start_time, end_time, subject, node_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (user_id, session_date, duration, start_time, end_time, subject, node_id))

                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"保存学习时段失败: {e}")
                return False
    return False


def get_study_sessions(user_id, start_date=None, end_date=None):
    """获取学习时段记录"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                is_sql = _is_sqlite(conn)
                ph = '?' if is_sql else '%s'

                if start_date and end_date:
                    if is_sql:
                        cursor.execute(f"""
                            SELECT * FROM study_sessions
                            WHERE user_id = ? AND session_date >= ? AND session_date <= ?
                            ORDER BY session_date DESC, start_time DESC
                        """, (user_id, start_date, end_date))
                    else:
                        import pymysql
                        cursor = conn.cursor(pymysql.cursors.DictCursor)
                        cursor.execute(f"""
                            SELECT * FROM study_sessions
                            WHERE user_id = {ph} AND session_date >= {ph} AND session_date <= {ph}
                            ORDER BY session_date DESC, start_time DESC
                        """, (user_id, start_date, end_date))
                else:
                    if is_sql:
                        cursor.execute(f"""
                            SELECT * FROM study_sessions
                            WHERE user_id = ?
                            ORDER BY session_date DESC, start_time DESC
                        """, (user_id,))
                    else:
                        import pymysql
                        cursor = conn.cursor(pymysql.cursors.DictCursor)
                        cursor.execute(f"""
                            SELECT * FROM study_sessions
                            WHERE user_id = {ph}
                            ORDER BY session_date DESC, start_time DESC
                        """, (user_id,))

                rows = cursor.fetchall()
                cursor.close()
                return rows if rows else []
            except Exception as e:
                print(f"获取学习时段失败: {e}")
                return []
    return []


def get_study_sessions_by_date(user_id, date):
    """获取指定日期的学习时段"""
    return get_study_sessions(user_id, date, date)


def get_total_study_minutes(user_id, start_date=None, end_date=None):
    """获取指定日期范围的总学习时长（分钟）"""
    sessions = get_study_sessions(user_id, start_date, end_date)
    total = 0
    for session in sessions:
        duration = session.get('duration_minutes', 0) if isinstance(session, dict) else session[3]
        total += duration
    return total


# ============================================================
# 学习目标 (learning_goals)
# ============================================================

def save_learning_goal(user_id, goal_data):
    """创建或更新学习目标"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                is_sql = _is_sqlite(conn)
                ph = '?' if is_sql else '%s'

                goal_type = goal_data.get('goal_type', 'daily')
                title = goal_data.get('title', '')
                target = goal_data.get('target_value', 60)
                current = goal_data.get('current_value', 0)
                unit = goal_data.get('unit', 'minutes')
                start_date = goal_data.get('start_date', '')
                end_date = goal_data.get('end_date', '')

                if is_sql:
                    cursor.execute(f"""
                        INSERT INTO learning_goals
                        (user_id, goal_type, title, target_value, current_value, unit, start_date, end_date, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """, (user_id, goal_type, title, target, current, unit, start_date, end_date))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(f"""
                        INSERT INTO learning_goals
                        (user_id, goal_type, title, target_value, current_value, unit, start_date, end_date, is_active)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 1)
                    """, (user_id, goal_type, title, target, current, unit, start_date, end_date))

                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"保存学习目标失败: {e}")
                return False
    return False


def get_learning_goals(user_id, active_only=True):
    """获取用户的学习目标"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                is_sql = _is_sqlite(conn)
                ph = '?' if is_sql else '%s'

                if active_only:
                    if is_sql:
                        cursor.execute(f"""
                            SELECT * FROM learning_goals
                            WHERE user_id = ? AND is_active = 1
                            ORDER BY created_at DESC
                        """, (user_id,))
                    else:
                        import pymysql
                        cursor = conn.cursor(pymysql.cursors.DictCursor)
                        cursor.execute(f"""
                            SELECT * FROM learning_goals
                            WHERE user_id = {ph} AND is_active = 1
                            ORDER BY created_at DESC
                        """, (user_id,))
                else:
                    if is_sql:
                        cursor.execute(f"""
                            SELECT * FROM learning_goals
                            WHERE user_id = ?
                            ORDER BY created_at DESC
                        """, (user_id,))
                    else:
                        import pymysql
                        cursor = conn.cursor(pymysql.cursors.DictCursor)
                        cursor.execute(f"""
                            SELECT * FROM learning_goals
                            WHERE user_id = {ph}
                            ORDER BY created_at DESC
                        """, (user_id,))

                rows = cursor.fetchall()
                cursor.close()
                return rows if rows else []
            except Exception as e:
                print(f"获取学习目标失败: {e}")
                return []
    return []


def update_learning_goal(goal_id, current_value):
    """更新目标当前进度"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                is_sql = _is_sqlite(conn)
                ph = '?' if is_sql else '%s'

                if is_sql:
                    cursor.execute(f"""
                        UPDATE learning_goals
                        SET current_value = ?
                        WHERE id = ?
                    """, (current_value, goal_id))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(f"""
                        UPDATE learning_goals
                        SET current_value = {ph}
                        WHERE id = {ph}
                    """, (current_value, goal_id))

                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"更新学习目标失败: {e}")
                return False
    return False


def deactivate_learning_goal(goal_id):
    """停用学习目标"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                is_sql = _is_sqlite(conn)
                ph = '?' if is_sql else '%s'

                if is_sql:
                    cursor.execute(f"""
                        UPDATE learning_goals
                        SET is_active = 0
                        WHERE id = ?
                    """, (goal_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(f"""
                        UPDATE learning_goals
                        SET is_active = 0
                        WHERE id = {ph}
                    """, (goal_id,))

                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"停用学习目标失败: {e}")
                return False
    return False


# ============================================================
# 周学习总结 (weekly_summary)
# ============================================================

def save_weekly_summary(user_id, week_start_date, daily_minutes, hourly_distribution):
    """保存周学习总结"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                is_sql = _is_sqlite(conn)
                ph = '?' if is_sql else '%s'

                # 转换为 JSON 字符串
                daily_json = json.dumps(daily_minutes) if isinstance(daily_minutes, list) else daily_minutes
                hourly_json = json.dumps(hourly_distribution) if isinstance(hourly_distribution, dict) else hourly_distribution

                if is_sql:
                    cursor.execute(f"""
                        INSERT OR REPLACE INTO weekly_summary
                        (user_id, week_start_date, daily_minutes, hourly_distribution)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, week_start_date, daily_json, hourly_json))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(f"""
                        INSERT INTO weekly_summary
                        (user_id, week_start_date, daily_minutes, hourly_distribution)
                        VALUES ({ph}, {ph}, {ph}, {ph})
                        ON DUPLICATE KEY UPDATE
                        daily_minutes = {ph},
                        hourly_distribution = {ph}
                    """, (user_id, week_start_date, daily_json, hourly_json,
                          daily_json, hourly_json))

                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"保存周总结失败: {e}")
                return False
    return False


def get_weekly_summary(user_id, week_start_date):
    """获取指定周的总结数据"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                is_sql = _is_sqlite(conn)
                ph = '?' if is_sql else '%s'

                if is_sql:
                    cursor.execute(f"""
                        SELECT * FROM weekly_summary
                        WHERE user_id = ? AND week_start_date = ?
                    """, (user_id, week_start_date))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(f"""
                        SELECT * FROM weekly_summary
                        WHERE user_id = {ph} AND week_start_date = {ph}
                    """, (user_id, week_start_date))

                row = cursor.fetchone()
                cursor.close()

                if row:
                    result = dict(row) if not isinstance(row, dict) else row
                    # 解析 JSON 字段
                    for field in ('daily_minutes', 'hourly_distribution'):
                        if field in result and isinstance(result[field], str):
                            try:
                                result[field] = json.loads(result[field])
                            except Exception:
                                pass
                    return result
                return None
            except Exception as e:
                print(f"获取周总结失败: {e}")
                return None
    return None


def get_recent_weekly_summaries(user_id, weeks=4):
    """获取最近几周的总结数据"""
    summaries = []
    today = datetime.now()
    for i in range(weeks):
        # 计算周一日期
        week_start = today - timedelta(days=today.weekday() + 7 * i)
        week_start_str = week_start.strftime('%Y-%m-%d')
        summary = get_weekly_summary(user_id, week_start_str)
        if summary:
            summaries.append(summary)
    return summaries


# ============================================================
# 知识点掌握度计算
# ============================================================

def get_user_knowledge_mastery(user_id):
    """计算用户的知识点掌握度"""
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                is_sql = _is_sqlite(conn)
                ph = '?' if is_sql else '%s'

                # 获取所有知识点及其 SM2 数据
                if is_sql:
                    cursor.execute(f"""
                        SELECT node_id, name, sm2_data_json, stats_json
                        FROM knowledge_nodes
                        WHERE user_id = ?
                    """, (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute(f"""
                        SELECT node_id, name, sm2_data_json, stats_json
                        FROM knowledge_nodes
                        WHERE user_id = {ph}
                    """, (user_id,))

                nodes = cursor.fetchall()
                cursor.close()

                mastery_data = []
                for node in nodes:
                    if isinstance(node, tuple):
                        node = {
                            'node_id': node[0],
                            'name': node[1],
                            'sm2_data_json': node[2],
                            'stats_json': node[3]
                        }
                    else:
                        node = dict(node)

                    # 解析 SM2 数据
                    sm2_data = {}
                    if node.get('sm2_data_json'):
                        try:
                            sm2_data = json.loads(node['sm2_data_json'])
                        except Exception:
                            pass

                    # 解析统计数据
                    stats = {}
                    if node.get('stats_json'):
                        try:
                            stats = json.loads(node['stats_json'])
                        except Exception:
                            pass

                    # 计算掌握度 (0-100)
                    mastery = 0

                    # 1. 基于 EF (easiness factor): 1.3-2.5 => 0-100
                    ef = sm2_data.get('easiness_factor', 2.5)
                    if ef:
                        mastery += min(100, (ef - 1.3) / 1.2 * 100) * 0.3

                    # 2. 基于复习间隔 (interval): 1-30天 => 0-100
                    interval = sm2_data.get('interval', 1)
                    if interval:
                        mastery += min(100, interval / 30 * 100) * 0.3

                    # 3. 基于正确率: correct/total => 0-100
                    total = stats.get('total_reviews', 0)
                    correct = stats.get('correct_count', 0)
                    if total > 0:
                        accuracy = correct / total * 100
                        mastery += accuracy * 0.4

                    mastery_data.append({
                        'node_id': node.get('node_id', ''),
                        'name': node.get('name', '未知知识点'),
                        'mastery': min(100, max(0, int(mastery))),
                        'sm2_data': sm2_data,
                        'stats': stats
                    })

                return mastery_data
            except Exception as e:
                print(f"计算知识点掌握度失败: {e}")
                return []
    return []


# ============================================================
# 批量加载
# ============================================================

def get_full_user_state(user_id):
    """一次性加载用户所有数据，减少 API 调用次数"""
    state = {
        'user': None,
        'preferences': {},
        'garden': {'seeds': 3, 'garden_data': {}},
        'pet': {'pet': {}, 'pet_game': {}},
        'achievements': {},
        'stats': {},
        'notifications': {'notifications': [], 'last_update_time': 0},
        'settings': {'settings': {}, 'weather_city': '', 'floating_alarm_x': None, 'floating_alarm_y': None, 'hub_theme': ''},
        'coding_state': None,
        'weather_cache': None,
        'focus_history': [],
        'eco_data': {},
        'projects': [],
        'calendar_events': {},
        'learning_profile': None,
        'learning_path': None,
        'learning_record': None,
    }

    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                is_sql = _is_sqlite(conn)
                ph = '?' if is_sql else '%s'

                # user
                cursor.execute(f"SELECT id, username, nickname, avatar, current_task, preferred_language, theme, last_agent_id, last_login, created_at FROM user WHERE id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    state['user'] = dict(row) if not isinstance(row, dict) else row

                # preferences
                cursor.execute(f"SELECT preferences_json FROM user_preferences WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    val = row['preferences_json'] if isinstance(row, dict) else row[0]
                    state['preferences'] = json.loads(val) if isinstance(val, str) else (val or {})

                # garden
                cursor.execute(f"SELECT seeds, garden_json FROM user_garden WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    if isinstance(row, dict):
                        garden_json = row.get('garden_json', '{}')
                    else:
                        garden_json = row[1] if row[1] else '{}'
                    state['garden']['seeds'] = row[0] if not isinstance(row, dict) else row.get('seeds', 3)
                    state['garden']['garden_data'] = json.loads(garden_json) if isinstance(garden_json, str) else garden_json

                # pet
                cursor.execute(f"SELECT pet_json, pet_game_json FROM user_pet WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    pj = row[0] if not isinstance(row, dict) else row.get('pet_json', '{}')
                    gj = row[1] if not isinstance(row, dict) else row.get('pet_game_json', '{}')
                    state['pet']['pet'] = json.loads(pj) if isinstance(pj, str) else pj
                    state['pet']['pet_game'] = json.loads(gj) if isinstance(gj, str) else gj

                # achievements
                cursor.execute(f"SELECT achievements_json FROM user_achievements WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    val = row['achievements_json'] if isinstance(row, dict) else row[0]
                    state['achievements'] = json.loads(val) if isinstance(val, str) else (val or {})

                # stats
                cursor.execute(f"SELECT stats_json FROM user_stats WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    val = row['stats_json'] if isinstance(row, dict) else row[0]
                    state['stats'] = json.loads(val) if isinstance(val, str) else (val or {})

                # notifications
                cursor.execute(f"SELECT notifications_json, last_update_time FROM user_notifications WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    nj = row[0] if not isinstance(row, dict) else row.get('notifications_json', '[]')
                    lt = row[1] if not isinstance(row, dict) else row.get('last_update_time', 0)
                    state['notifications']['notifications'] = json.loads(nj) if isinstance(nj, str) else nj
                    state['notifications']['last_update_time'] = lt

                # settings
                cursor.execute(f"SELECT settings_json, weather_city, floating_alarm_x, floating_alarm_y, hub_theme FROM user_settings WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    if isinstance(row, dict):
                        sj = row.get('settings_json', '{}')
                        state['settings']['settings'] = json.loads(sj) if isinstance(sj, str) else sj
                        state['settings']['weather_city'] = row.get('weather_city', '')
                        state['settings']['floating_alarm_x'] = row.get('floating_alarm_x')
                        state['settings']['floating_alarm_y'] = row.get('floating_alarm_y')
                        state['settings']['hub_theme'] = row.get('hub_theme', '')
                    else:
                        state['settings']['settings'] = json.loads(row[0]) if row[0] else {}
                        state['settings']['weather_city'] = row[1] if row[1] else ''
                        state['settings']['floating_alarm_x'] = row[2]
                        state['settings']['floating_alarm_y'] = row[3]
                        state['settings']['hub_theme'] = row[4] if row[4] else ''

                # coding_state
                cursor.execute(f"SELECT coding_state_json FROM user_coding_state WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    val = row['coding_state_json'] if isinstance(row, dict) else row[0]
                    state['coding_state'] = json.loads(val) if isinstance(val, str) and val else val

                # weather_cache
                cursor.execute(f"SELECT weather_json FROM user_weather_cache WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    val = row['weather_json'] if isinstance(row, dict) else row[0]
                    state['weather_cache'] = json.loads(val) if isinstance(val, str) else val

                # focus_history
                cursor.execute(f"SELECT focus_json FROM user_focus_history WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    val = row['focus_json'] if isinstance(row, dict) else row[0]
                    state['focus_history'] = json.loads(val) if isinstance(val, str) else val

                # eco_data
                cursor.execute(f"SELECT eco_data_json FROM user_eco_data WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    val = row['eco_data_json'] if isinstance(row, dict) else row[0]
                    state['eco_data'] = json.loads(val) if isinstance(val, str) else val

                # projects
                cursor.execute(f"SELECT projects_json FROM user_projects WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    val = row['projects_json'] if isinstance(row, dict) else row[0]
                    state['projects'] = json.loads(val) if isinstance(val, str) else val

                # calendar_events
                cursor.execute(f"SELECT events_json FROM user_calendar_events WHERE user_id = {ph}", (user_id,))
                row = cursor.fetchone()
                if row:
                    val = row['events_json'] if isinstance(row, dict) else row[0]
                    state['calendar_events'] = json.loads(val) if isinstance(val, str) else val

                # learning profile & path & record
                state['learning_profile'] = get_user_profile(user_id)
                state['learning_path'] = get_learning_path(user_id)
                state['learning_record'] = get_learning_record(user_id)

                cursor.close()
                return state
            except Exception as e:
                print(f"批量加载用户数据失败: {e}")

        # JSON fallback: 逐个调用各函数
        state['user'] = get_user_by_username('')  # won't work, need separate lookup
        state['preferences'] = get_user_preferences(user_id)
        state['garden'] = get_user_garden(user_id) or {'seeds': 3, 'garden_data': {}}
        state['pet'] = get_user_pet(user_id) or {'pet': {}, 'pet_game': {}}
        state['achievements'] = get_user_achievements(user_id)
        state['stats'] = get_user_stats(user_id)
        state['notifications'] = get_user_notifications(user_id)
        state['settings'] = get_user_settings(user_id)
        state['coding_state'] = get_user_coding_state(user_id)
        state['weather_cache'] = get_user_weather_cache(user_id)
        state['focus_history'] = get_user_focus_history(user_id)
        state['eco_data'] = get_user_eco_data(user_id)
        state['projects'] = get_user_projects(user_id)
        state['calendar_events'] = get_user_calendar_events(user_id)
        state['learning_profile'] = get_user_profile(user_id)
        state['learning_path'] = get_learning_path(user_id)
        state['learning_record'] = get_learning_record(user_id)
        return state


# ============================================================
# 课堂记录 CRUD
# ============================================================

def init_classroom_tables():
    """初始化课堂记录表"""
    with get_db() as conn:
        if conn is None:
            return
        try:
            cursor = conn.cursor()
            if _is_sqlite(conn):
                # SQLite: use CURRENT_TIMESTAMP instead of datetime() for defaults
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS classroom_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        course_id TEXT NOT NULL UNIQUE,
                        title TEXT NOT NULL DEFAULT '',
                        ppt_pages INTEGER DEFAULT 0,
                        full_data TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                try:
                    # 检查列是否存在（SQLite 支持 PRAGMA table_info）
                    cursor.execute("PRAGMA table_info(classroom_records)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if 'ppt_pages' not in columns:
                        cursor.execute("ALTER TABLE classroom_records ADD COLUMN ppt_pages INTEGER DEFAULT 0")
                        conn.commit()
                except Exception as e:
                    print(f"添加ppt_pages列失败: {e}")
                    pass
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS classroom_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        course_id VARCHAR(100) NOT NULL UNIQUE,
                        title VARCHAR(255) NOT NULL DEFAULT '',
                        ppt_pages INT DEFAULT 0,
                        full_data LONGTEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_user_id (user_id),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                try:
                    # 先检查列是否存在（MySQL 5.x 不支持 ADD COLUMN IF NOT EXISTS）
                    cursor.execute("SHOW COLUMNS FROM classroom_records LIKE 'ppt_pages'")
                    if not cursor.fetchone():
                        cursor.execute("ALTER TABLE classroom_records ADD COLUMN ppt_pages INT DEFAULT 0")
                        conn.commit()
                except Exception as e:
                    print(f"添加ppt_pages列失败: {e}")
                    pass
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"初始化课堂记录表失败: {e}")


def init_course_generation_status_table():
    """初始化课程生成状态跟踪表"""
    with get_db() as conn:
        if conn is None:
            return
        try:
            cursor = conn.cursor()
            if _is_sqlite(conn):
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS course_generation_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        course_id TEXT NOT NULL UNIQUE,
                        total_outlines INTEGER DEFAULT 0,
                        generated_count INTEGER DEFAULT 0,
                        pending_slides_v2 TEXT,
                        pending_quiz_data TEXT,
                        pending_exercise_data TEXT,
                        is_complete INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS course_generation_status (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        course_id VARCHAR(100) NOT NULL UNIQUE,
                        total_outlines INT DEFAULT 0,
                        generated_count INT DEFAULT 0,
                        pending_slides_v2 TEXT,
                        pending_quiz_data TEXT,
                        pending_exercise_data TEXT,
                        is_complete TINYINT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_course_id (course_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"初始化course_generation_status表失败: {e}")


def save_course_generation_status(course_id: str, total_outlines: int, generated_count: int,
                                   pending_slides_v2: list = None, pending_quiz_data: list = None,
                                   pending_exercise_data: list = None, is_complete: int = 0) -> bool:
    """保存课程生成状态到数据库"""
    import json
    init_course_generation_status_table()
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                pending_slides_v2_json = json.dumps(pending_slides_v2 or [], ensure_ascii=False)
                pending_quiz_json = json.dumps(pending_quiz_data or [], ensure_ascii=False)
                pending_exercise_json = json.dumps(pending_exercise_data or [], ensure_ascii=False)

                if _is_sqlite(conn):
                    cursor.execute("""
                        INSERT INTO course_generation_status
                        (course_id, total_outlines, generated_count, pending_slides_v2,
                         pending_quiz_data, pending_exercise_data, is_complete)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(course_id) DO UPDATE SET
                            total_outlines=excluded.total_outlines,
                            generated_count=excluded.generated_count,
                            pending_slides_v2=excluded.pending_slides_v2,
                            pending_quiz_data=excluded.pending_quiz_data,
                            pending_exercise_data=excluded.pending_exercise_data,
                            is_complete=excluded.is_complete,
                            updated_at=datetime('now')
                    """, (course_id, total_outlines, generated_count, pending_slides_v2_json,
                          pending_quiz_json, pending_exercise_json, is_complete))
                else:
                    cursor.execute("""
                        INSERT INTO course_generation_status
                        (course_id, total_outlines, generated_count, pending_slides_v2,
                         pending_quiz_data, pending_exercise_data, is_complete)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            total_outlines=%s, generated_count=%s, pending_slides_v2=%s,
                            pending_quiz_data=%s, pending_exercise_data=%s, is_complete=%s
                    """, (course_id, total_outlines, generated_count, pending_slides_v2_json,
                          pending_quiz_json, pending_exercise_json, is_complete,
                          total_outlines, generated_count, pending_slides_v2_json,
                          pending_quiz_json, pending_exercise_json, is_complete))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"保存课程生成状态失败: {e}")
        return False


def get_course_generation_status(course_id: str) -> Optional[dict]:
    """获取课程生成状态"""
    import json
    init_course_generation_status_table()
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("""
                        SELECT course_id, total_outlines, generated_count, pending_slides_v2,
                               pending_quiz_data, pending_exercise_data, is_complete,
                               created_at, updated_at
                        FROM course_generation_status WHERE course_id = ?
                    """, (course_id,))
                    row = cursor.fetchone()
                    cursor.close()
                    if row:
                        return {
                            'course_id': row[0],
                            'total_outlines': row[1],
                            'generated_count': row[2],
                            'pending_slides_v2': json.loads(row[3]) if row[3] else [],
                            'pending_quiz_data': json.loads(row[4]) if row[4] else [],
                            'pending_exercise_data': json.loads(row[5]) if row[5] else [],
                            'is_complete': bool(row[6]),
                            'created_at': row[7],
                            'updated_at': row[8],
                        }
                    return None
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("""
                        SELECT course_id, total_outlines, generated_count, pending_slides_v2,
                               pending_quiz_data, pending_exercise_data, is_complete,
                               created_at, updated_at
                        FROM course_generation_status WHERE course_id = %s
                    """, (course_id,))
                    row = cursor.fetchone()
                    cursor.close()
                    if row:
                        row['pending_slides_v2'] = json.loads(row['pending_slides_v2']) if row['pending_slides_v2'] else []
                        row['pending_quiz_data'] = json.loads(row['pending_quiz_data']) if row['pending_quiz_data'] else []
                        row['pending_exercise_data'] = json.loads(row['pending_exercise_data']) if row['pending_exercise_data'] else []
                        row['is_complete'] = bool(row['is_complete'])
                        return row
                    return None
            except Exception as e:
                print(f"获取课程生成状态失败: {e}")
        return None


def update_course_generation_status(course_id: str, generated_count: int = None,
                                     pending_slides_v2: list = None, pending_quiz_data: list = None,
                                     pending_exercise_data: list = None, is_complete: int = None) -> bool:
    """更新课程生成状态（只更新提供的字段）"""
    import json
    init_course_generation_status_table()
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                current = None
                if _is_sqlite(conn):
                    cursor.execute("""
                        SELECT total_outlines, generated_count, pending_slides_v2,
                               pending_quiz_data, pending_exercise_data, is_complete
                        FROM course_generation_status WHERE course_id = ?
                    """, (course_id,))
                    current = cursor.fetchone()
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("""
                        SELECT total_outlines, generated_count, pending_slides_v2,
                               pending_quiz_data, pending_exercise_data, is_complete
                        FROM course_generation_status WHERE course_id = %s
                    """, (course_id,))
                    current = cursor.fetchone()

                if not current:
                    return False

                if _is_sqlite(conn):
                    total_outlines = current[0]
                    new_gen_count = generated_count if generated_count is not None else current[1]
                    new_pending_v2 = json.dumps(pending_slides_v2 if pending_slides_v2 is not None else json.loads(current[2] or "[]"), ensure_ascii=False)
                    new_pending_quiz = json.dumps(pending_quiz_data if pending_quiz_data is not None else json.loads(current[3] or "[]"), ensure_ascii=False)
                    new_pending_exercise = json.dumps(pending_exercise_data if pending_exercise_data is not None else json.loads(current[4] or "[]"), ensure_ascii=False)
                    new_complete = is_complete if is_complete is not None else current[5]

                    cursor.execute("""
                        UPDATE course_generation_status SET
                            generated_count = ?, pending_slides_v2 = ?, pending_quiz_data = ?,
                            pending_exercise_data = ?, is_complete = ?, updated_at = datetime('now')
                        WHERE course_id = ?
                    """, (new_gen_count, new_pending_v2, new_pending_quiz, new_pending_exercise, new_complete, course_id))
                else:
                    total_outlines = current['total_outlines']
                    new_gen_count = generated_count if generated_count is not None else current['generated_count']
                    new_pending_v2 = json.dumps(pending_slides_v2 if pending_slides_v2 is not None else json.loads(current['pending_slides_v2'] or "[]"), ensure_ascii=False)
                    new_pending_quiz = json.dumps(pending_quiz_data if pending_quiz_data is not None else json.loads(current['pending_quiz_data'] or "[]"), ensure_ascii=False)
                    new_pending_exercise = json.dumps(pending_exercise_data if pending_exercise_data is not None else json.loads(current['pending_exercise_data'] or "[]"), ensure_ascii=False)
                    new_complete = is_complete if is_complete is not None else current['is_complete']

                    cursor.execute("""
                        UPDATE course_generation_status SET
                            generated_count = %s, pending_slides_v2 = %s, pending_quiz_data = %s,
                            pending_exercise_data = %s, is_complete = %s
                        WHERE course_id = %s
                    """, (new_gen_count, new_pending_v2, new_pending_quiz, new_pending_exercise, new_complete, course_id))

                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"更新课程生成状态失败: {e}")
        return False


def save_classroom_record(user_id: int, course_id: str, title: str, full_data: str, ppt_pages: int = 0) -> bool:
    """保存课堂记录到数据库"""
    # 先初始化表（使用独立连接，不依赖contextmanager）
    init_classroom_tables()

    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("""
                        INSERT INTO classroom_records (user_id, course_id, title, ppt_pages, full_data)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(course_id) DO UPDATE SET
                            title=excluded.title,
                            ppt_pages=excluded.ppt_pages,
                            full_data=excluded.full_data,
                            updated_at=datetime('now')
                    """, (user_id, course_id, title, ppt_pages, full_data))
                else:
                    cursor.execute("""
                        INSERT INTO classroom_records (user_id, course_id, title, ppt_pages, full_data)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            title=%s, ppt_pages=%s, full_data=%s
                    """, (user_id, course_id, title, ppt_pages, full_data, title, ppt_pages, full_data))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"保存课堂记录失败: {e}")

        # JSON fallback
        storage = load_local_storage()
        records = storage.get('classroom_records', [])
        for record in records:
            if record.get('course_id') == course_id:
                record.update({'user_id': user_id, 'title': title, 'full_data': full_data, 'ppt_pages': ppt_pages})
                save_local_storage(storage)
                return True
        records.append({
            'id': len(records) + 1,
            'user_id': user_id,
            'course_id': course_id,
            'title': title,
            'ppt_pages': ppt_pages,
            'full_data': full_data,
            'created_at': 'local',
            'updated_at': 'local',
        })
        storage['classroom_records'] = records
        save_local_storage(storage)
        return True


def get_classroom_records(user_id: int) -> list:
    """获取指定学生的所有课堂记录（不含full_data）"""
    init_classroom_tables()  # 确保表已创建
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("""
                        SELECT id, user_id, course_id, title, ppt_pages, created_at, updated_at
                        FROM classroom_records WHERE user_id = ?
                        ORDER BY created_at DESC
                    """, (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("""
                        SELECT id, user_id, course_id, title, ppt_pages, created_at, updated_at
                        FROM classroom_records WHERE user_id = %s
                        ORDER BY created_at DESC
                    """, (user_id,))
                rows = cursor.fetchall()
                cursor.close()
                return [dict(row) for row in rows] if _is_sqlite(conn) else rows
            except Exception as e:
                print(f"查询课堂记录失败: {e}")

        storage = load_local_storage()
        records = storage.get('classroom_records', [])
        result = []
        for r in records:
            if r.get('user_id') == user_id:
                result.append({
                    'id': r.get('id'),
                    'user_id': r.get('user_id'),
                    'course_id': r.get('course_id'),
                    'title': r.get('title'),
                    'ppt_pages': r.get('ppt_pages', 0),
                    'created_at': r.get('created_at'),
                    'updated_at': r.get('updated_at'),
                })
        return sorted(result, key=lambda x: x.get('created_at', ''), reverse=True)


def get_classroom_record(course_id: str) -> Optional[dict]:
    """获取单个课堂记录的完整数据"""
    init_classroom_tables()  # 确保表已创建
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT * FROM classroom_records WHERE course_id = ?", (course_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT * FROM classroom_records WHERE course_id = %s", (course_id,))
                row = cursor.fetchone()
                cursor.close()
                return dict(row) if row and _is_sqlite(conn) else row
            except Exception as e:
                print(f"查询课堂记录失败: {e}")

        storage = load_local_storage()
        for r in storage.get('classroom_records', []):
            if r.get('course_id') == course_id:
                return r
        return None


def update_classroom_record(course_id: str, title: str) -> bool:
    """更新课堂标题"""
    init_classroom_tables()  # 确保表已创建
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("""
                        UPDATE classroom_records SET title = ?,
                            updated_at = datetime('now','localtime')
                        WHERE course_id = ?
                    """, (title, course_id))
                else:
                    cursor.execute("""
                        UPDATE classroom_records SET title = %s
                        WHERE course_id = %s
                    """, (title, course_id))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"更新课堂记录失败: {e}")

        storage = load_local_storage()
        for r in storage.get('classroom_records', []):
            if r.get('course_id') == course_id:
                r['title'] = title
                r['updated_at'] = 'local'
                save_local_storage(storage)
                return True
        return False


def delete_classroom_record(course_id: str) -> bool:
    """删除课堂记录"""
    init_classroom_tables()  # 确保表已创建
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("DELETE FROM classroom_records WHERE course_id = ?", (course_id,))
                else:
                    cursor.execute("DELETE FROM classroom_records WHERE course_id = %s", (course_id,))
                conn.commit()
                affected = cursor.rowcount
                cursor.close()
                return affected > 0
            except Exception as e:
                print(f"删除课堂记录失败: {e}")

        storage = load_local_storage()
        original_len = len(storage.get('classroom_records', []))
        storage['classroom_records'] = [
            r for r in storage.get('classroom_records', [])
            if r.get('course_id') != course_id
        ]
        save_local_storage(storage)
        return len(storage['classroom_records']) < original_len


# ============================================================
# 辅助函数
# ============================================================

def _is_sqlite(conn):
    """判断当前连接是否为 SQLite"""
    try:
        import sqlite3
        return isinstance(conn, sqlite3.Connection)
    except ImportError:
        return False


def _is_mysql(conn):
    """判断当前连接是否为 MySQL"""
    try:
        import pymysql
        return isinstance(conn, pymysql.connections.Connection)
    except ImportError:
        return False


def get_backend_name():
    """返回当前使用的后端名称"""
    return _detect_backend()


# ============================================================
# 视频课程库相关表
# ============================================================

def _get_video_cursor(conn):
    if _is_sqlite(conn):
        return conn.cursor()
    else:
        import pymysql
        return conn.cursor(pymysql.cursors.DictCursor)


def init_video_tables():
    with get_db() as conn:
        if conn is None:
            return
        try:
            cursor = _get_video_cursor(conn)
            if _is_sqlite(conn):
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS video_courses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        subtitle TEXT DEFAULT '',
                        source_type TEXT NOT NULL DEFAULT 'bilibili',
                        bvid TEXT DEFAULT '',
                        page INTEGER DEFAULT 1,
                        local_path TEXT DEFAULT '',
                        duration_label TEXT DEFAULT '--:--',
                        ai_summary TEXT DEFAULT '',
                        ai_timeline TEXT DEFAULT '[]',
                        ai_questions TEXT DEFAULT '[]',
                        ai_suggestion TEXT DEFAULT '',
                        created_by TEXT DEFAULT '',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS video_playlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL DEFAULT '默认列表',
                        position INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS playlist_videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        playlist_id INTEGER NOT NULL,
                        course_id INTEGER NOT NULL,
                        position INTEGER DEFAULT 0,
                        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS video_courses (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(256) NOT NULL,
                        subtitle VARCHAR(512) DEFAULT '',
                        source_type VARCHAR(16) NOT NULL DEFAULT 'bilibili',
                        bvid VARCHAR(32) DEFAULT '',
                        page INT DEFAULT 1,
                        local_path VARCHAR(512) DEFAULT '',
                        duration_label VARCHAR(16) DEFAULT '--:--',
                        ai_summary TEXT,
                        ai_timeline JSON,
                        ai_questions JSON,
                        ai_suggestion TEXT,
                        created_by VARCHAR(64) DEFAULT '',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS video_playlists (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(64) NOT NULL,
                        name VARCHAR(128) NOT NULL DEFAULT '默认列表',
                        position INT DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS playlist_videos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        playlist_id INT NOT NULL,
                        course_id INT NOT NULL,
                        position INT DEFAULT 0,
                        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f"初始化视频表失败: {e}")


def get_all_video_courses(source_type=None):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                if _is_sqlite(conn):
                    if source_type:
                        cursor.execute("SELECT * FROM video_courses WHERE source_type = ? ORDER BY id DESC", (source_type,))
                    else:
                        cursor.execute("SELECT * FROM video_courses ORDER BY id DESC")
                    rows = cursor.fetchall()
                    cursor.close()
                    return [dict(r) for r in rows]
                else:
                    if source_type:
                        cursor.execute("SELECT * FROM video_courses WHERE source_type = %s ORDER BY id DESC", (source_type,))
                    else:
                        cursor.execute("SELECT * FROM video_courses ORDER BY id DESC")
                    rows = cursor.fetchall()
                    cursor.close()
                    return [dict(r) for r in rows]
            except Exception as e:
                print(f"查询视频课程失败: {e}")
                return []
        storage = load_local_storage()
        courses = storage.get('video_courses', [])
        if source_type:
            courses = [c for c in courses if c.get('source_type') == source_type]
        return sorted(courses, key=lambda c: c.get('id', 0), reverse=True)


def get_video_course(course_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                if _is_sqlite(conn):
                    cursor.execute("SELECT * FROM video_courses WHERE id = ?", (course_id,))
                else:
                    cursor.execute("SELECT * FROM video_courses WHERE id = %s", (course_id,))
                row = cursor.fetchone()
                cursor.close()
                return dict(row) if row else None
            except Exception as e:
                print(f"查询视频课程失败: {e}")
                return None
        storage = load_local_storage()
        for c in storage.get('video_courses', []):
            if c.get('id') == course_id:
                return c
        return None


def create_video_course(title, source_type='bilibili', subtitle='', bvid='', page=1,
                        local_path='', duration_label='--:--', ai_summary='',
                        ai_timeline='[]', ai_questions='[]', ai_suggestion='', created_by=''):
    import json as _json
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                if _is_sqlite(conn):
                    cursor.execute("""
                        INSERT INTO video_courses (title, subtitle, source_type, bvid, page,
                            local_path, duration_label, ai_summary, ai_timeline, ai_questions,
                            ai_suggestion, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (title, subtitle, source_type, bvid, page, local_path, duration_label,
                          ai_summary, ai_timeline, ai_questions, ai_suggestion, created_by))
                else:
                    cursor.execute("""
                        INSERT INTO video_courses (title, subtitle, source_type, bvid, page,
                            local_path, duration_label, ai_summary, ai_timeline, ai_questions,
                            ai_suggestion, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (title, subtitle, source_type, bvid, page, local_path, duration_label,
                          ai_summary if isinstance(ai_summary, str) else _json.dumps(ai_summary or ''),
                          ai_timeline if isinstance(ai_timeline, str) else _json.dumps(ai_timeline or '[]'),
                          ai_questions if isinstance(ai_questions, str) else _json.dumps(ai_questions or '[]'),
                          ai_suggestion, created_by))
                conn.commit()
                course_id = cursor.lastrowid
                cursor.close()
                return course_id
            except Exception as e:
                print(f"创建视频课程失败: {e}")
                return None
        storage = load_local_storage()
        courses = storage.get('video_courses', [])
        new_id = max([c.get('id', 0) for c in courses], default=0) + 1
        course = {
            'id': new_id, 'title': title, 'subtitle': subtitle, 'source_type': source_type,
            'bvid': bvid, 'page': page, 'local_path': local_path, 'duration_label': duration_label,
            'ai_summary': ai_summary, 'ai_timeline': ai_timeline, 'ai_questions': ai_questions,
            'ai_suggestion': ai_suggestion, 'created_by': created_by, 'created_at': ''
        }
        courses.append(course)
        storage['video_courses'] = courses
        save_local_storage(storage)
        return new_id


def delete_video_course(course_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                if _is_sqlite(conn):
                    cursor.execute("DELETE FROM video_courses WHERE id = ?", (course_id,))
                else:
                    cursor.execute("DELETE FROM video_courses WHERE id = %s", (course_id,))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"删除视频课程失败: {e}")
                return False
        storage = load_local_storage()
        storage['video_courses'] = [c for c in storage.get('video_courses', []) if c.get('id') != course_id]
        save_local_storage(storage)
        return True


def update_video_course(course_id, **kwargs):
    if not kwargs:
        return False
    valid_keys = ('title', 'subtitle', 'source_type', 'bvid', 'page', 'local_path',
                  'duration_label', 'ai_summary', 'ai_timeline', 'ai_questions', 'ai_suggestion')
    filtered = {k: v for k, v in kwargs.items() if k in valid_keys}
    if not filtered:
        return False
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                sqlite = _is_sqlite(conn)
                placeholders = ', '.join(f"{k} = {'?' if sqlite else '%s'}" for k in filtered)
                sql = f"UPDATE video_courses SET {placeholders} WHERE id = {'?' if sqlite else '%s'}"
                vals = list(filtered.values()) + [course_id]
                cursor.execute(sql, vals)
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"更新视频课程失败: {e}")
                return False
        storage = load_local_storage()
        for c in storage.get('video_courses', []):
            if c.get('id') == course_id:
                c.update(filtered)
                save_local_storage(storage)
                return True
        return False


def get_user_playlists(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                if _is_sqlite(conn):
                    cursor.execute("SELECT * FROM video_playlists WHERE user_id = ? ORDER BY position, id", (user_id,))
                else:
                    cursor.execute("SELECT * FROM video_playlists WHERE user_id = %s ORDER BY position, id", (user_id,))
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    pl = dict(row)
                    join_sql = "SELECT pv.*, vc.title, vc.subtitle, vc.source_type, vc.bvid, vc.page, vc.local_path, vc.duration_label, vc.ai_summary, vc.ai_timeline, vc.ai_questions, vc.ai_suggestion FROM playlist_videos pv JOIN video_courses vc ON pv.course_id = vc.id WHERE pv.playlist_id = " + ("?" if _is_sqlite(conn) else "%s") + " ORDER BY pv.position, pv.id"
                    cursor.execute(join_sql, (pl['id'],))
                    vrows = cursor.fetchall()
                    pl['videos'] = [dict(vr) for vr in vrows]
                    results.append(pl)
                cursor.close()
                return results
            except Exception as e:
                print(f"查询播放列表失败: {e}")
                return []
        storage = load_local_storage()
        playlists = [p for p in storage.get('video_playlists', []) if p.get('user_id') == user_id]
        all_items = storage.get('playlist_videos', [])
        all_courses = {c['id']: c for c in storage.get('video_courses', [])}
        for pl in playlists:
            items = [i for i in all_items if i.get('playlist_id') == pl['id']]
            for item in items:
                course = all_courses.get(item.get('course_id'))
                if course:
                    item.update({k: course[k] for k in ('title', 'subtitle', 'source_type', 'bvid', 'page', 'local_path', 'duration_label', 'ai_summary', 'ai_timeline', 'ai_questions', 'ai_suggestion') if k in course})
            pl['videos'] = sorted(items, key=lambda i: i.get('position', 0))
        return sorted(playlists, key=lambda p: p.get('position', 0))


def create_playlist(user_id, name='默认列表'):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                if _is_sqlite(conn):
                    cursor.execute("INSERT INTO video_playlists (user_id, name) VALUES (?, ?)", (user_id, name))
                else:
                    cursor.execute("INSERT INTO video_playlists (user_id, name) VALUES (%s, %s)", (user_id, name))
                conn.commit()
                pl_id = cursor.lastrowid
                cursor.close()
                return pl_id
            except Exception as e:
                print(f"创建播放列表失败: {e}")
                return None
        storage = load_local_storage()
        playlists = storage.get('video_playlists', [])
        new_id = max([p.get('id', 0) for p in playlists], default=0) + 1
        pl = {'id': new_id, 'user_id': user_id, 'name': name, 'position': 0, 'created_at': ''}
        playlists.append(pl)
        storage['video_playlists'] = playlists
        save_local_storage(storage)
        return new_id


def delete_playlist(playlist_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                if _is_sqlite(conn):
                    cursor.execute("DELETE FROM playlist_videos WHERE playlist_id = ?", (playlist_id,))
                    cursor.execute("DELETE FROM video_playlists WHERE id = ?", (playlist_id,))
                else:
                    cursor.execute("DELETE FROM playlist_videos WHERE playlist_id = %s", (playlist_id,))
                    cursor.execute("DELETE FROM video_playlists WHERE id = %s", (playlist_id,))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"删除播放列表失败: {e}")
                return False
        storage = load_local_storage()
        storage['playlist_videos'] = [i for i in storage.get('playlist_videos', []) if i.get('playlist_id') != playlist_id]
        storage['video_playlists'] = [p for p in storage.get('video_playlists', []) if p.get('id') != playlist_id]
        save_local_storage(storage)
        return True


def rename_playlist(playlist_id, name):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                if _is_sqlite(conn):
                    cursor.execute("UPDATE video_playlists SET name = ? WHERE id = ?", (name, playlist_id))
                else:
                    cursor.execute("UPDATE video_playlists SET name = %s WHERE id = %s", (name, playlist_id))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"重命名播放列表失败: {e}")
                return False
        storage = load_local_storage()
        for p in storage.get('video_playlists', []):
            if p.get('id') == playlist_id:
                p['name'] = name
                save_local_storage(storage)
                return True
        return False


def add_video_to_playlist(playlist_id, course_id, position=None):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                if position is None:
                    if _is_sqlite(conn):
                        cursor.execute("SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM playlist_videos WHERE playlist_id = ?", (playlist_id,))
                    else:
                        cursor.execute("SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM playlist_videos WHERE playlist_id = %s", (playlist_id,))
                    row = cursor.fetchone()
                    position = row['next_pos'] if row else 0
                if _is_sqlite(conn):
                    cursor.execute("INSERT INTO playlist_videos (playlist_id, course_id, position) VALUES (?, ?, ?)", (playlist_id, course_id, position))
                else:
                    cursor.execute("INSERT INTO playlist_videos (playlist_id, course_id, position) VALUES (%s, %s, %s)", (playlist_id, course_id, position))
                conn.commit()
                pv_id = cursor.lastrowid
                cursor.close()
                return pv_id
            except Exception as e:
                print(f"添加视频到列表失败: {e}")
                return None
        storage = load_local_storage()
        items = storage.get('playlist_videos', [])
        new_id = max([i.get('id', 0) for i in items], default=0) + 1
        if position is None:
            existing = [i for i in items if i.get('playlist_id') == playlist_id]
            position = max([i.get('position', 0) for i in existing], default=-1) + 1
        item = {'id': new_id, 'playlist_id': playlist_id, 'course_id': course_id, 'position': position, 'added_at': ''}
        items.append(item)
        storage['playlist_videos'] = items
        save_local_storage(storage)
        return new_id


def remove_video_from_playlist(pv_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                if _is_sqlite(conn):
                    cursor.execute("DELETE FROM playlist_videos WHERE id = ?", (pv_id,))
                else:
                    cursor.execute("DELETE FROM playlist_videos WHERE id = %s", (pv_id,))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"移除列表视频失败: {e}")
                return False
        storage = load_local_storage()
        storage['playlist_videos'] = [i for i in storage.get('playlist_videos', []) if i.get('id') != pv_id]
        save_local_storage(storage)
        return True


def reorder_playlist_videos(items):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = _get_video_cursor(conn)
                for item in items:
                    if _is_sqlite(conn):
                        cursor.execute("UPDATE playlist_videos SET position = ? WHERE id = ?", (item['position'], item['id']))
                    else:
                        cursor.execute("UPDATE playlist_videos SET position = %s WHERE id = %s", (item['position'], item['id']))
                conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"排序失败: {e}")
                return False
        storage = load_local_storage()
        for item in items:
            for i in storage.get('playlist_videos', []):
                if i.get('id') == item['id']:
                    i['position'] = item['position']
        save_local_storage(storage)
        return True


def get_user_theme_prefs(user_id):
    """Retrieve user theme preferences as a dict, or None if not found."""
    with get_db() as conn:
        if conn is None:
            return None
        ensure_theme_prefs_column(conn)
        if _is_sqlite(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT theme_prefs FROM user WHERE id = ?", (user_id,))
        else:
            import pymysql
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT theme_prefs FROM user WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            prefs = row[0] if _is_sqlite(conn) else row.get('theme_prefs')
            if prefs:
                if isinstance(prefs, str):
                    try:
                        return json.loads(prefs)
                    except:
                        return None
                return prefs
        return None


def save_user_theme_prefs(user_id, prefs_dict):
    """Persist user theme preferences dict to database."""
    prefs_json = json.dumps(prefs_dict, ensure_ascii=False)
    with get_db() as conn:
        if conn is None:
            return False
        ensure_theme_prefs_column(conn)
        cursor = conn.cursor()
        if _is_sqlite(conn):
            cursor.execute("UPDATE user SET theme_prefs = ? WHERE id = ?", (prefs_json, user_id))
        else:
            cursor.execute("UPDATE user SET theme_prefs = %s WHERE id = %s", (prefs_json, user_id))
        conn.commit()
        cursor.close()
        return True


# 自动初始化视频表
try:
    init_video_tables()
except Exception:
    pass
