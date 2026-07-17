"""ProfilerAgent memory card schema — slice-B4."""
from __future__ import annotations

from app.services.agent.memory_card_loader import CardField, CardSchema


# Per-field budget allocation. Total = 180 + 120 + 150 = 450 (within 500).
# ``weakness_top5`` gets the largest share because it is the most
# actionable signal for downstream tutoring agents. ``semantic_top3``
# follows because it carries the most reusable long-term context.
_FIELD_BUDGETS: dict[str, int] = {
    "weakness_top5": 180,
    "capability_recent": 120,
    "semantic_top3": 150,
}


def profile_schema() -> CardSchema:
    """Return the canonical CardSchema for the Profiler agent."""
    fields = [
        CardField(
            key="weakness_top5",
            source_layer="L4_weakness",
            query="user's 5 weakest topics (last 30 days)",
            max_tokens=_FIELD_BUDGETS["weakness_top5"],
            ttl_seconds=900,
            fallback="(no weakness data)",
        ),
        CardField(
            key="capability_recent",
            source_layer="L4_capability",
            query="user's capability deltas (last 7 days)",
            max_tokens=_FIELD_BUDGETS["capability_recent"],
            ttl_seconds=600,
            fallback="(no capability data)",
        ),
        CardField(
            key="semantic_top3",
            source_layer="L2_semantic",
            query="user's top-3 semantic memory entries by relevance",
            max_tokens=_FIELD_BUDGETS["semantic_top3"],
            ttl_seconds=300,
            fallback="(no semantic memory)",
        ),
    ]
    return CardSchema(
        agent_id="profiler",
        fields=fields,
        total_max_tokens=500,
    )