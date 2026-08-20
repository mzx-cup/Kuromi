"""Legacy 仓库共享连接助手：跟随 db.py 的生效后端（无跨引擎降级）。

背景（split-brain 修复）：legacy 仓库原本各自 ``sqlite3.connect(db.SQLITE_PATH)``
直连 SQLite，而 db.py 写路径在 auto 探测下可能选中 MySQL —— 同一功能的
读和写落进两个引擎，表现为"数据查找不到"。本模块提供统一入口：

- ``legacy_conn(db_path)``：layer-1 连接。显式传 ``db_path``（测试隔离用
  临时 SQLite 文件）则直连该文件；否则打开**生效后端**连接（MySQL /
  SQLite，由 ``STARLEARN_DB_BACKEND`` 决定），连不上抛
  ``db.BackendUnavailable``，不再静默换引擎。
- ``orm_conn(db_path)``：ORM(v2) 层连接。course_progress / learning_paths /
  user_evaluations / course_deadlines 这些表由 ORM ``create_all`` 创建、
  ORM 写路径写入，"数据家"在 ``DATABASE_URL`` 指向的库（默认
  xingshi_v2.db）—— 读取它们必须连同一个库，而不是 layer-1。

方言工具（SQLite ``?`` vs MySQL ``%s`` 等）：
- ``is_sqlite(conn)`` / ``ph(conn)`` / ``ph_list(conn, n)``
- ``upsert_sql(conn, table, columns, conflict_cols, update_cols)``
- ``date_today(conn)`` / ``date_days_ago(conn, n)`` / ``date_days_ahead(conn, n)``
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from urllib.parse import urlsplit

import db


# ── 方言判断与占位符 ──


def is_sqlite(conn) -> bool:
    """连接是否为 SQLite（MySQL 连接返回 False）。"""
    return isinstance(conn, sqlite3.Connection)


def ph(conn) -> str:
    """SQL 占位符：SQLite ``?`` / MySQL ``%s``。"""
    return '?' if is_sqlite(conn) else '%s'


def ph_list(conn, n: int) -> str:
    """``n`` 个占位符的逗号串。"""
    return ', '.join([ph(conn)] * n)


def upsert_sql(conn, table: str, columns, conflict_cols, update_cols) -> str:
    """按方言生成 upsert 语句。

    - SQLite: ``INSERT ... ON CONFLICT(cols) DO UPDATE SET x=excluded.x``
    - MySQL:  ``INSERT ... ON DUPLICATE KEY UPDATE x=VALUES(x)``
      （不指名冲突列，依赖 PRIMARY KEY / UNIQUE 索引；``conflict_cols``
      仅用于 SQLite 分支）
    """
    base = (
        f'INSERT INTO {table} ({", ".join(columns)}) '
        f'VALUES ({ph_list(conn, len(columns))})'
    )
    if is_sqlite(conn):
        upd = ', '.join(f'{c} = excluded.{c}' for c in update_cols)
        return f'{base} ON CONFLICT({", ".join(conflict_cols)}) DO UPDATE SET {upd}'
    upd = ', '.join(f'{c} = VALUES({c})' for c in update_cols)
    return f'{base} ON DUPLICATE KEY UPDATE {upd}'


# ── 日期表达式 ──


def date_today(conn) -> str:
    """"今天" 的日期表达式（用于 ``<=`` / ``>=`` 比较）。"""
    return "date('now')" if is_sqlite(conn) else 'CURDATE()'


def date_days_ago(conn, days: int) -> str:
    """"N 天前" 的日期表达式。"""
    if is_sqlite(conn):
        return f"date('now', '-{days} days')"
    return f'DATE_SUB(CURDATE(), INTERVAL {days} DAY)'


def date_days_ahead(conn, days: int) -> str:
    """"N 天后" 的日期表达式。"""
    if is_sqlite(conn):
        return f"date('now', '+{days} days')"
    return f'DATE_ADD(CURDATE(), INTERVAL {days} DAY)'


# ── 连接入口 ──


@contextmanager
def legacy_conn(db_path: str | None = None):
    """Layer-1 统一连接入口：跟随 db.py 生效后端（MySQL / SQLite）。

    显式传 ``db_path``（测试隔离）则直连该 SQLite 文件 —— 这是保留的
    唯一侧门；生产路径（``db_path=None``）一律走生效后端，连不上抛
    ``db.BackendUnavailable``。
    """
    if db_path is not None:
        conn = sqlite3.connect(db_path)
    else:
        conn = db.open_effective_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _sqlite_path_from_url(url: str) -> str:
    """从 SQLAlchemy URL 提取 SQLite 文件路径。

    ``sqlite+aiosqlite:///C:/proj/xingshi_v2.db`` → ``C:/proj/xingshi_v2.db``
    """
    rest = url.split('://', 1)[1] if '://' in url else url
    rest = rest.split('?', 1)[0]
    if rest.startswith('./'):
        rest = rest[2:]
    return rest


@contextmanager
def legacy_scope(db_path: str | None):
    """测试隔离缝：把 db.py 全局指向 ``db_path``（临时 SQLite 文件）。

    委托 db.py 正式函数的方法（preferences / gamification / chat 消息 /
    knowledge / classroom 测验读取）不经过 ``legacy_conn``，而是跟随
    db.py 的生效后端全局。测试传入 ``db_path`` 时，本上下文把
    ``db.SQLITE_PATH`` / ``db.DB_BACKEND`` / ``db._effective_backend``
    临时指到该文件，保证**直连 SQL 与委托调用落在同一个临时库** ——
    否则测试里"写进临时文件、读出生效后端"会假失败。

    生产路径 ``db_path=None`` → 完全 no-op，不改任何全局。
    """
    if db_path is None:
        yield
        return
    saved = (db.SQLITE_PATH, db.DB_BACKEND, db._effective_backend)
    db.SQLITE_PATH = db_path
    db.DB_BACKEND = 'sqlite'
    db._effective_backend = 'sqlite'
    try:
        yield
    finally:
        db.SQLITE_PATH, db.DB_BACKEND, db._effective_backend = saved


@contextmanager
def orm_conn(db_path: str | None = None):
    """ORM(v2) 层连接入口。

    ``course_progress`` / ``learning_paths`` / ``learning_path_nodes`` /
    ``user_evaluations`` / ``course_deadlines`` 表的家在 ORM 管理的库
    （默认 xingshi_v2.db，由 ``DATABASE_URL`` 决定），从 URL 推导同步
    连接；显式传 ``db_path`` 则直连（测试隔离）。
    """
    if db_path is not None:
        conn = sqlite3.connect(db_path)
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return

    from app.core.config import DATABASE_URL
    engine_base = DATABASE_URL.split(':', 1)[0].split('+')[0]

    if engine_base == 'sqlite':
        path = _sqlite_path_from_url(DATABASE_URL) or ':memory:'
        conn = sqlite3.connect(path)
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return

    # MySQL URL：mysql+pymysql://user:password@host:port/dbname
    import pymysql
    parts = urlsplit(DATABASE_URL)
    conn = pymysql.connect(
        host=parts.hostname or '127.0.0.1',
        port=parts.port or 3306,
        user=parts.username or 'root',
        password=parts.password or '',
        database=parts.path.lstrip('/'),
        charset='utf8mb4',
    )
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass
