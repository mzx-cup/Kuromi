"""SQLAlchemy implementation for learning statistics (read methods only in M3).

Implements read methods for the learning statistics slice. Write methods
are stubs and will be filled in M4.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.learning import (
    LearningGoal,
    LearningRecord,
    StudySession,
    UserStats,
    WeeklySummary,
)


class SqlAlchemyLearningRepository:
    def __init__(self, session: Session):
        self.session = session

    # ── Read methods ──

    def get_overview(self, user_id) -> dict:
        total_min = (
            self.session.query(func.coalesce(func.sum(StudySession.duration_minutes), 0))
            .filter(StudySession.user_id == user_id)
            .scalar()
            or 0
        )
        study_days = (
            self.session.query(func.count(func.distinct(StudySession.session_date)))
            .filter(StudySession.user_id == user_id)
            .scalar()
            or 0
        )

        # Streak calculation
        sessions = (
            self.session.query(StudySession.session_date)
            .filter(StudySession.user_id == user_id)
            .order_by(StudySession.session_date.desc())
            .limit(30)
            .all()
        )
        dates = [s[0] for s in sessions]
        streak = 0
        today = datetime.now().date()
        for i, d in enumerate(dates):
            expected = today - timedelta(days=i)
            if d == expected:
                streak += 1
            else:
                break

        return {
            "total_minutes": int(total_min),
            "study_days": int(study_days),
            "current_streak": streak,
        }

    def get_trend(self, user_id, days: int) -> list:
        cutoff = datetime.now().date() - timedelta(days=days)
        results = (
            self.session.query(
                StudySession.session_date,
                func.sum(StudySession.duration_minutes).label("minutes"),
            )
            .filter(
                StudySession.user_id == user_id,
                StudySession.session_date >= cutoff,
            )
            .group_by(StudySession.session_date)
            .order_by(StudySession.session_date)
            .all()
        )
        return [{"date": str(r[0]), "minutes": int(r[1] or 0)} for r in results]

    def get_heatmap(self, user_id) -> dict:
        cutoff = datetime.now().date() - timedelta(days=365)
        results = (
            self.session.query(
                StudySession.session_date,
                func.sum(StudySession.duration_minutes).label("minutes"),
            )
            .filter(
                StudySession.user_id == user_id,
                StudySession.session_date >= cutoff,
            )
            .group_by(StudySession.session_date)
            .all()
        )
        return {str(r[0]): int(r[1] or 0) for r in results}

    def get_mastery(self, user_id) -> list:
        results = (
            self.session.query(
                LearningRecord.subject,
                LearningRecord.activity_type,
                func.avg(LearningRecord.minutes).label("avg_min"),
            )
            .filter(LearningRecord.user_id == user_id)
            .group_by(LearningRecord.subject, LearningRecord.activity_type)
            .all()
        )
        return [
            {"subject": r[0], "topic": r[1], "mastery": min(100, int(r[2] or 0) * 2)}
            for r in results
        ]

    # ── Write stub (M4's responsibility) ──

    def record_session(self, user_id, session_data: dict) -> None:
        raise NotImplementedError("Write path is M4's responsibility")
