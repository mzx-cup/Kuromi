"""SQLAlchemy implementation for classroom sessions and quiz records (M10).

This repository backs the classroom read path with SQLAlchemy. It mirrors
the methods on :class:`app.repositories.legacy.classroom.DbPyClassroomRepository`
so callers can swap implementations behind the
:class:`app.repositories.base.ClassroomRepository` Protocol.

The legacy ``classroom_sessions.id`` is INTEGER, but the ORM
:class:`app.models.classroom.ClassroomSession` PK is a String(64) UUID.
We reconcile by stringifying ORM ids when interacting with the legacy
backend and by stringifying any caller-supplied integer id before
filtering in this ORM repository.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.classroom import ClassroomSession, QuizRecord, AgentTurnRecord


def _coerce_id(session_id) -> str:
    """Coerce a caller-supplied session id to the ORM's String PK type.

    The legacy table uses integer ids, but the ORM ClassroomSession PK is
    String(64). We stringify here so callers can pass either form and the
    filter still finds the row (matches in our slice 10 test fixtures).
    """
    if session_id is None:
        return ""
    return str(session_id)


class SqlAlchemyClassroomRepository:
    def __init__(self, session: Session = None):
        self.session = session

    # ── sessions ──

    def get_session(self, session_id) -> dict | None:
        if self.session is None:
            return None
        cs = (
            self.session.query(ClassroomSession)
            .filter_by(id=_coerce_id(session_id))
            .first()
        )
        if not cs:
            return None
        return {
            "id": cs.id,
            "user_id": cs.user_id or cs.student_id,
            "course_id": cs.course_id,
            "started_at": cs.started_at.isoformat() if cs.started_at else None,
            "ended_at": cs.ended_at.isoformat() if cs.ended_at else None,
            "current_slide": cs.current_slide or 0,
            "status": cs.status or "active",
            "teacher_mode": bool(cs.teacher_mode),
        }

    def list_sessions(self, user_id) -> list:
        if self.session is None:
            return []
        # The original immersive-classroom schema uses ``student_id``;
        # the M10 extension added ``user_id``. Try both so callers can
        # pass either form.
        sessions = (
            self.session.query(ClassroomSession)
            .filter(
                (ClassroomSession.user_id == str(user_id))
                | (ClassroomSession.student_id == str(user_id))
            )
            .order_by(ClassroomSession.started_at.desc().nullslast())
            .all()
        )
        results = []
        for s in sessions:
            results.append(
                {
                    "id": s.id,
                    "course_id": s.course_id,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                    "current_slide": s.current_slide or 0,
                    "status": s.status or "active",
                }
            )
        return results

    def create_session(self, user_id, course_id: str, teacher_mode: bool = False) -> int:
        if self.session is None:
            return 0
        cs = ClassroomSession(
            id=_coerce_id(user_id) + "-" + datetime.utcnow().strftime("%Y%m%d%H%M%S%f"),
            user_id=str(user_id),
            student_id=str(user_id),
            course_id=course_id,
            started_at=datetime.utcnow(),
            status="active",
            teacher_mode=bool(teacher_mode),
            current_slide=0,
        )
        self.session.add(cs)
        self.session.flush()
        return cs.id

    def update_session(self, session_id, updates: dict) -> None:
        if self.session is None:
            return
        cs = (
            self.session.query(ClassroomSession)
            .filter_by(id=_coerce_id(session_id))
            .first()
        )
        if not cs:
            return
        for k, v in updates.items():
            if k == "teacher_mode":
                setattr(cs, k, bool(v))
            elif hasattr(cs, k):
                setattr(cs, k, v)
        self.session.flush()

    # ── quiz records ──

    def save_quiz_record(self, user_id, quiz_data: dict) -> int:
        if self.session is None:
            return 0
        # The original ``classroom_id`` is NOT NULL in the original schema
        # (string FK to classroom_sessions.id). The M10 additive session_id
        # is an optional integer. Use the provided session_id (stringified)
        # when available, otherwise fall back to a placeholder string so the
        # NOT NULL constraint is satisfied without breaking callers that
        # pass no session_id.
        session_str = ""
        if quiz_data.get("session_id") is not None:
            session_str = str(quiz_data.get("session_id"))
        qr = QuizRecord(
            classroom_id=session_str or "ad-hoc",
            user_id=str(user_id),
            student_id=str(user_id),
            session_id=quiz_data.get("session_id"),
            question=quiz_data.get("question", ""),
            answer=quiz_data.get("answer", ""),
            correct=bool(quiz_data.get("correct")),
            score=float(quiz_data.get("score", 0)),
            max_score=float(quiz_data.get("max_score", 100)),
            passed=bool(quiz_data.get("passed")),
            created_at=datetime.utcnow(),
        )
        self.session.add(qr)
        self.session.flush()
        return qr.id

    def get_quiz_records(self, user_id, limit: int = 20) -> list:
        if self.session is None:
            return []
        records = (
            self.session.query(QuizRecord)
            .filter(
                (QuizRecord.user_id == str(user_id))
                | (QuizRecord.student_id == str(user_id))
            )
            .order_by(QuizRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "session_id": r.session_id,
                "question": r.question,
                "answer": r.answer,
                "correct": bool(r.correct),
                "score": r.score or 0,
                "max_score": r.max_score or 100,
                "passed": bool(r.passed),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
