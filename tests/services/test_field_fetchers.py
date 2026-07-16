"""Tests for FieldFetchers — slice-A3."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.agent.field_fetchers import FieldFetchers


@pytest.fixture
def fetchers():
    repos = {
        "episodic": MagicMock(),
        "capability": MagicMock(),
        "semantic": MagicMock(),
        "supervision": MagicMock(),
    }
    repos["episodic"].recent_unconsolidated.return_value = []
    repos["capability"].recent.return_value = []
    repos["semantic"].top_by_confidence.return_value = []
    repos["supervision"].list_pending.return_value = []
    return FieldFetchers(repos)


def test_four_fetchers_all_keys(fetchers):
    out = fetchers.fetch_all("u-1")
    assert set(out.keys()) == {
        "episodic_last", "capability_recent",
        "semantic_top3", "supervision_pending",
    }


def test_priority_order(fetchers):
    """4 字段优先级降序：supervision > semantic > capability > episodic"""
    out = fetchers.fetch_all("u-1")
    keys = list(out.keys())
    # Remove partial_fields from order assertion
    field_keys = [k for k in keys if k != "partial_fields"]
    assert field_keys.index("supervision_pending") < field_keys.index("semantic_top3")
    assert field_keys.index("semantic_top3") < field_keys.index("capability_recent")
    assert field_keys.index("capability_recent") < field_keys.index("episodic_last")


def test_fetcher_timeout_uses_fallback(fetchers):
    """某 fetcher 抛异常 → 用 fallback"""
    fetchers._repos["episodic"].recent_unconsolidated.side_effect = RuntimeError("db down")
    out = fetchers.fetch_all("u-1")
    assert "(no recent episode)" in out["episodic_last"]
    assert out["semantic_top3"] != ""  # 其他字段 OK


def test_partial_fields_marker(fetchers):
    """fail 时 partial_fields 包含失败 key"""
    fetchers._repos["episodic"].recent_unconsolidated.side_effect = RuntimeError("e")
    fetchers.fetch_all("u-1")
    assert "episodic_last" in fetchers.last_partial_fields


def test_all_fetchers_fail_returns_empty_strings(fetchers):
    for repo in fetchers._repos.values():
        for attr in [
            "recent_unconsolidated", "recent",
            "top_by_confidence", "list_pending",
        ]:
            if hasattr(repo, attr):
                getattr(repo, attr).side_effect = RuntimeError("down")
    out = fetchers.fetch_all("u-1")
    # 4 个字段全部 fallback（非空字符串）
    assert all(out[k] for k in [
        "episodic_last", "capability_recent",
        "semantic_top3", "supervision_pending",
    ])
    # all four in partial_fields
    assert set(fetchers.last_partial_fields) == {
        "episodic_last", "capability_recent",
        "semantic_top3", "supervision_pending",
    }


def test_total_under_500_tokens(fetchers):
    """即使 4 字段都填长内容，总长度 sanity check 通过"""
    fetchers._repos["episodic"].recent_unconsolidated.return_value = [
        {"summary": "x" * 500}, {"summary": "y" * 500},
    ]
    out = fetchers.fetch_all("u-1")
    full = " ".join(out[k] for k in out if k != "partial_fields")
    assert len(full) < 8000


def test_unknown_field_key_raises(fetchers):
    """未注册字段抛 KeyError"""
    with pytest.raises(KeyError):
        fetchers.fetch_one("u-1", "unknown_field_xyz")
