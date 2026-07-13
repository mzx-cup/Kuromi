"""db.py wrapper for knowledge graph and SM2 reviews (M6).

Provides read/write methods against the db.py tables
``knowledge_nodes``, ``knowledge_relations``, ``knowledge_reviews``,
``knowledge_records`` and ``knowledge_pending`` while M6 gradually
shifts the read path to SQLAlchemy.

Only storage operations are exposed here — the SM2 algorithm itself
lives in higher-level services that pass in the computed
``ease_factor`` and ``interval_days``.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, date, timedelta


class DbPyKnowledgeRepository:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "xingshi.db"

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── knowledge_nodes ──

    def get_nodes(self, user_id: str) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, name, subject, description, mastery, importance
                FROM knowledge_nodes
                WHERE user_id = ?
                ORDER BY importance DESC, mastery ASC
                """,
                (user_id,),
            )
            return [
                {
                    "id": r[0],
                    "name": r[1],
                    "subject": r[2],
                    "description": r[3],
                    "mastery": r[4],
                    "importance": r[5],
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    def add_node(self, user_id: str, node_data: dict) -> int:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO knowledge_nodes
                (user_id, name, subject, description, mastery, importance, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    node_data.get("name", ""),
                    node_data.get("subject", ""),
                    node_data.get("description", ""),
                    node_data.get("mastery", 0),
                    node_data.get("importance", 1),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    # ── knowledge_pending ──

    def get_pending(self, user_id: str) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT kn.id, kn.name, kn.subject, kn.mastery,
                       kr.next_review_date, kr.interval_days
                FROM knowledge_pending kp
                JOIN knowledge_nodes kn ON kn.id = kp.node_id
                LEFT JOIN knowledge_reviews kr ON kr.node_id = kn.id
                WHERE kp.user_id = ? AND kp.due_date <= date('now')
                ORDER BY kp.priority DESC, kp.due_date
                """,
                (user_id,),
            )
            return [
                {
                    "id": r[0],
                    "name": r[1],
                    "subject": r[2],
                    "mastery": r[3],
                    "next_review": r[4],
                    "interval_days": r[5] or 1,
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    # ── knowledge_records ──

    def get_records(self, user_id: str, limit: int = 50) -> list:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, node_id, action, quality, notes, created_at
                FROM knowledge_records
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            return [
                {
                    "id": r[0],
                    "node_id": r[1],
                    "action": r[2],
                    "quality": r[3],
                    "notes": r[4],
                    "created_at": r[5],
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    # ── SM2 review write (knowledge_reviews + knowledge_records) ──

    def record_review(
        self,
        user_id: str,
        node_id: int,
        quality: int,
        ease_factor: float,
        interval_days: int,
    ) -> None:
        """Record a SM2 review: upsert the per-node review row and append
        a ``review`` audit row to ``knowledge_records``.

        The SM2 algorithm itself runs in higher-level services; this method
        only persists the upstream-computed ease_factor / interval_days.
        """
        conn = self._conn()
        try:
            cur = conn.cursor()
            next_date = (date.today() + timedelta(days=interval_days)).isoformat()
            now_iso = datetime.now().isoformat()

            # Upsert the (user_id, node_id) review row. SQLite supports
            # ON CONFLICT against the primary key; we look up first because
            # the legacy table does not have a UNIQUE(user_id, node_id).
            cur.execute(
                """
                SELECT id, repetitions FROM knowledge_reviews
                WHERE user_id = ? AND node_id = ?
                """,
                (user_id, node_id),
            )
            row = cur.fetchone()
            if row:
                review_id, repetitions = row[0], (row[1] or 0) + 1
                cur.execute(
                    """
                    UPDATE knowledge_reviews
                    SET ease_factor = ?,
                        interval_days = ?,
                        repetitions = ?,
                        next_review_date = ?,
                        last_reviewed_at = ?
                    WHERE id = ?
                    """,
                    (ease_factor, interval_days, repetitions, next_date, now_iso, review_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO knowledge_reviews
                    (user_id, node_id, ease_factor, interval_days,
                     repetitions, next_review_date, last_reviewed_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    """,
                    (user_id, node_id, ease_factor, interval_days, next_date, now_iso),
                )

            # Append audit row.
            cur.execute(
                """
                INSERT INTO knowledge_records (user_id, node_id, action, quality, created_at)
                VALUES (?, ?, 'review', ?, ?)
                """,
                (user_id, node_id, quality, now_iso),
            )
            conn.commit()
        finally:
            conn.close()

    # ── SM2 due items (slice-11) ──

    def get_sm2_due(self, user_id: str) -> list:
        """Return SM2-spaced-repetition review items due now.

        Aggregates from knowledge_nodes + review_history; items whose next_review
        date is today or earlier are returned.

        Note: schema-deviation from the plan. ``knowledge_nodes`` has
        ``name`` (not ``topic``) and no ``interval_days`` column —
        ``interval_days`` is read from the matching ``review_history`` row.
        Output dict shape preserves the plan contract: ``node_id``,
        ``subject``, ``topic`` (=name), ``interval_days``.
        """
        from datetime import date
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT kn.id, kn.subject, kn.name,
                       (SELECT rh.interval_days
                        FROM review_history rh
                        WHERE rh.node_id = kn.id AND rh.user_id = kn.user_id
                        ORDER BY rh.next_review_date DESC
                        LIMIT 1)
                FROM knowledge_nodes kn
                WHERE kn.user_id = ?
                  AND (
                    SELECT MAX(next_review_date)
                    FROM review_history rh
                    WHERE rh.node_id = kn.id AND rh.user_id = kn.user_id
                  ) <= date('now')
                LIMIT 20
            """, (user_id,))
            return [
                {"node_id": row[0], "subject": row[1], "topic": row[2], "interval_days": row[3] or 1}
                for row in cur.fetchall()
            ]
        finally:
            conn.close()