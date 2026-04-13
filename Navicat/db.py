import pymysql
from contextlib import contextmanager
import json
import os

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'xingshi',
    'charset': 'utf8mb4'
}

# 数据库连接状态
db_available = False

# 本地存储路径
LOCAL_STORAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'local_storage.json')

@contextmanager
def get_db():
    global db_available
    try:
        conn = pymysql.connect(**DB_CONFIG)
        db_available = True
        try:
            yield conn
        finally:
            conn.close()
    except Exception as e:
        db_available = False
        print(f"数据库连接失败: {e}")
        print("将使用本地存储模式")
        yield None

# 本地存储操作
def load_local_storage():
    if os.path.exists(LOCAL_STORAGE_PATH):
        try:
            with open(LOCAL_STORAGE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'users': [], 'learning_records': []}

def save_local_storage(data):
    try:
        with open(LOCAL_STORAGE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存本地存储失败: {e}")

def get_user_by_username(username):
    with get_db() as conn:
        if conn:
            try:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
                user = cursor.fetchone()
                cursor.close()
                return user
            except Exception as e:
                print(f"数据库查询失败: {e}")
        # 降级到本地存储
        storage = load_local_storage()
        for user in storage.get('users', []):
            if user.get('username') == username:
                return user
        return None

def create_user(username, hashed_password, avatar=''):
    with get_db() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO user (username, password, avatar) VALUES (%s, %s, %s)",
                    (username, hashed_password, avatar)
                )
                conn.commit()
                user_id = cursor.lastrowid
                cursor.close()
                return user_id
            except Exception as e:
                print(f"数据库插入失败: {e}")
        # 降级到本地存储
        storage = load_local_storage()
        user_id = len(storage.get('users', [])) + 1
        new_user = {
            'id': user_id,
            'username': username,
            'password': hashed_password,
            'avatar': avatar,
            'current_task': '大数据导论',
            'created_at': 'local',
            'last_login': 'local'
        }
        storage['users'] = storage.get('users', []) + [new_user]
        save_local_storage(storage)
        return user_id

def update_user_avatar(user_id, avatar):
    with get_db() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE user SET avatar = %s WHERE id = %s", (avatar, user_id))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库更新失败: {e}")
        # 降级到本地存储
        storage = load_local_storage()
        for user in storage.get('users', []):
            if user.get('id') == user_id:
                user['avatar'] = avatar
                save_local_storage(storage)
                break

def update_user_task(user_id, task):
    with get_db() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                # 检查user表是否有current_task字段，如果没有则添加
                cursor.execute("SHOW COLUMNS FROM user LIKE 'current_task'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE user ADD COLUMN current_task VARCHAR(100) DEFAULT '大数据导论'")
                cursor.execute("UPDATE user SET current_task = %s WHERE id = %s", (task, user_id))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库更新失败: {e}")
        # 降级到本地存储
        storage = load_local_storage()
        for user in storage.get('users', []):
            if user.get('id') == user_id:
                user['current_task'] = task
                save_local_storage(storage)
                break

def update_last_login(user_id):
    with get_db() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                # 检查user表是否有last_login字段，如果没有则添加
                cursor.execute("SHOW COLUMNS FROM user LIKE 'last_login'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE user ADD COLUMN last_login TIMESTAMP NULL DEFAULT NULL")
                cursor.execute("UPDATE user SET last_login = NOW() WHERE id = %s", (user_id,))
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库更新失败: {e}")
        # 降级到本地存储
        storage = load_local_storage()
        for user in storage.get('users', []):
            if user.get('id') == user_id:
                user['last_login'] = 'local'
                save_local_storage(storage)
                break

def get_learning_record(user_id):
    with get_db() as conn:
        if conn:
            try:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT * FROM learning_records WHERE user_id = %s", (user_id,))
                record = cursor.fetchone()
                cursor.close()
                return record
            except Exception as e:
                print(f"数据库查询失败: {e}")
        # 降级到本地存储
        storage = load_local_storage()
        for record in storage.get('learning_records', []):
            if record.get('user_id') == user_id:
                return record
        return None

def save_learning_record(user_id, interaction_count, code_practice_time, socratic_pass_rate, difficulty_level, profile_json):
    with get_db() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO learning_records (user_id, interaction_count, code_practice_time, socratic_pass_rate, difficulty_level, profile_json)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                       interaction_count=%s, code_practice_time=%s, socratic_pass_rate=%s, difficulty_level=%s, profile_json=%s""",
                    (user_id, interaction_count, code_practice_time, socratic_pass_rate, difficulty_level, profile_json,
                     interaction_count, code_practice_time, socratic_pass_rate, difficulty_level, profile_json)
                )
                conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"数据库保存失败: {e}")
        # 降级到本地存储
        storage = load_local_storage()
        record_exists = False
        for record in storage.get('learning_records', []):
            if record.get('user_id') == user_id:
                record['interaction_count'] = interaction_count
                record['code_practice_time'] = code_practice_time
                record['socratic_pass_rate'] = socratic_pass_rate
                record['difficulty_level'] = difficulty_level
                record['profile_json'] = profile_json
                record_exists = True
                break
        if not record_exists:
            new_record = {
                'id': len(storage.get('learning_records', [])) + 1,
                'user_id': user_id,
                'interaction_count': interaction_count,
                'code_practice_time': code_practice_time,
                'socratic_pass_rate': socratic_pass_rate,
                'difficulty_level': difficulty_level,
                'profile_json': profile_json,
                'updated_at': 'local'
            }
            storage['learning_records'] = storage.get('learning_records', []) + [new_record]
        save_local_storage(storage)
