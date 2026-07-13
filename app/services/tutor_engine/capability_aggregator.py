"""Aggregate raw 6-dim data into a structured CapabilityProfile.

The aggregator wraps a CapabilityRepository (resolved via the factory)
and produces a CapabilityProfile dataclass that ProactiveAdvisor can
consume.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.core.repository_factory import get_repository_for_user


@dataclass
class CognitiveStyle:
    preferred_modality: str = "visual"  # "visual" | "auditory" | "kinesthetic"
    depth: str = "deep"  # "shallow" | "deep"


@dataclass
class FocusLevel:
    avg_session_minutes: int = 0
    streak_days: int = 0


@dataclass
class LearningGoal:
    id: int
    title: str
    progress: float = 0.0
    unit: str = ""
    deadline: Optional[str] = None


@dataclass
class Weakness:
    subject: str
    topic: str = ""
    mastery: float = 0.0


@dataclass
class CapabilityProfile:
    user_id: str = ""
    knowledge_base: dict = field(default_factory=dict)
    code_skill: dict = field(default_factory=dict)
    cognitive_style: CognitiveStyle = field(default_factory=CognitiveStyle)
    focus_level: FocusLevel = field(default_factory=FocusLevel)
    learning_goals: list = field(default_factory=list)  # list[LearningGoal]
    weakness: list = field(default_factory=list)  # list[Weakness]


class CapabilityAggregator:
    async def from_raw(self, raw: dict) -> CapabilityProfile:
        return CapabilityProfile(
            knowledge_base=raw.get("knowledge_base", {}),
            code_skill=raw.get("code_skill", {}),
            cognitive_style=CognitiveStyle(
                preferred_modality=raw.get("cognitive_style", {}).get("preferred_modality", "visual"),
                depth=raw.get("cognitive_style", {}).get("depth", "deep"),
            ),
            focus_level=FocusLevel(
                avg_session_minutes=raw.get("focus_level", {}).get("avg_session_minutes", 0),
                streak_days=raw.get("focus_level", {}).get("streak_days", 0),
            ),
            learning_goals=[
                LearningGoal(
                    id=g.get("id", 0),
                    title=g.get("title", ""),
                    progress=g.get("progress", 0.0),
                    unit=g.get("unit", ""),
                    deadline=g.get("deadline"),
                )
                for g in raw.get("learning_goals", [])
            ],
            weakness=[
                Weakness(
                    subject=w.get("subject", ""),
                    topic=w.get("topic", ""),
                    mastery=w.get("mastery", 0.0),
                )
                for w in raw.get("weakness", [])
            ],
        )

    async def for_user(self, user_id: str) -> CapabilityProfile:
        repo = get_repository_for_user(user_id, repository_type="capability")
        raw = await repo.aggregate_profile(user_id)
        profile = await self.from_raw(raw)
        profile.user_id = user_id
        return profile