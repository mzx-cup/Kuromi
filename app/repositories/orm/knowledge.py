"""SQLAlchemy implementation for knowledge graph and SM2 reviews (M6).

This repository backs the knowledge read path with SQLAlchemy. It mirrors
the methods on :class:`app.repositories.legacy.knowledge.DbPyKnowledgeRepository`
so callers can swap implementations behind the
:class:`app.repositories.base.KnowledgeRepository` Protocol.

The SM2 algorithm itself stays in higher-level services — we accept the
upstream-computed ``ease_factor`` and ``interval_days`` and only persist
them.
"""
from __future__ import annotations

from datetime import datetime, date, timedelta

from sqlalchemy.orm import Session

from app.models.knowledge import (
    KnowledgeNode,
    KnowledgeRelation,
    KnowledgeReview,
    KnowledgeRecord,
    KnowledgePending,
)


class SqlAlchemyKnowledgeRepository:
    def __init__(self, session: Session = None):
        self.session = session

    # ── knowledge_nodes ──

    def get_nodes(self, user_id: str) -> list:
        nodes = (
            self.session.query(KnowledgeNode)
            .filter_by(user_id=user_id)
            .order_by(KnowledgeNode.importance.desc(), KnowledgeNode.mastery.asc())
            .all()
        )
        return [
            {
                "id": n.id,
                "name": n.name,
                "subject": n.subject,
                "description": n.description,
                "mastery": n.mastery,
                "importance": n.importance,
            }
            for n in nodes
        ]

    def add_node(self, user_id: str, node_data: dict) -> int:
        node = KnowledgeNode(
            user_id=user_id,
            name=node_data.get("name", ""),
            subject=node_data.get("subject", ""),
            description=node_data.get("description", ""),
            mastery=node_data.get("mastery", 0),
            importance=node_data.get("importance", 1),
            created_at=datetime.utcnow(),
        )
        self.session.add(node)
        self.session.flush()
        return node.id

    # ── knowledge_pending ──

    def get_pending(self, user_id: str) -> list:
        today = date.today()
        pending = (
            self.session.query(KnowledgePending)
            .filter(
                KnowledgePending.user_id == user_id,
                KnowledgePending.due_date <= today,
            )
            .order_by(KnowledgePending.priority.desc(), KnowledgePending.due_date)
            .all()
        )
        result = []
        for p in pending:
            node = (
                self.session.query(KnowledgeNode)
                .filter_by(id=p.node_id)
                .first()
            )
            if not node:
                continue
            review = (
                self.session.query(KnowledgeReview)
                .filter_by(node_id=node.id)
                .first()
            )
            result.append(
                {
                    "id": node.id,
                    "name": node.name,
                    "subject": node.subject,
                    "mastery": node.mastery,
                    "next_review": review.next_review_date.isoformat()
                    if review and review.next_review_date
                    else None,
                    "interval_days": review.interval_days if review else 1,
                }
            )
        return result

    # ── knowledge_records ──

    def get_records(self, user_id: str, limit: int = 50) -> list:
        records = (
            self.session.query(KnowledgeRecord)
            .filter_by(user_id=user_id)
            .order_by(KnowledgeRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "node_id": r.node_id,
                "action": r.action,
                "quality": r.quality,
                "notes": r.notes,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]

    # ── SM2 review write ──

    def record_review(
        self,
        user_id: str,
        node_id: int,
        quality: int,
        ease_factor: float,
        interval_days: int,
    ) -> None:
        """Upsert the (user, node) review row and append a ``review`` audit row."""
        next_date = date.today() + timedelta(days=interval_days)
        now = datetime.utcnow()

        existing = (
            self.session.query(KnowledgeReview)
            .filter_by(user_id=user_id, node_id=node_id)
            .first()
        )
        if existing:
            existing.ease_factor = ease_factor
            existing.interval_days = interval_days
            existing.repetitions = (existing.repetitions or 0) + 1
            existing.next_review_date = next_date
            existing.last_reviewed_at = now
        else:
            self.session.add(
                KnowledgeReview(
                    user_id=user_id,
                    node_id=node_id,
                    ease_factor=ease_factor,
                    interval_days=interval_days,
                    repetitions=1,
                    next_review_date=next_date,
                    last_reviewed_at=now,
                )
            )

        self.session.add(
            KnowledgeRecord(
                user_id=user_id,
                node_id=node_id,
                action="review",
                quality=quality,
                created_at=now,
            )
        )
        self.session.flush()

    # ── SM2 due items (slice-11) ──

    def get_sm2_due(self, user_id: str) -> list:
        """Return SM2-spaced-repetition review items due now.

        Note: schema-deviation from the plan. ``KnowledgeNode`` has
        ``name`` (not ``topic``) and the ``ReviewHistory`` table does not
        expose a per-row ``interval_days`` column, so this query omits the
        interval-days projection entirely and emits a hardcoded
        ``interval_days=1`` in the result dict — matching the plan's
        ``node.interval_days or 1`` fallback. Output dict shape still
        preserves the contract: ``node_id``, ``subject``, ``topic``
        (=name), ``interval_days``.
        """
        from datetime import date
        from app.models.knowledge import KnowledgeNode, ReviewHistory
        from sqlalchemy import func

        subq = (
            self.session.query(
                ReviewHistory.node_id,
                func.max(ReviewHistory.next_review_date).label("next"),
            )
            .filter(ReviewHistory.user_id == user_id)
            .group_by(ReviewHistory.node_id)
            .subquery()
        )
        rows = (
            self.session.query(KnowledgeNode, subq.c.next)
            .outerjoin(subq, KnowledgeNode.id == subq.c.node_id)
            .filter(KnowledgeNode.user_id == user_id)
            .filter((subq.c.next == None) | (subq.c.next <= date.today()))
            .limit(20)
            .all()
        )
        return [
            {
                "node_id": node.id,
                "subject": node.subject,
                "topic": node.name,
                "interval_days": 1,
            }
            for node, _ in rows
        ]