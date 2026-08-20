"""db.py wrapper for knowledge graph and SM2 reviews (M6).

真实 schema（两引擎一致）：``knowledge_nodes(node_id, name, subject,
sm2_data_json, stats_json, ...)`` + ``review_records(record_id, user_id,
node_id, quality, response_time, sm2_result_json)``。SM2 状态存在节点的
sm2_data_json 里，复习历史存在 review_records。

旧版本查询的 ``knowledge_reviews`` / ``knowledge_records`` /
``knowledge_pending`` / ``review_history`` 表在两个真实引擎中都不存在
（只在测试 fixture 里建过）—— 那些路径此前必然抛
"no such table"。本版本读路径委托 db.py 正式函数，写路径用真实表。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime

import db
from app.repositories.legacy._conn import legacy_conn, legacy_scope, ph


def _parse_json(value, default):
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, type(default)) else default
        except (json.JSONDecodeError, TypeError):
            return default
    if value is None:
        return default
    return value if isinstance(value, type(default)) else default


class DbPyKnowledgeRepository:
    def __init__(self, db_path: str = None):
        # 测试隔离用（显式 SQLite 文件）；生产为 None → 跟随生效后端。
        self.db_path = db_path

    # ── knowledge_nodes ──

    def get_nodes(self, user_id: str) -> list:
        with legacy_scope(self.db_path):
            nodes = db.get_knowledge_nodes(user_id) or []
        out = []
        for node in nodes:
            sm2 = _parse_json(node.get("sm2_data"), {}) or {}
            stats = _parse_json(node.get("stats"), {}) or {}
            mastery = stats.get("mastery")
            if mastery is None:
                mastery = min(1.0, (sm2.get("repetitions") or 0) / 10.0)
            out.append({
                "id": node.get("node_id"),
                "name": node.get("name", ""),
                "subject": node.get("subject", ""),
                "description": stats.get("description", ""),
                "mastery": mastery,
                "importance": stats.get("importance", 1),
            })
        out.sort(key=lambda n: (-(n["importance"] or 0), n["mastery"] or 0))
        return out

    def add_node(self, user_id: str, node_data: dict) -> int:
        """INSERT 一个知识节点（真实 schema），node_id 为生成的 uuid。

        mastery / importance / description 存进 stats_json（真实表没有
        这三个归一化列），get_nodes 读回时还原。
        """
        with legacy_scope(self.db_path):
            db.init_knowledge_tables()
        node_id = node_data.get("node_id") or uuid.uuid4().hex[:16]
        now_iso = datetime.now().isoformat()
        stats = {
            "mastery": node_data.get("mastery", 0),
            "importance": node_data.get("importance", 1),
            "description": node_data.get("description", ""),
        }
        sm2_data = node_data.get("sm2_data") or {
            "easiness_factor": 2.5,
            "interval": 1,
            "repetitions": 0,
        }
        with legacy_conn(self.db_path) as conn:
            cur = conn.cursor()
            p = ph(conn)
            cur.execute(
                f"""
                INSERT INTO knowledge_nodes
                (user_id, node_id, name, subject, level, icon, is_active,
                 created_at, sm2_data_json, stats_json)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                """,
                (
                    user_id,
                    node_id,
                    node_data.get("name", ""),
                    node_data.get("subject", ""),
                    node_data.get("level", "leaf"),
                    node_data.get("icon", "📚"),
                    1 if node_data.get("is_active", True) else 0,
                    now_iso,
                    json.dumps(sm2_data, ensure_ascii=False),
                    json.dumps(stats, ensure_ascii=False),
                ),
            )
            conn.commit()
            return cur.lastrowid

    # ── pending reviews ──

    def _subject_map(self, user_id: str) -> dict:
        with legacy_scope(self.db_path):
            nodes = db.get_knowledge_nodes(user_id) or []
        return {
            n.get("node_id"): n.get("subject", "")
            for n in nodes
        }

    def get_pending(self, user_id: str) -> list:
        subjects = self._subject_map(user_id)
        with legacy_scope(self.db_path):
            pending = db.get_pending_reviews(user_id) or []
        return [
            {
                "id": item.get("node_id"),
                "name": item.get("name", ""),
                "subject": subjects.get(item.get("node_id"), ""),
                "mastery": 0,
                "next_review": item.get("next_review"),
                "interval_days": 1,
            }
            for item in pending
        ]

    # ── review_records ──

    def get_records(self, user_id: str, limit: int = 50) -> list:
        with legacy_scope(self.db_path):
            records = db.get_review_records(user_id, limit=limit) or []
        return [
            {
                "id": r.get("record_id") or r.get("id"),
                "node_id": r.get("node_id"),
                "action": "review",
                "quality": r.get("quality"),
                "notes": "",
                "created_at": str(r.get("review_date")) if r.get("review_date") is not None else None,
            }
            for r in records
        ]

    # ── SM2 review write ──

    def record_review(
        self,
        user_id: str,
        node_id,
        quality: int,
        ease_factor: float,
        interval_days: int,
    ) -> None:
        """记录一次 SM2 复习：更新节点 sm2_data_json + 追加 review_records。

        委托 db.add_review_record（系统唯一的 SM2 写入路径）：SM2 值由
        db.calculate_sm2(quality, ...) 重算 —— 与上游用同一公式，落库
        结果一致；且保证 review_records 与 sm2_data_json 由同一段代码
        维护，不会漂移。
        """
        with legacy_scope(self.db_path):
            db.add_review_record(user_id, str(node_id), quality)

    # ── SM2 due items (slice-11) ──

    def get_sm2_due(self, user_id: str) -> list:
        """Return SM2-spaced-repetition review items due now.

        db.get_pending_reviews 已按 next_review <= now（或 24h 内）过滤。
        """
        subjects = self._subject_map(user_id)
        with legacy_scope(self.db_path):
            pending = db.get_pending_reviews(user_id) or []
        return [
            {
                "node_id": item.get("node_id"),
                "subject": subjects.get(item.get("node_id"), ""),
                "topic": item.get("name", ""),
                "interval_days": 1,
            }
            for item in pending[:20]
        ]
