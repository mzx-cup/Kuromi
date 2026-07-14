"""EpisodicMemory service — record_event + recent_unconsolidated."""
from __future__ import annotations

from typing import Optional, Any

from app.models.episodic_memory import EpisodicMemory
from app.repositories.orm.episodic_memory import OrmEpisodicMemoryRepository


def record_event(
    user_id: str,
    event_type: str,
    summary: str,
    event_metadata: Optional[dict] = None,
) -> int:
    """Record a single episodic event for the user and return its id.

    ``event_metadata`` defaults to ``None`` so the model stores SQL
    NULL (rather than an empty ``{}``); downstream consumers can
    distinguish "no metadata" from "explicitly empty metadata".
    ``consolidated_into`` defaults to ``None`` (unconsolidated).
    """
    repo = OrmEpisodicMemoryRepository()
    entry = EpisodicMemory(
        user_id=user_id,
        event_type=event_type,
        summary=summary,
        event_metadata=event_metadata,
        consolidated_into=None,
    )
    return repo.insert(entry)


def recent_unconsolidated(
    user_id: str, days: int = 7,
) -> list[EpisodicMemory]:
    """Return episodes for ``user_id`` within the last ``days`` days
    that have not yet been consolidated into a ``SemanticMemory`` row.

    Ordered chronologically (oldest first).
    """
    repo = OrmEpisodicMemoryRepository()
    return repo.recent_unconsolidated(user_id=user_id, days=days)