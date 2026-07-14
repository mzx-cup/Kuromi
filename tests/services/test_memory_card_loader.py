"""Tests for AgentMemoryCardSchema + CardField (Core Innovation 3).

The agent memory card layer packs up to 500 tokens of cross-layer
context (episodic, semantic, capability, supervision) so the LLM
sees the most relevant memory per turn without losing focus.
"""
from __future__ import annotations

import pytest


def test_socratic_schema_lists_4_fields():
    from app.services.agent.socratic_memory_card import socratic_schema

    schema = socratic_schema()
    assert schema.agent_id == "socratic"
    assert schema.total_max_tokens == 500
    assert len(schema.fields) == 4
    keys = [f.key for f in schema.fields]
    assert set(keys) == {
        "episodic_last",
        "capability_recent",
        "semantic_top3",
        "supervision_pending",
    }


def test_socratic_schema_max_tokens_sum_within_budget():
    from app.services.agent.socratic_memory_card import socratic_schema

    schema = socratic_schema()
    total = sum(f.max_tokens for f in schema.fields)
    # Allocations must total to at most the card budget (500).
    assert total <= 500
    # And the four fields should actually consume a meaningful share.
    assert total >= 400


def test_loader_respects_token_budget():
    from app.services.agent.memory_card_loader import (
        MemoryCardLoader,
        CardField,
    )

    long_text = "word " * 400  # ~400 tokens in the Latin heuristic
    fields = [
        CardField(
            key="episodic_last",
            source_layer="L2_episodic",
            query="recent unconsolidated event",
            max_tokens=100,
            ttl_seconds=300,
            value=long_text,
        ),
        CardField(
            key="capability_recent",
            source_layer="L5_capability",
            query="recent capability deltas",
            max_tokens=130,
            ttl_seconds=300,
            value=long_text,
        ),
        CardField(
            key="semantic_top3",
            source_layer="L2_semantic",
            query="top 3 semantic memories",
            max_tokens=150,
            ttl_seconds=300,
            value=long_text,
        ),
        CardField(
            key="supervision_pending",
            source_layer="L3_supervision",
            query="pending supervision items",
            max_tokens=120,
            ttl_seconds=300,
            value=long_text,
        ),
    ]
    card = MemoryCardLoader(total_max_tokens=500).pack(fields)
    assert card.token_count <= 500


def test_loader_truncates_by_priority():
    from app.services.agent.memory_card_loader import (
        MemoryCardLoader,
        CardField,
    )

    # Size the high-priority field so that even after truncation it
    # consumes almost all of the budget, leaving the lower-priority
    # field no room. 4000 chars ≈ 1000 tokens (Latin heuristic).
    # After truncation at 500 tokens: ~1500 chars remain, so the
    # episodic_last field (50 tokens) must still be dropped.
    high = "high" * 1000  # 4000 chars, ~1000 tokens
    low = "low" * 200     # 600 chars, ~150 tokens — exceeds remaining
    fields = [
        CardField(
            key="episodic_last",  # low priority
            source_layer="L2_episodic",
            query="q",
            max_tokens=100,
            ttl_seconds=300,
            value=low,
        ),
        CardField(
            key="supervision_pending",  # highest priority
            source_layer="L3_supervision",
            query="q",
            max_tokens=120,
            ttl_seconds=300,
            value=high,
        ),
    ]
    card = MemoryCardLoader(total_max_tokens=120).pack(fields)
    assert card.token_count <= 120
    # High-priority field is kept (truncated) and rendered.
    assert "### supervision_pending" in card.markdown
    assert "high" in card.markdown
    # Low-priority field is dropped because the budget was already
    # exhausted by the truncated high-priority field.
    assert "### episodic_last" not in card.markdown


def test_loader_preserves_priority_order_in_markdown():
    from app.services.agent.memory_card_loader import (
        MemoryCardLoader,
        CardField,
    )

    fields = [
        CardField(
            key="episodic_last",
            source_layer="L2_episodic",
            query="q",
            max_tokens=100,
            ttl_seconds=300,
            value="episodic body",
        ),
        CardField(
            key="supervision_pending",
            source_layer="L3_supervision",
            query="q",
            max_tokens=120,
            ttl_seconds=300,
            value="supervision body",
        ),
        CardField(
            key="capability_recent",
            source_layer="L5_capability",
            query="q",
            max_tokens=130,
            ttl_seconds=300,
            value="capability body",
        ),
        CardField(
            key="semantic_top3",
            source_layer="L2_semantic",
            query="q",
            max_tokens=150,
            ttl_seconds=300,
            value="semantic body",
        ),
    ]
    card = MemoryCardLoader(total_max_tokens=500).pack(fields)
    pos_sup = card.markdown.find("### supervision_pending")
    pos_eps = card.markdown.find("### episodic_last")
    assert pos_sup != -1 and pos_eps != -1
    assert pos_sup < pos_eps, "supervision_pending must come before episodic_last"


def test_loader_handles_empty_fields():
    from app.services.agent.memory_card_loader import MemoryCardLoader

    card = MemoryCardLoader(total_max_tokens=500).pack([])
    assert card.markdown == ""
    assert card.token_count == 0


def test_loader_falls_back_to_field_fallback_when_value_empty():
    from app.services.agent.memory_card_loader import (
        MemoryCardLoader,
        CardField,
    )

    fields = [
        CardField(
            key="supervision_pending",
            source_layer="L3_supervision",
            query="q",
            max_tokens=120,
            ttl_seconds=300,
            value="",  # fetch returned nothing
            fallback="(no pending supervision)",
        ),
    ]
    card = MemoryCardLoader(total_max_tokens=500).pack(fields)
    assert "(no pending supervision)" in card.markdown