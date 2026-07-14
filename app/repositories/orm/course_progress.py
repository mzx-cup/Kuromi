"""SQLAlchemy implementation for course progress and learning paths (M5)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.course_progress import (
    CourseGenerationStatus,
    CourseProgress,
    DailyRoute,
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

    # ── Upcoming deadlines (slice-11) ──

    def get_upcoming_deadlines(self, user_id, days: int = 7) -> list:
        """Return course deadlines within the next ``days`` days."""
        from datetime import date, timedelta
        from app.models.course_progress import CourseDeadline

        cutoff = date.today() + timedelta(days=days)
        rows = (
            self.session.query(CourseDeadline)
            .filter(
                CourseDeadline.user_id == user_id,
                CourseDeadline.deadline <= cutoff,
            )
            .order_by(CourseDeadline.deadline.asc())
            .limit(20)
            .all()
        )
        return [
            {"course_id": r.course_id, "title": r.title, "deadline": str(r.deadline)}
            for r in rows
        ]

    # ── Learning-path graph (Task C1) ──
    # The existing ORM ``learning_paths`` table is structurally distinct
    # from db.py's singular ``learning_path`` graph table (per-user JSON
    # blob vs. multi-row document). Until that schema is unified, the ORM
    # implementation routes through db.py helpers so legacy and ORM
    # produce identical results.

    def get_learning_path_graph(self, user_id) -> dict | None:
        import db as dbmod
        return dbmod.get_learning_path(user_id)

    def save_learning_path_graph(self, user_id, path_json, reasoning=None, data_sources=None, confidence=0.0) -> None:
        import db as dbmod
        dbmod.save_learning_path(
            user_id,
            path_json,
            reasoning=reasoning,
            data_sources=data_sources,
            confidence=confidence,
        )

    def get_learning_path_nodes(self, user_id) -> list:
        import db as dbmod
        return dbmod.get_learning_path_nodes(user_id)

    def get_learning_path_node(self, user_id, node_id) -> dict | None:
        import db as dbmod
        return dbmod.get_learning_path_node(user_id, node_id)

    def save_learning_path_node(self, user_id, node_data: dict) -> bool:
        import db as dbmod
        return bool(dbmod.save_learning_path_node(user_id, node_data))

    def sync_path_to_nodes(self, user_id, path_json) -> int:
        import db as dbmod
        return dbmod.sync_path_to_nodes(user_id, path_json)

    # ── Daily route (Task C1) ──

    def get_daily_route(self, user_id, route_date: str) -> dict | None:
        from datetime import date as _date
        target = _date.fromisoformat(route_date) if isinstance(route_date, str) else route_date
        row = (
            self.session.query(DailyRoute)
            .filter_by(user_id=str(user_id), route_date=target)
            .first()
        )
        if not row:
            return None
        return {
            "user_id": row.user_id,
            "route_date": row.route_date.isoformat(),
            "tasks_json": list(row.tasks_json or []),
            "completed_json": list(row.completed_json or []),
        }

    def save_daily_route(self, user_id, route_date: str, tasks, completed=None) -> None:
        from datetime import date as _date
        target = _date.fromisoformat(route_date) if isinstance(route_date, str) else route_date
        existing = (
            self.session.query(DailyRoute)
            .filter_by(user_id=str(user_id), route_date=target)
            .first()
        )
        if existing:
            existing.tasks_json = tasks if tasks is not None else existing.tasks_json
            existing.completed_json = completed if completed is not None else existing.completed_json
        else:
            self.session.add(
                DailyRoute(
                    user_id=str(user_id),
                    route_date=target,
                    tasks_json=tasks or [],
                    completed_json=completed or [],
                )
            )
        self.session.flush()
