"""SQLAlchemy models for knowledge graph and SM2 spaced repetition (M6).

This slice introduces the per-user knowledge graph backing the SM2
(Ebbinghaus forgetting curve) review system. Five tables:

* ``knowledge_nodes``        – nodes in the user's personal knowledge graph
* ``knowledge_relations``    – edges (prerequisite / related) between nodes
* ``knowledge_reviews``      – SM2 ease/interval/repetition state per node
* ``knowledge_records``      – append-only audit log of knowledge actions
* ``knowledge_pending``      – denormalized "due for review" set for fast lookup

The slice only persists SM2 storage. The SM2 algorithm itself continues to
live in higher-level services (we accept the upstream-computed
``ease_factor`` and ``interval_days``).
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Date, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class KnowledgeNode(Base):
    """A node in the user's knowledge graph (replaces db.py knowledge_nodes)."""
    __tablename__ = "knowledge_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    subject: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    mastery: Mapped[float] = mapped_column(Float, default=0)
    importance: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class KnowledgeRelation(Base):
    """A relation between two knowledge nodes (e.g., prerequisite)."""
    __tablename__ = "knowledge_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    source_node_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False)
    target_node_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), default="related")
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class KnowledgeReview(Base):
    """SM2 spaced repetition review record per (user, node)."""
    __tablename__ = "knowledge_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    node_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    next_review_date: Mapped[date] = mapped_column(Date, default=date.today)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeRecord(Base):
    """Audit log of all knowledge interactions (review, edit, etc.)."""
    __tablename__ = "knowledge_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    node_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), default="view")
    quality: Mapped[int] = mapped_column(Integer, default=0)  # SM2 quality 0-5
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())


class KnowledgePending(Base):
    """Knowledge nodes due for review (denormalized for fast lookup)."""
    __tablename__ = "knowledge_pending"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    node_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, default=date.today)
    priority: Mapped[int] = mapped_column(Integer, default=0)


class ReviewHistory(Base):
    """Append-only SM2 review history (one row per review).

    Used by ``KnowledgeRepository.get_sm2_due`` to compute the next due
    review date via ``MAX(next_review_date)`` per node.
    """
    __tablename__ = "review_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    node_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    next_review_date: Mapped[date] = mapped_column(Date, default=date.today)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())