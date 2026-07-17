"""EchoAgent memory card schema — slice-B4."""
from __future__ import annotations

from app.services.agent.memory_card_loader import CardField, CardSchema


# Per-field budget allocation. Total = 120 + 80 = 200 (well within 500).
# Echo is not a tutoring agent: it uses minimal context to compose a
# lightweight greeting/check-in. ``episodic_last`` provides the most
# recent user event for tone; ``user_preferences`` carries the user's
# preferred greeting style.
_FIELD_BUDGETS: dict[str, int] = {
    "episodic_last": 120,
    "user_preferences": 80,
}


def echo_schema() -> CardSchema:
    """Return the canonical CardSchema for the Echo agent."""
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
            key="user_preferences",
            source_layer="L5_preferences",
            query="user's greeting preferences",
            max_tokens=_FIELD_BUDGETS["user_preferences"],
            ttl_seconds=1800,
            fallback="(no preferences)",
        ),
    ]
    return CardSchema(
        agent_id="echo",
        fields=fields,
        total_max_tokens=500,
    )