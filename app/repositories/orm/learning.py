"""SQLAlchemy implementation for learning statistics (read methods only in M3).

Implements read methods for the learning statistics slice. Write methods
are stubs and will be filled in M4.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.learning import (
    LearningGoal,
    LearningRecord,
    StudySession,
    UserEvaluationMetric,
    UserLearningProfile,
    UserStats,
    WeeklySummary,
)


class SqlAlchemyLearningRepository:
    def __init__(self, session: Session = None):
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

    # ── Write methods (M4) ──

    def record_session(self, user_id, session_data: dict) -> None:
        """Insert a study session record (ORM).

        Writes both StudySession and LearningRecord rows so the
        overview/trend/mastery read paths remain consistent.
        """
        from datetime import datetime, date

        minutes = int(
            session_data.get("minutes")
            or session_data.get("duration_minutes")
            or 0
        )
        subject = session_data.get("subject", "")

        session_date_raw = session_data.get("session_date")
        if session_date_raw:
            try:
                session_date = datetime.fromisoformat(session_date_raw).date()
            except (ValueError, TypeError):
                session_date = date.today()
        else:
            session_date = date.today()

        study = StudySession(
            user_id=user_id,
            subject=subject,
            duration_minutes=minutes,
            session_date=session_date,
            created_at=datetime.utcnow(),
        )
        self.session.add(study)

        record = LearningRecord(
            user_id=user_id,
            activity_type=session_data.get("activity_type", "study"),
            subject=subject,
            minutes=minutes,
            metadata_json=session_data.get("metadata", {}),
            recorded_at=datetime.utcnow(),
        )
        self.session.add(record)
        self.session.flush()

    def record_goal(self, user_id, goal_data: dict) -> int:
        """Create or update a learning goal. Returns the goal id."""
        from datetime import datetime

        if goal_data.get("id"):
            existing = (
                self.session.query(LearningGoal)
                .filter_by(id=goal_data["id"], user_id=user_id)
                .first()
            )
            if existing:
                existing.title = goal_data.get("title", existing.title)
                existing.target_value = goal_data.get(
                    "target_value", existing.target_value
                )
                existing.current_value = goal_data.get(
                    "current_value", existing.current_value
                )
                existing.unit = goal_data.get("unit", existing.unit)
                existing.deadline = goal_data.get("deadline", existing.deadline)
                self.session.flush()
                return existing.id

        goal = LearningGoal(
            user_id=user_id,
            title=goal_data.get("title", ""),
            target_value=goal_data.get("target_value", 0),
            current_value=goal_data.get("current_value", 0),
            unit=goal_data.get("unit", "minutes"),
            deadline=goal_data.get("deadline"),
            created_at=datetime.utcnow(),
        )
        self.session.add(goal)
        self.session.flush()
        return goal.id

    def delete_goal(self, user_id, goal_id: int) -> None:
        """Delete a learning goal owned by the user."""
        goal = (
            self.session.query(LearningGoal)
            .filter_by(id=goal_id, user_id=user_id)
            .first()
        )
        if goal:
            self.session.delete(goal)
            self.session.flush()

    # ── Learning profile + evaluation (A3) ──

    _EVAL_FIELDS = (
        "interaction_count",
        "socratic_pass_rate",
        "difficulty_level",
        "code_practice_time",
        "focus_time_today",
        "flashcards_studied",
        "streak_days",
    )

    _EVAL_INPUT_ALIASES = {
        "interaction_count": "interactionCount",
        "socratic_pass_rate": "socraticPassRate",
        "difficulty_level": "difficultyLevel",
        "code_practice_time": "codePracticeTime",
        "focus_time_today": "focusTimeToday",
        "flashcards_studied": "flashcardsStudied",
        "streak_days": "streakDays",
    }

    def save_learning_record(self, user_id, record: dict) -> int:
        """Upsert the user's learning-profile snapshot (one row per user)."""
        profile = (
            self.session.query(UserLearningProfile)
            .filter_by(user_id=user_id)
            .first()
        )
        if profile is None:
            profile = UserLearningProfile(user_id=user_id)
            self.session.add(profile)
        for field in (
            "interaction_count",
            "code_practice_time",
            "socratic_pass_rate",
            "difficulty_level",
            "profile_json",
        ):
            if field in record:
                setattr(profile, field, record[field])
        profile.updated_at = datetime.utcnow()
        self.session.flush()
        return 1

    def get_learning_record(self, user_id) -> dict | None:
        """Return the user's learning-profile snapshot, or None."""
        profile = (
            self.session.query(UserLearningProfile)
            .filter_by(user_id=user_id)
            .first()
        )
        if profile is None:
            return None
        return {
            "user_id": profile.user_id,
            "interaction_count": profile.interaction_count,
            "code_practice_time": profile.code_practice_time,
            "socratic_pass_rate": profile.socratic_pass_rate,
            "difficulty_level": profile.difficulty_level,
            "profile_json": profile.profile_json,
        }

    def save_user_evaluation(self, user_id, evaluation: dict) -> int:
        """Upsert today's evaluation metrics, merging present fields only."""
        today = date.today()
        row = (
            self.session.query(UserEvaluationMetric)
            .filter_by(user_id=user_id, record_date=today)
            .first()
        )
        if row is None:
            row = UserEvaluationMetric(user_id=user_id, record_date=today)
            self.session.add(row)
        for field in self._EVAL_FIELDS:
            if field in evaluation:
                setattr(row, field, evaluation[field])
                continue
            alias = self._EVAL_INPUT_ALIASES[field]
            if alias in evaluation:
                setattr(row, field, evaluation[alias])
        row.eval_json = json.dumps(evaluation, ensure_ascii=False)
        self.session.flush()
        return 1

    def _eval_to_dict(self, row: UserEvaluationMetric) -> dict:
        return {
            "interaction_count": row.interaction_count,
            "socratic_pass_rate": row.socratic_pass_rate,
            "difficulty_level": row.difficulty_level,
            "code_practice_time": row.code_practice_time,
            "focus_time_today": row.focus_time_today,
            "flashcards_studied": row.flashcards_studied,
            "streak_days": row.streak_days,
            "eval_json": row.eval_json,
            "record_date": row.record_date.isoformat(),
        }

    def get_user_evaluation(self, user_id, record_date: str | None = None) -> dict | None:
        """Return a single day's evaluation (defaults to today), or None."""
        if record_date is None:
            target = date.today()
        else:
            target = date.fromisoformat(record_date)
        row = (
            self.session.query(UserEvaluationMetric)
            .filter_by(user_id=user_id, record_date=target)
            .first()
        )
        return self._eval_to_dict(row) if row else None

    def get_user_evaluation_history(self, user_id, days: int = 7) -> list:
        """Return the most-recent N days of evaluation metrics."""
        rows = (
            self.session.query(UserEvaluationMetric)
            .filter(UserEvaluationMetric.user_id == user_id)
            .order_by(UserEvaluationMetric.record_date.desc())
            .limit(days)
            .all()
        )
        return [self._eval_to_dict(r) for r in rows]
