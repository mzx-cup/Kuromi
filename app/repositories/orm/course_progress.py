"""SQLAlchemy implementation for course progress and learning paths (M5)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.course_progress import (
    CourseGenerationStatus,
    CourseProgress,
    LearningPath,
    LearningPathNode,
    UserEvaluation,
)


class SqlAlchemyCourseProgressRepository:
    def __init__(self, session: Session = None):
        self.session = session

    # ── course_progress ──

    def get_progress(self, user_id, course_id: str) -> Optional[dict]:
        cp = (
            self.session.query(CourseProgress)
            .filter_by(user_id=str(user_id), course_id=course_id)
            .first()
        )
        if not cp:
            return None
        return {
            "progress_percent": cp.progress_percent or 0,
            "completed_at": cp.completed_at.isoformat() if cp.completed_at else None,
            "last_accessed": cp.last_accessed.isoformat() if cp.last_accessed else None,
            "state": cp.state_json or {},
        }

    def save_progress(
        self,
        user_id,
        course_id: str,
        progress_percent: float,
        state: dict = None,
    ) -> None:
        existing = (
            self.session.query(CourseProgress)
            .filter_by(user_id=str(user_id), course_id=course_id)
            .first()
        )
        now = datetime.utcnow()
        if existing:
            existing.progress_percent = progress_percent
            existing.last_accessed = now
            existing.state_json = state or {}
        else:
            self.session.add(
                CourseProgress(
                    user_id=str(user_id),
                    course_id=course_id,
                    progress_percent=progress_percent,
                    last_accessed=now,
                    state_json=state or {},
                )
            )
        self.session.flush()

    # ── learning_paths ──

    def get_learning_path(self, user_id) -> list:
        paths = (
            self.session.query(LearningPath)
            .filter_by(user_id=str(user_id))
            .order_by(LearningPath.created_at.desc())
            .all()
        )
        result = []
        for p in paths:
            nodes = (
                self.session.query(LearningPathNode)
                .filter_by(path_id=p.id)
                .order_by(LearningPathNode.order_index)
                .all()
            )
            result.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "nodes": [
                        {
                            "id": n.id,
                            "course_id": n.course_id,
                            "title": n.title,
                            "order": n.order_index,
                            "completed": bool(n.completed),
                        }
                        for n in nodes
                    ],
                }
            )
        return result

    # ── user_evaluations ──

    def get_evaluations(self, user_id) -> list:
        evals = (
            self.session.query(UserEvaluation)
            .filter_by(user_id=str(user_id))
            .order_by(UserEvaluation.evaluated_at.desc())
            .all()
        )
        return [
            {
                "id": e.id,
                "subject": e.subject,
                "score": e.score,
                "max_score": e.max_score,
                "notes": e.notes,
                "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None,
            }
            for e in evals
        ]
