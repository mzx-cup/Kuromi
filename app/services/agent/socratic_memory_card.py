"""Socratic agent card schema — 4 fields packed into a <= 500 token card.

This is the L2 memory-card schema consumed by SocraticAgent. Each
field declares which layer it pulls from, a per-field budget, a TTL
for caching, and a fallback string for when the fetcher returns
nothing. The actual fetcher wiring happens in S9.
"""
from __future__ import annotations

from app.services.agent.memory_card_loader import CardField, CardSchema


# Per-field budget allocation. Total = 100 + 130 + 150 + 120 = 500.
# ``supervision_pending`` is the most actionable signal (user needs
# intervention), so it gets the largest share after the top slot.
# ``semantic_top3`` carries the most reusable context. ``episodic_last``
# is kept smallest because single recent events are usually brief.
_FIELD_BUDGETS: dict[str, int] = {
    "supervision_pending": 120,
    "semantic_top3": 150,
    "capability_recent": 130,
    "episodic_last": 100,
}


def socratic_schema() -> CardSchema:
    """Return the canonical CardSchema for the Socratic agent."""
    fields = [
        CardField(
            key="episodic_last",
            source_layer="L2_episodic",
            query="user's most recent unconsolidated episodic event",
            max_tokens=_FIELD_BUDGETS["episodic_last"],
            ttl_seconds=300,
            fallback="(no recent episode)",
        ),
        CardField(
            key="capability_recent",
            source_layer="L5_capability",
            query="user's recent capability deltas (last 7 days)",
            max_tokens=_FIELD_BUDGETS["capability_recent"],
            ttl_seconds=300,
            fallback="(no capability delta)",
        ),
        CardField(
            key="semantic_top3",
            source_layer="L2_semantic",
            query="user's top-3 semantic memory entries by relevance",
            max_tokens=_FIELD_BUDGETS["semantic_top3"],
            ttl_seconds=300,
            fallback="(no semantic memory)",
        ),
        CardField(
            key="supervision_pending",
            source_layer="L3_supervision",
            query="user's pending supervision items requiring attention",
            max_tokens=_FIELD_BUDGETS["supervision_pending"],
            ttl_seconds=300,
            fallback="(no pending supervision)",
        ),
    ]
    return CardSchema(
        agent_id="socratic",
        fields=fields,
        total_max_tokens=500,
    )