import json
import os
from contextlib import contextmanager
from datetime import datetime

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
# 学习路径
# ============================================================

def get_learning_path(user_id):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute("SELECT * FROM learning_path WHERE user_id = ?", (user_id,))
                else:
                    import pymysql
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                    cursor.execute("SELECT * FROM learning_path WHERE user_id = %s", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                return dict(row) if row and _is_sqlite(conn) else row
            except Exception as e:
                print(f"数据库查询失败: {e}")

        return _get_json_record(load_local_storage(), 'learning_paths', user_id)


def save_learning_path(user_id, path_json):
    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    cursor.execute(
                        """INSERT INTO learning_path (user_id, path_json) VALUES (?, ?)
                           ON CONFLICT(user_id) DO UPDATE SET path_json=excluded.path_json""",
                        (user_id, path_json))
                else:
                    cursor.execute(
                        """INSERT INTO learning_path (user_id, path_json) VALUES (%s, %s)
                           ON DUPLICATE KEY UPDATE path_json=%s""",
                        (user_id, path_json, path_json))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")

        storage = load_local_storage()
        for path in storage.get('learning_paths', []):
            if path.get('user_id') == user_id:
                path['path_json'] = path_json
                save_local_storage(storage)
                return
        storage['learning_paths'].append({
            'id': len(storage.get('learning_paths', [])) + 1,
            'user_id': user_id, 'path_json': path_json, 'updated_at': 'local',
        })
        save_local_storage(storage)


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
