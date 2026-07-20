"""SQLAlchemy implementation for capability profile.

Mirrors DbPyCapabilityRepository 1:1 using SQLAlchemy ORM.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.learning import LearningGoal, LearningRecord, StudySession


class SqlAlchemyCapabilityRepository:
    def __init__(self, db_path: str = "xingshi_v2.db", session=None):
        self.db_path = db_path
        self._session = session

    def _session_local(self):
        engine = create_engine(f"sqlite:///{self.db_path}")
        Session = sessionmaker(bind=engine)
        return engine, Session()

    async def get_knowledge_base(self, user_id: str) -> dict:
        engine, session = self._session_local()
        try:
            rows = (
                session.query(StudySession.subject, StudySession.duration_minutes)
                .filter(StudySession.user_id == user_id)
                .all()
            )
            totals = defaultdict(int)
            for subject, mins in rows:
                if subject:
                    totals[subject] += mins or 0
            return {s: min(1.0, m / 600.0) for s, m in totals.items()}
        finally:
            session.close()
            engine.dispose()

    async def get_code_skill(self, user_id: str) -> dict:
        engine, session = self._session_local()
        try:
            rows = (
                session.query(LearningRecord.subject, LearningRecord.minutes)
                .filter(LearningRecord.user_id == user_id, LearningRecord.activity_type == "code")
                .all()
            )
            totals = defaultdict(int)
            for subject, mins in rows:
                if subject:
                    totals[subject] += mins or 0
            return {s: min(1.0, m / 300.0) for s, m in totals.items()}
        finally:
            session.close()
            engine.dispose()

    async def get_cognitive_style(self, user_id: str) -> dict:
        engine, session = self._session_local()
        try:
            records = (
                session.query(LearningRecord.metadata_json)
                .filter(LearningRecord.user_id == user_id)
                .order_by(LearningRecord.recorded_at.desc())
                .limit(20)
                .all()
            )
            modalities = []
            for (meta,) in records:
                if isinstance(meta, dict) and "modality" in meta:
                    modalities.append(meta["modality"])
            preferred = max(set(modalities), key=modalities.count) if modalities else "visual"
            return {"preferred_modality": preferred, "depth": "deep"}
        finally:
            session.close()
            engine.dispose()

    async def get_focus_level(self, user_id: str) -> dict:
        engine, session = self._session_local()
        try:
            sessions = (
                session.query(StudySession)
                .filter(StudySession.user_id == user_id)
                .all()
            )
            if not sessions:
                return {"avg_session_minutes": 0, "streak_days": 0}
            avg = sum(s.duration_minutes or 0 for s in sessions) / len(sessions)
            distinct_dates = sorted({s.session_date for s in sessions if s.session_date}, reverse=True)
            streak = 0
            today = date.today()
            for i, d in enumerate(distinct_dates):
                if d == today - timedelta(days=i):
                    streak += 1
                else:
                    break
            return {"avg_session_minutes": int(avg), "streak_days": streak}
        finally:
            session.close()
            engine.dispose()

    async def get_learning_goals(self, user_id: str) -> list:
        engine, session = self._session_local()
        try:
            goals = (
                session.query(LearningGoal)
                .filter(LearningGoal.user_id == user_id, LearningGoal.deadline.isnot(None))
                .all()
            )
            return [
                {
                    "id": g.id,
                    "title": g.title,
                    "progress": min(1.0, (g.current_value or 0) / g.target_value) if g.target_value else 0,
                    "unit": g.unit,
                    "deadline": str(g.deadline) if g.deadline else None,
                }
                for g in goals
            ]
        finally:
            session.close()
            engine.dispose()

    async def get_weakness(self, user_id: str) -> list:
        engine, session = self._session_local()
        try:
            rows = (
                session.query(LearningRecord.subject, LearningRecord.minutes)
                .filter(LearningRecord.user_id == user_id)
                .all()
            )
            by_subj = defaultdict(list)
            for s, m in rows:
                if s:
                    by_subj[s].append(m or 0)
            weakness = []
            for subject, vals in by_subj.items():
                avg = sum(vals) / len(vals)
                mastery = min(1.0, avg / 60.0)
                if mastery < 0.4:
                    weakness.append({"subject": subject, "mastery": mastery})
            return weakness
        finally:
            session.close()
            engine.dispose()

    async def aggregate_profile(self, user_id: str) -> dict:
        return {
            "knowledge_base": await self.get_knowledge_base(user_id),
            "code_skill": await self.get_code_skill(user_id),
            "cognitive_style": await self.get_cognitive_style(user_id),
            "focus_level": await self.get_focus_level(user_id),
            "learning_goals": await self.get_learning_goals(user_id),
            "weakness": await self.get_weakness(user_id),
        }
