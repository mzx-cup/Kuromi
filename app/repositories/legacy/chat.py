"""db.py wrapper for chat messages, summaries, agent turns, and memories.

Provides read/write methods against the db.py tables
``messages``, ``conversation_summaries``, ``agent_turn_records`` and
``user_memories``. Mirrors
:class:`app.repositories.orm.chat.SqlAlchemyChatRepository` so callers
can swap implementations behind the
:class:`app.repositories.base.ChatRepository` Protocol.

设计要点：
  - ``messages``: 直接 SQLite 连接,因为生产 MySQL 上的 messages 表用的是
    ``msg_metadata`` 列名(不是 ``metadata``);直接拿 ``db.get_db()`` 给的
    MySQL 连接会因为列名不匹配而报错。生产数据迁移见
    ``scripts/migrate_messages_metadata.py``。``db_path`` 显式传入时(test
    fixture 注入)使用该路径。
  - ``user_memories``: 当构造时显式传入 ``db_path``(test fixture)时,直接
    连该 SQLite 文件,这是测试所需的能力。否则走 ``db.get_db()`` 让生产
    MySQL / SQLite 都能工作,与 ORM 路径对齐。同时**自动探测列名**,对老
    schema(只有 ``user_id, memory_type, content, importance,
    source_conversation_id, created_at, last_accessed``)与新 schema(完整
    超集含 ``source``/``confidence``/``access_count``/``confirmed``)都兼容。
  - 返回的 dict 包含超集字段 ``source``/``confidence``/``access_count``/
    ``confirmed``,让 ``memory_retriever`` 评分能拿到完整信息。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

import db


class DbPyChatRepository:
    def __init__(self, db_path: str = None):
        # 当 ``db_path`` 显式传入(test fixture)时记下来;``self._conn()`` 会用它。
        # 否则保留为 ``None``,记忆方法会用 ``db.get_db()`` 跟随当前生效后端。
        self.db_path = db_path

    def _conn(self):
        # 旧 messages 方法用的:永远连 self.db_path;若未设置则退回 db.SQLITE_PATH
        # (保持向后兼容)。
        import db as _db
        return sqlite3.connect(self.db_path or _db.SQLITE_PATH)

    # ── messages ──  (留 SQLite,不走 get_db())

    def save_message(self, user_id, message: dict) -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO messages (user_id, role, content, msg_metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                message.get("role", "user"),
                message.get("content", ""),
                json.dumps(message.get("metadata", {}), ensure_ascii=False),
                datetime.now().isoformat(),
            ))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_history(self, user_id, limit: int = 50) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, role, content, msg_metadata, created_at
                FROM messages
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            rows = [
                {
                    "id": r[0],
                    "role": r[1],
                    "content": r[2],
                    "metadata": json.loads(r[3]) if r[3] else {},
                    "created_at": r[4],
                }
                for r in cur.fetchall()
            ][::-1]  # reverse to chronological order
            return rows
        finally:
            conn.close()

    # ── memories ──  (db_path 显式 → 直连;否则走 db.get_db())

    def _memory_connection(self):
        """选择记忆操作的连接来源。

        - ``self.db_path`` 显式传入(test fixture)→ 返回 (``"sqlite"``,
          ``sqlite3.connect(self.db_path)``)
        - 否则 → 用 ``db.get_db()`` 跟随当前生效后端(MySQL / SQLite / JSON)

        返回 ``(backend_kind, conn_or_ctx)``。``conn_or_ctx`` 可以是直接的
        sqlite3.Connection,或一个 ``db.get_db()`` 返回的 context manager。
        为统一接口,这里直接返回连接对象,并把 ``db.get_db()`` 的生命周期
        由 ``_memory_conn_iter`` 负责进入/退出。
        """
        if self.db_path is not None:
            return "sqlite", sqlite3.connect(self.db_path)
        # 否则进入 db.get_db() 上下文;调用方应使用 _memory_conn_iter
        return "auto", None

    def _memory_conn_iter(self):
        """根据 ``self.db_path`` 是否显式,选择正确的连接上下文。

        产出 ``(backend_kind, conn)``;调用方负责 ``conn.close()`` 或依赖
        ``db.get_db()`` 自动 close。
        """
        if self.db_path is not None:
            conn = sqlite3.connect(self.db_path)
            try:
                yield "sqlite", conn
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
            return
        # 默认走 db.get_db(),跟随当前生效后端
        with db.get_db() as conn:
            yield ("auto", conn)

    @staticmethod
    def _existing_cols(conn) -> set:
        """探测 ``user_memories`` 已有列名(SQLite/MySQL 通用)。"""
        try:
            if db._is_sqlite(conn):  # noqa: SLF001
                cur = conn.cursor()
                try:
                    cur.execute("PRAGMA table_info(user_memories)")
                    return {row[1] for row in cur.fetchall()}
                finally:
                    try:
                        cur.close()
                    except Exception:
                        pass
            else:
                cur = conn.cursor()
                try:
                    cur.execute(
                        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_memories'"
                    )
                    return {row[0] for row in cur.fetchall()}
                finally:
                    try:
                        cur.close()
                    except Exception:
                        pass
        except Exception:
            return set()

    def save_memory(self, user_id, memory: dict) -> int:
        """保存一条用户记忆。

        id 处理策略：
          - 若 ``memory.get("id")`` 是整数：当 schema 是 BIGINT/INT 自增 PK 时使用
          - 若 ``memory.get("id")`` 是字符串（UUID）：当 schema 是 VARCHAR PK 时使用
          - 否则探测 ``id`` 列的类型：VARCHAR/TEXT → 生成 UUID；BIGINT/INT → 依赖
            ``AUTO_INCREMENT``（lastrowid）

        自动适配 schema:如果表里没有 ``source`` / ``confidence`` /
        ``access_count`` / ``confirmed`` / ``updated_at`` 列(老 schema 或
        简化的 test fixture),只 INSERT 已存在的列。
        """
        import uuid as _uuid

        explicit_id = memory.get("id")
        explicit_str_id = None  # 用于 VARCHAR 类型的字符串 PK
        explicit_int_id = None  # 用于 BIGINT/INT 类型的整型 PK
        if explicit_id is not None:
            # 优先尝试整型
            try:
                explicit_int_id = int(explicit_id)
            except (TypeError, ValueError):
                # 非整数 → 当字符串 PK 用（如果传过来的本来就是 str）
                if isinstance(explicit_id, str) and explicit_id:
                    explicit_str_id = explicit_id

        for _backend, conn in self._memory_conn_iter():
            if conn is None:
                # JSON 回退
                return self._save_memory_json(user_id, memory)
            try:
                # 确保表存在;只在没有时建(不会重复补列,因为 _ensure_user_memories_table
                # 内部已经幂等)。在 ``self.db_path`` 显式注入的 test 场景下,
                # 表已经存在,这一步几乎是 no-op。
                db._ensure_user_memories_table(conn)  # noqa: SLF001

                cols_avail = self._existing_cols(conn)
                if not cols_avail:
                    # 表都不存在 → JSON 回退
                    return self._save_memory_json(user_id, memory)

                # 探测 id 列类型,决定是否需要生成 UUID
                id_col_type = ""
                try:
                    if db._is_sqlite(conn):  # noqa: SLF001
                        cur = conn.cursor()
                        try:
                            cur.execute("PRAGMA table_info(user_memories)")
                            for r in cur.fetchall():
                                if r[1] == "id":
                                    id_col_type = (r[2] or "").upper()
                                    break
                        finally:
                            try:
                                cur.close()
                            except Exception:
                                pass
                    else:
                        cur = conn.cursor()
                        try:
                            cur.execute(
                                "SELECT DATA_TYPE FROM information_schema.COLUMNS "
                                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='user_memories' "
                                "AND COLUMN_NAME='id'"
                            )
                            row = cur.fetchone()
                            if row:
                                id_col_type = (row[0] or "").upper()
                        finally:
                            try:
                                cur.close()
                            except Exception:
                                pass
                except Exception:
                    id_col_type = ""

                varchar_like = any(
                    t in id_col_type
                    for t in ("VARCHAR", "CHAR", "TEXT", "UUID")
                )
                int_like = any(t in id_col_type for t in ("INT", "BIGINT"))

                # 根据 id 列类型决定显式 id：VARCHAR → 字符串 UUID；BIGINT → 整数
                # 缺省情况下：探测失败 → 走 UUID 路径（最安全的兼容）
                generated_str_id = f"mem_{_uuid.uuid4().hex[:16]}"
                if varchar_like:
                    use_id_value = explicit_str_id or generated_str_id
                elif int_like:
                    use_id_value = explicit_int_id  # 依赖 AUTO_INCREMENT 时为 None
                else:
                    # 未知类型 → 优先用字符串 UUID（更安全）
                    use_id_value = explicit_str_id or generated_str_id

                now = datetime.now().isoformat(sep=" ", timespec="seconds")
                placeholder = "?" if db._is_sqlite(conn) else "%s"  # noqa: SLF001

                # 列定义(标准超集);过滤掉实际不存在的列
                spec = [
                    ("user_id",                str(user_id)),
                    ("memory_type",            memory.get("memory_type", "fact")),
                    ("content",                memory.get("content", "")),
                    ("importance",             memory.get("importance", 1)),
                    ("source_conversation_id", memory.get("source_conversation_id")),
                    ("source",                 memory.get("source", "auto")),
                    ("confidence",             float(memory.get("confidence", 1.0))),
                    ("created_at",             now),
                    ("updated_at",             now),
                    ("last_accessed",          None),
                    ("access_count",           memory.get("access_count", 1)),
                    ("confirmed",              int(memory.get("confirmed", 0))),
                ]
                cols = []
                values = []
                if "id" in cols_avail and use_id_value is not None:
                    cols.append("id")
                    values.append(use_id_value)
                for col, val in spec:
                    if col in cols_avail:
                        cols.append(col)
                        values.append(val)

                cursor = conn.cursor()
                try:
                    cursor.execute(
                        f"INSERT INTO user_memories ({', '.join(cols)}) "
                        f"VALUES ({', '.join([placeholder] * len(cols))})",
                        values,
                    )
                    conn.commit()
                    new_id = cursor.lastrowid
                    # 优先级：lastrowid（自增 INT）> use_id_value（UUID 字符串）>
                    # explicit_int_id > 0
                    if new_id is not None and new_id > 0:
                        return new_id
                    if use_id_value is not None:
                        return use_id_value
                    return explicit_int_id or 0
                finally:
                    try:
                        cursor.close()
                    except Exception:
                        pass
            except Exception as e:
                # 任何 schema/类型不匹配 → JSON 回退
                print(f"[DbPyChatRepository.save_memory] SQL 保存失败,回退到 JSON: {e}")
                return self._save_memory_json(user_id, memory)
        return self._save_memory_json(user_id, memory)

    def _save_memory_json(self, user_id, memory: dict) -> int:
        """JSON 本地存储回退路径(与 db.py:save_user_memory 同语义)."""
        try:
            storage = db.load_local_storage()
            if "user_memories" not in storage:
                storage["user_memories"] = []
            now = datetime.now().isoformat(sep=" ", timespec="seconds")
            new_id = max(
                [m.get("id", 0) for m in storage["user_memories"] if isinstance(m.get("id"), int)],
                default=0,
            ) + 1
            storage["user_memories"].append({
                "id": new_id,
                "user_id": str(user_id),
                "memory_type": memory.get("memory_type", "fact"),
                "content": memory.get("content", ""),
                "importance": memory.get("importance", 1),
                "source_conversation_id": memory.get("source_conversation_id"),
                "source": memory.get("source", "auto"),
                "confidence": float(memory.get("confidence", 1.0)),
                "created_at": now,
                "updated_at": now,
                "last_accessed": None,
                "access_count": memory.get("access_count", 1),
                "confirmed": int(memory.get("confirmed", 0)),
            })
            db.save_local_storage(storage)
            return new_id
        except Exception:
            return 0

    def get_memories(self, user_id, memory_type: str | None = None, limit: int = 20) -> list:
        """获取用户记忆列表(超集字段,老 schema 也能跑)。

        返回字段: ``id`` / ``user_id`` / ``memory_type`` / ``content`` /
        ``importance`` / ``source_conversation_id`` / ``source`` /
        ``confidence`` / ``created_at`` / ``updated_at`` / ``last_accessed`` /
        ``access_count`` / ``confirmed``。
        """
        for _backend, conn in self._memory_conn_iter():
            if conn is None:
                return self._get_memories_json(user_id, memory_type, limit)
            try:
                db._ensure_user_memories_table(conn)  # noqa: SLF001
                cols_avail = self._existing_cols(conn)
                if not cols_avail:
                    return self._get_memories_json(user_id, memory_type, limit)

                # 列名 → 顺序索引;查询时按可用列拼 SELECT
                preferred = [
                    "id", "user_id", "memory_type", "content",
                    "importance", "source_conversation_id",
                    "source", "confidence",
                    "created_at", "updated_at", "last_accessed",
                    "access_count", "confirmed",
                ]
                select_cols = [c for c in preferred if c in cols_avail]
                if "id" not in select_cols:
                    select_cols.insert(0, "id")

                placeholder = "?" if db._is_sqlite(conn) else "%s"  # noqa: SLF001
                where_parts = [f"user_id = {placeholder}"]
                params: list = [str(user_id)]
                if memory_type is not None and "memory_type" in cols_avail:
                    where_parts.append(f"memory_type = {placeholder}")
                    params.append(memory_type)

                order_col = "importance" if "importance" in cols_avail else (
                    "updated_at" if "updated_at" in cols_avail else "id"
                )
                sql = (
                    f"SELECT {', '.join(select_cols)} FROM user_memories "
                    f"WHERE {' AND '.join(where_parts)} "
                    f"ORDER BY {order_col} DESC LIMIT {placeholder}"
                )
                params.append(limit)

                cursor = conn.cursor()
                try:
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                finally:
                    try:
                        cursor.close()
                    except Exception:
                        pass

                # 标准化为 dict 列表
                out: list = []
                for row in rows:
                    if isinstance(row, dict):
                        d = dict(row)
                    else:
                        d = dict(zip(select_cols, row))
                    # 默认值填充分
                    out.append({
                        "id": d.get("id"),
                        "user_id": d.get("user_id", str(user_id)),
                        "memory_type": d.get("memory_type") or "fact",
                        "content": d.get("content") or "",
                        "importance": d.get("importance") if d.get("importance") is not None else 1,
                        "source_conversation_id": d.get("source_conversation_id"),
                        "source": d.get("source") or "auto",
                        "confidence": float(d["confidence"]) if d.get("confidence") is not None else 1.0,
                        "created_at": d.get("created_at"),
                        "updated_at": d.get("updated_at"),
                        "last_accessed": d.get("last_accessed"),
                        "access_count": d.get("access_count") if d.get("access_count") is not None else 1,
                        "confirmed": int(d["confirmed"]) if d.get("confirmed") is not None else 0,
                    })
                return out
            except Exception:
                return self._get_memories_json(user_id, memory_type, limit)
        return self._get_memories_json(user_id, memory_type, limit)

    def _get_memories_json(self, user_id, memory_type, limit) -> list:
        """JSON 本地存储回退路径."""
        try:
            storage = db.load_local_storage()
            memories = [m for m in storage.get("user_memories", []) if m.get("user_id") == str(user_id)]
            if memory_type is not None:
                memories = [m for m in memories if m.get("memory_type") == memory_type]
            memories.sort(
                key=lambda m: (m.get("importance") or 1, m.get("updated_at") or m.get("created_at") or ""),
                reverse=True,
            )
            return memories[:limit]
        except Exception:
            return []

    def update_memory(self, memory_id, updates: dict) -> None:
        """更新已有记忆的 content / importance / confidence / source.

        自动适配 schema:不存在的列会被跳过。
        """
        for _backend, conn in self._memory_conn_iter():
            if conn is None:
                return self._update_memory_json(memory_id, updates)

            try:
                db._ensure_user_memories_table(conn)  # noqa: SLF001
                cols_avail = self._existing_cols(conn)
                if not cols_avail:
                    return self._update_memory_json(memory_id, updates)

                placeholder = "?" if db._is_sqlite(conn) else "%s"  # noqa: SLF001
                assignments = []
                values: list = []
                field_map = {
                    "content":    updates.get("content"),
                    "importance": updates.get("importance"),
                    "confidence": updates.get("confidence"),
                    "source":     updates.get("source"),
                }
                for col, val in field_map.items():
                    if val is None or col not in cols_avail:
                        continue
                    assignments.append(f"{col} = {placeholder}")
                    values.append(val)
                if not assignments:
                    return

                cursor = conn.cursor()
                try:
                    cursor.execute(
                        f"UPDATE user_memories SET {', '.join(assignments)} WHERE id = {placeholder}",
                        (*values, memory_id),
                    )
                    conn.commit()
                    return
                finally:
                    try:
                        cursor.close()
                    except Exception:
                        pass
            except Exception:
                return self._update_memory_json(memory_id, updates)
        return self._update_memory_json(memory_id, updates)

    def _update_memory_json(self, memory_id, updates: dict) -> None:
        try:
            storage = db.load_local_storage()
            for m in storage.get("user_memories", []):
                if m.get("id") == memory_id:
                    if "content" in updates:
                        m["content"] = updates["content"]
                    if "importance" in updates:
                        m["importance"] = updates["importance"]
                    if "confidence" in updates:
                        m["confidence"] = updates["confidence"]
                    if "source" in updates:
                        m["source"] = updates["source"]
                    db.save_local_storage(storage)
                    break
        except Exception:
            pass

    def confirm_memory(self, memory_id, confirmed: bool = True) -> None:
        db.confirm_user_memory(memory_id, confirmed)

    def delete_memory(self, memory_id) -> None:
        db.delete_user_memory(memory_id)

    def bump_memory_access(self, memory_id) -> None:
        db.bump_memory_access(memory_id)