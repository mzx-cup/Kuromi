from app.services.claude_card.cache import ClaudeCardCache
from app.services.claude_card.packer import pack


def test_cache_hit_skips_reload():
    c = ClaudeCardCache()
    c.set("abc123", "cached md")
    assert c.get("abc123") == "cached md"


def test_cache_ttl_expired():
    c = ClaudeCardCache()
    c.set("abc", "v1")
    assert c.get("abc") == "v1"
    # Force-expire: rewrite with old timestamp
    c._store["abc"] = (0, "v1")  # written at epoch; >3600s ago
    assert c.get("abc") is None


def test_packer_under_3kb():
    md = pack("abc123", {
        "slices": "X" * 500,
        "adrs": "Y" * 500,
        "git": "Z" * 5000,  # over-budget; will truncate
        "drift": "D" * 500,
        "consol": "C" * 500,
    })
    # 3KB + 100 byte overhead tolerance
    assert len(md.encode("utf-8")) <= 3100


def test_drift_and_consol_fallback_on_error():
    """Drift/Consolidation DB errors return fallback placeholder string."""
    from app.services.claude_card.loader import _drift_reports, _consolidation_log
    from unittest.mock import patch
    # drift DB unavailable
    with patch("app.services.claude_card.loader.OrmDriftReportRepository",
               side_effect=RuntimeError("db down"), create=True):
        s = _drift_reports()
    assert "unreachable" in s.lower() or "no" in s.lower()
    # consol DB unavailable
    with patch("app.services.claude_card.loader.OrmAgentBehaviorLogRepository",
               side_effect=RuntimeError("db down"), create=True):
        s = _consolidation_log()
    assert "unreachable" in s.lower() or "no" in s.lower()
