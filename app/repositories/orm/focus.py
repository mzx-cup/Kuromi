"""SQLAlchemy implementation for focus session tracking (M7).

This repository backs the focus read path with SQLAlchemy. It mirrors
the methods on :class:`app.repositories.legacy.focus.DbPyFocusRepository`
so callers can swap implementations behind the
:class:`app.repositories.base.FocusRepository` Protocol.

The flow score formula itself stays in higher-level services — we only
persist events and aggregates here.
"""
from __future__ import annotations

from datetime import datetime, date, timedelta

from sqlalchemy.orm import Session

from app.models.focus import FocusSession, FocusEvent, UserFocusHistory


class SqlAlchemyFocusRepository:
    def __init__(self, session: Session = None):
        self.session = session

    # ── user_focus_history ──

    def get_history(self, user_id: str, days: int = 7) -> list:
        cutoff = date.today() - timedelta(days=days)
        rows = (
            self.session.query(UserFocusHistory)
            .filter(
                UserFocusHistory.user_id == user_id,
                UserFocusHistory.focus_date >= cutoff,
            )
            .order_by(UserFocusHistory.focus_date.desc())
            .all()
        )
        return [
            {
                "date": str(r.focus_date),
                "total_minutes": r.total_focus_minutes,
                "sessions": r.sessions_count,
                "avg_flow_score": r.avg_flow_score,
                "deep_focus_minutes": r.deep_focus_minutes,
            }
            for r in rows
        ]

    # ── focus_sessions ──

    def start_session(self, user_id: str, planned_minutes: int, subject: str = "") -> int:
        fs = FocusSession(
            user_id=user_id,
            planned_minutes=planned_minutes,
            subject=subject,
            started_at=datetime.utcnow(),
            completed=False,
        )
        self.session.add(fs)
        self.session.flush()
        return fs.id

    def end_session(self, session_id: int, duration_minutes: int, completed: bool) -> None:
        fs = self.session.query(FocusSession).filter_by(id=session_id).first()
        if fs:
            fs.ended_at = datetime.utcnow()
            fs.duration_minutes = duration_minutes
            fs.completed = completed
            self.session.flush()

    # ── focus_events ──

    def record_event(
        self,
        session_id: int,
        event_type: str,
        flow_score: float,
        metadata: dict = None,
    ) -> None:
        self.session.add(
            FocusEvent(
                session_id=session_id,
                event_type=event_type,
                flow_score=flow_score,
                metadata_json=metadata or {},
                timestamp=datetime.utcnow(),
            )
        )
        self.session.flush()

    def get_events(self, session_id: int) -> list:
        events = (
            self.session.query(FocusEvent)
            .filter_by(session_id=session_id)
            .order_by(FocusEvent.timestamp)
            .all()
        )
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "flow_score": e.flow_score,
                "metadata": e.metadata_json,
            }
            for e in events
        ]

    # ── user_focus_history upsert (daily aggregate) ──

    def upsert_user_focus_history(
        self,
        user_id: str,
        focus_date,
        added_focus_minutes: int,
        added_session: bool,
        new_flow_score: float,
    ) -> None:
        """Increment today's aggregate row. Idempotent w.r.t. concurrent flushes
        because we read-then-write within the same session."""
        from sqlalchemy import func

        row = (
            self.session.query(UserFocusHistory)
            .filter_by(user_id=user_id, focus_date=focus_date)
            .first()
        )
        if row is None:
            row = UserFocusHistory(
                user_id=user_id,
                focus_date=focus_date,
                total_focus_minutes=int(added_focus_minutes),
                sessions_count=1 if added_session else 0,
                avg_flow_score=float(new_flow_score),
                deep_focus_minutes=int(added_focus_minutes) if new_flow_score >= 75 else 0,
            )
            self.session.add(row)
        else:
            # weighted average: combine existing avg with the new sample
            old_n = max(1, row.sessions_count)
            old_avg = float(row.avg_flow_score or 0)
            if added_session:
                row.sessions_count = old_n + 1
                row.avg_flow_score = (old_avg * old_n + float(new_flow_score)) / (old_n + 1)
            row.total_focus_minutes = int(row.total_focus_minutes or 0) + int(added_focus_minutes)
            if new_flow_score >= 75:
                row.deep_focus_minutes = int(row.deep_focus_minutes or 0) + int(added_focus_minutes)
        self.session.flush()