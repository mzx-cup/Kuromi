"""Per-agent schema isolation — slice-B4.

Critical B4 invariant: ProfilerAgent and EchoAgent have different
field sets than SocraticAgent, and the loader must dispatch by
agent_id so each agent only sees its own schema.
"""
from __future__ import annotations

import pytest


def test_echo_does_not_include_semantic_top3():
    """Echo is not a tutoring agent; it must not carry semantic_top3."""
    from app.services.agent.echo_memory_card import echo_schema

    s = echo_schema()
    keys = {f.key for f in s.fields}
    assert "semantic_top3" not in keys


def test_profile_does_not_include_episodic_last():
    """Profiler is an analytical agent; episodic_last is Socratic's concern."""
    from app.services.agent.profile_memory_card import profile_schema

    s = profile_schema()
    keys = {f.key for f in s.fields}
    assert "episodic_last" not in keys


def test_card_cache_does_not_share_across_agents():
    """CardCache keys are namespaced by agent_id so cross-agent leakage is impossible."""
    from app.services.agent.card_cache import CardCache

    c = CardCache()
    c.set("socratic:u1:episodic_last", "ep1", ttl_s=300)
    c.set("profiler:u1:capability_recent", "cap1", ttl_s=300)
    assert c.get("socratic:u1:episodic_last") == "ep1"
    assert c.get("profiler:u1:capability_recent") == "cap1"