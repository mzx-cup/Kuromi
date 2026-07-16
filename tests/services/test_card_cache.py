"""Tests for CardCache — slice-A3."""
from __future__ import annotations


def test_cache_set_then_get():
    from app.services.agent.card_cache import CardCache
    c = CardCache()
    c.set("socratic:u-1:episodic_last", "ep text", ttl_s=300)
    assert c.get("socratic:u-1:episodic_last") == "ep text"


def test_cache_miss_returns_none():
    from app.services.agent.card_cache import CardCache
    c = CardCache()
    assert c.get("nope") is None


def test_cache_ttl_expired(monkeypatch):
    from app.services.agent.card_cache import CardCache
    import app.services.agent.card_cache as card_cache_mod
    c = CardCache()
    # t=0
    monkeypatch.setattr(card_cache_mod.time, "time", lambda: 0.0)
    c.set("k", "v1", ttl_s=10)
    assert c.get("k") == "v1"
    # 模拟时钟前进到 t=20（已超过 ttl=10s）
    monkeypatch.setattr(card_cache_mod.time, "time", lambda: 20.0)
    assert c.get("k") is None


def test_cache_overwrite_replaces():
    from app.services.agent.card_cache import CardCache
    c = CardCache()
    c.set("k", "v1", ttl_s=300)
    c.set("k", "v2", ttl_s=300)
    assert c.get("k") == "v2"
