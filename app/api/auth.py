"""
Auth API — 用户认证 (登录/注册/获取当前用户)

POST /api/auth/login    — 登录，返回 JWT token + 用户信息
POST /api/auth/register — 注册新用户
GET  /api/auth/me       — 获取当前用户信息（需 Bearer token）
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db import get_db, _is_sqlite, load_local_storage, save_local_storage
from app.core.repository_factory import get_repository_for_user
from app.core.rate_limiter import login_rate_limit, register_rate_limit

logger = logging.getLogger("starlearn.auth")

router = APIRouter(prefix="/api/auth")

# JWT 密钥 — 生产环境应通过环境变量配置
JWT_SECRET = os.environ.get("JWT_SECRET", "starlearn-jwt-secret-key-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72


# ── 密码工具（导入 main.py 中的函数可能导致循环引用，这里内联一份） ──

def _hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')


def _verify_password(password: str, hashed: str) -> bool:
    import bcrypt
    import hashlib
    if hashed.startswith('$2b$') or hashed.startswith('$2a$'):
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    if len(hashed) == 64 and all(c in '0123456789abcdef' for c in hashed):
        return hashlib.sha256(password.encode('utf-8')).hexdigest() == hashed
    return False


# ── 数据库 schema 兼容 ──

def _ensure_user_table():
    """确保 user 表存在（含 role 和 display_name），不存在则创建。"""
    with get_db() as conn:
        if conn is None:
            return
        try:
            cursor = conn.cursor()
            if _is_sqlite(conn):
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        nickname TEXT DEFAULT '',
                        avatar TEXT DEFAULT '',
                        role TEXT DEFAULT 'student',
                        display_name TEXT DEFAULT '',
                        current_task TEXT DEFAULT '大数据导论',
                        preferred_language TEXT DEFAULT 'python',
                        theme TEXT DEFAULT 'ocean',
                        last_agent_id TEXT DEFAULT '',
                        last_login TIMESTAMP NULL DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) NOT NULL UNIQUE,
                        password VARCHAR(255) NOT NULL,
                        nickname VARCHAR(50) DEFAULT '',
                        avatar VARCHAR(500) DEFAULT '',
                        role VARCHAR(20) DEFAULT 'student',
                        display_name VARCHAR(100) DEFAULT '',
                        current_task VARCHAR(100) DEFAULT '大数据导论',
                        preferred_language VARCHAR(20) DEFAULT 'python',
                        theme VARCHAR(50) DEFAULT 'ocean',
                        last_agent_id VARCHAR(50) DEFAULT '',
                        last_login TIMESTAMP NULL DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
            conn.commit()
            cursor.close()
        except Exception as e:
            logger.warning(f"创建 user 表失败（可能已存在）: {e}")

    # 兼容旧表（无 role/display_name 列时补齐）
    _ensure_user_columns()


def _ensure_user_columns():
    """确保 user 表有 role 和 display_name 列（向前兼容旧表）。"""
    with get_db() as conn:
        if conn is None:
            return
        try:
            cursor = conn.cursor()
            if _is_sqlite(conn):
                cursor.execute("PRAGMA table_info(user)")
                columns = {row[1] for row in cursor.fetchall()}
                if 'role' not in columns:
                    cursor.execute("ALTER TABLE user ADD COLUMN role TEXT DEFAULT 'student'")
                if 'display_name' not in columns:
                    cursor.execute("ALTER TABLE user ADD COLUMN display_name TEXT DEFAULT ''")
            else:
                cursor.execute("SHOW COLUMNS FROM user LIKE 'role'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'student'")
                cursor.execute("SHOW COLUMNS FROM user LIKE 'display_name'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE user ADD COLUMN display_name VARCHAR(100) DEFAULT ''")
            conn.commit()
            cursor.close()
        except Exception as e:
            logger.warning(f"确保 user 列失败（可能已存在）: {e}")


DEMO_ACCOUNTS = ("teacher", "student", "admin")

ALLOW_DEMO_LOGIN = os.environ.get("ALLOW_DEMO_LOGIN", "false").lower() in ("true", "1", "yes")


def _ensure_demo_accounts():
    """确保演示账号存在（teacher/student/admin，密码均为 123456）。

    仅当 ALLOW_DEMO_LOGIN=true 时才创建。生产环境默认 false,模块加载时
    不会自动注入 teacher/student/admin (123456) 账号;前端"演示账号登录"
    按钮调用 /api/auth/demo-login 时再触发创建。
    """
    if not ALLOW_DEMO_LOGIN:
        return
    _ensure_user_table()
    demo_users = [
        ("teacher", "教师演示", "teacher"),
        ("student", "学生演示", "student"),
        ("admin", "管理员", "admin"),
    ]
    for username, display_name, role in demo_users:
        repo = get_repository_for_user(username, repository_type="user")
        existing = repo.get_by_username(username)
        if existing:
            continue
        hashed = _hash_password("123456")
        with get_db() as conn:
            if conn is not None:
                try:
                    cursor = conn.cursor()
                    if _is_sqlite(conn):
                        sql = """INSERT INTO user (username, password, avatar, nickname, role, display_name)
                                 VALUES (?, ?, ?, ?, ?, ?)"""
                    else:
                        sql = """INSERT INTO user (username, password, avatar, nickname, role, display_name)
                                 VALUES (%s, %s, %s, %s, %s, %s)"""
                    cursor.execute(sql, (username, hashed, "", display_name, role, display_name))
                    conn.commit()
                    cursor.close()
                    logger.info(f"演示账号已创建: {username}")
                except Exception as e:
                    logger.warning(f"创建演示账号失败 ({username}): {e}")
                    continue

            # JSON fallback
            storage = load_local_storage()
            user_id = len(storage.get('users', [])) + 1
            new_user = {
                'id': user_id, 'username': username, 'password': hashed,
                'avatar': '', 'nickname': display_name, 'role': role,
                'display_name': display_name, 'created_at': 'local', 'last_login': 'local',
            }
            storage['users'] = storage.get('users', []) + [new_user]
            save_local_storage(storage)


# 模块加载时自动确保演示账号存在
try:
    _ensure_demo_accounts()
except Exception as e:
    logger.warning(f"初始化演示账号失败: {e}")


# ── 请求 / 响应模型 ──

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    confirmPassword: str = ""
    display_name: str = ""
    role: str = "teacher"


class UserInfo(BaseModel):
    id: int
    username: str
    role: str = "student"
    display_name: str = ""
    avatar: str = ""
    nickname: str = ""


# ── JWT 工具 ──

def create_jwt(user: dict) -> str:
    """为用户生成 JWT token。"""
    now = datetime.utcnow()
    payload = {
        "uid": user.get("id"),
        "username": user.get("username"),
        "role": user.get("role", "student"),
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """解析 JWT token，无效则抛出异常。"""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def _user_to_response(user: dict) -> dict:
    """将数据库用户字典转为 API 响应格式。"""
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "role": user.get("role", "student"),
        "display_name": user.get("display_name") or user.get("nickname") or user.get("username", ""),
        "avatar": user.get("avatar", ""),
        "nickname": user.get("nickname", ""),
    }


# ── 路由 ──

def login(body: LoginRequest):
    """用户登录，返回 JWT token 和用户信息。"""
    _ensure_user_table()

    repo = get_repository_for_user(body.username, repository_type="user")
    user = repo.get_by_username(body.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    hashed = user.get("password", "")
    if not _verify_password(body.password, hashed):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_jwt(user)
    return {
        "token": token,
        "user": _user_to_response(user),
    }


@router.post("/login")
@login_rate_limit()
def login_route(request: Request, body: LoginRequest):
    """Rate-limited route entry; delegates to ``login``."""
    return login(body)


@router.post("/demo-login")
def demo_login(role: str = "student"):
    """登录演示账号 (teacher / student / admin)。

    仅当 ALLOW_DEMO_LOGIN=true 时启用 (生产默认 false)。
    账号不存在则自动创建 (密码 123456),然后签发 JWT。
    前端"演示账号登录"按钮调用此端点。
    """
    if not ALLOW_DEMO_LOGIN:
        raise HTTPException(
            status_code=403,
            detail="演示账号登录已禁用 (生产环境默认关闭,需 ALLOW_DEMO_LOGIN=true 启用)",
        )
    if role not in DEMO_ACCOUNTS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的演示角色,允许: {', '.join(DEMO_ACCOUNTS)}",
        )

    # 调用原版函数 (内部已用 ALLOW_DEMO_LOGIN gate,这里直接用)
    _ensure_demo_accounts()
    repo = get_repository_for_user(role, repository_type="user")
    user = repo.get_by_username(role)
    if not user:
        raise HTTPException(status_code=500, detail="演示账号创建失败")

    token = create_jwt(user)
    return {
        "token": token,
        "user": _user_to_response(user),
        "isDemo": True,
    }


def register(body: RegisterRequest):
    """注册新用户。"""
    _ensure_user_table()

    # 验证输入
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")
    if body.confirmPassword and body.password != body.confirmPassword:
        raise HTTPException(status_code=400, detail="两次密码输入不一致")
    if body.role not in ("teacher", "student", "admin"):
        raise HTTPException(status_code=400, detail="无效的角色")

    # 检查用户名是否已存在
    repo = get_repository_for_user(body.username, repository_type="user")
    existing = repo.get_by_username(body.username)
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")

    hashed = _hash_password(body.password)
    display_name = body.display_name or body.username

    with get_db() as conn:
        if conn is not None:
            try:
                cursor = conn.cursor()
                if _is_sqlite(conn):
                    sql = """INSERT INTO user (username, password, avatar, nickname, role, display_name)
                             VALUES (?, ?, ?, ?, ?, ?)"""
                else:
                    sql = """INSERT INTO user (username, password, avatar, nickname, role, display_name)
                             VALUES (%s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (body.username, hashed, "", display_name, body.role, display_name))
                conn.commit()
                user_id = cursor.lastrowid
                cursor.close()
                return {"success": True, "id": user_id}
            except Exception as e:
                logger.error(f"数据库插入失败: {e}")
                raise HTTPException(status_code=500, detail=f"注册失败: {e}")

        # JSON fallback
        storage = load_local_storage()
        user_id = len(storage.get('users', [])) + 1
        new_user = {
            'id': user_id, 'username': body.username, 'password': hashed,
            'avatar': '', 'nickname': display_name, 'role': body.role,
            'display_name': display_name, 'created_at': 'local', 'last_login': 'local',
        }
        storage['users'] = storage.get('users', []) + [new_user]
        save_local_storage(storage)
        return {"success": True, "id": user_id}


@router.post("/register")
@register_rate_limit()
def register_route(request: Request, body: RegisterRequest):
    """Rate-limited route entry; delegates to ``register``."""
    return register(body)


@router.get("/me")
def get_me(request: Request):
    """获取当前登录用户信息（需 Bearer token）。"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    token = auth_header[7:]  # 去掉 "Bearer " 前缀
    try:
        payload = decode_jwt(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="令牌已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的认证令牌")

    user_id = payload.get("uid")
    username = payload.get("username")

    if not user_id and not username:
        raise HTTPException(status_code=401, detail="令牌数据无效")

    # 从数据库获取最新用户信息
    if username:
        repo = get_repository_for_user(username, repository_type="user")
        user = repo.get_by_username(username)
    else:
        user = None

    if not user:
        # 令牌有效但数据库中没有用户 — 返回令牌中的信息
        return {
            "user": {
                "id": user_id,
                "username": username,
                "role": payload.get("role", "student"),
                "display_name": username,
                "avatar": "",
            }
        }

    return {"user": _user_to_response(user)}
