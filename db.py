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
                        (user_id, profile_json, evaluation_json, grade_str))
                else:
                    cursor.execute(
                        """INSERT INTO user_profile (user_id, profile_json, evaluation_json, last_grade_record)
                           VALUES (%s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                               profile_json=%s, evaluation_json=%s, last_grade_record=%s""",
                        (user_id, profile_json, evaluation_json, grade_str,
                         profile_json, evaluation_json, grade_str))
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
