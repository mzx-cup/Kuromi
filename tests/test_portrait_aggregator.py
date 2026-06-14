# -*- coding: utf-8 -*-
"""Tests for portrait_aggregator.aggregate_portrait_snapshot.

6 维雷达 + 4 卡画像统一快照
- radar: knowledge_mastery / code_skill / cognitive_style / learning_goal / weakness / focus_level
- panel: learning_style / cognitive_level / current_goal / emotion_state
- last_synced: ISO 时间戳

Note: the new 6-dim LearningPortrait is the source of truth. It is NOT stored
on StudentState.profile (that is the legacy LearningProfile). The aggregator
accepts LearningPortrait directly.
"""

import pytest

from state import (
    LearningPortrait,
    KnowledgeMasteryPortrait,
    TopicMastery,
    CodeSkillPortrait,
    CognitiveStylePortrait,
    LearningGoalPortrait,
    WeaknessPortrait,
    FocusLevelPortrait,
)

from app.services.portrait_aggregator import aggregate_portrait_snapshot


def _portrait() -> LearningPortrait:
    """Build a populated LearningPortrait for tests."""
    return LearningPortrait(
        knowledge_mastery=KnowledgeMasteryPortrait(
            topics=[TopicMastery(name="t", level=0.8)],
            overall=0.8,
        ),
        code_skill=CodeSkillPortrait(level="intermediate"),
        cognitive_style=CognitiveStylePortrait(type="视觉型", confidence=0.7),
        learning_goal=LearningGoalPortrait(current="学会 Python"),
        weakness=WeaknessPortrait(areas=["递归"]),
        focus_level=FocusLevelPortrait(current="中等专注", trend="stable"),
    )


def test_snapshot_contains_radar_and_panel():
    snap = aggregate_portrait_snapshot(_portrait())
    assert "radar" in snap
    assert "panel" in snap
    assert "last_synced" in snap
    assert len(snap["radar"]) == 6
    assert set(snap["radar"].keys()) == {
        "knowledge_mastery", "code_skill", "cognitive_style",
        "learning_goal", "weakness", "focus_level",
    }


def test_radar_scores_clamped_0_100():
    snap = aggregate_portrait_snapshot(_portrait())
    for v in snap["radar"].values():
        assert 0 <= v <= 100, f"radar value {v} out of [0, 100]"


def test_panel_has_four_cards():
    snap = aggregate_portrait_snapshot(_portrait())
    assert set(snap["panel"].keys()) == {
        "learning_style", "cognitive_level", "current_goal", "emotion_state",
    }


def test_panel_current_goal_progress():
    snap = aggregate_portrait_snapshot(_portrait())
    goal = snap["panel"]["current_goal"]
    assert goal["label"] == "学会 Python"
    assert "progress_pct" in goal
    assert 0 <= goal["progress_pct"] <= 100


def test_last_synced_is_iso_format():
    snap = aggregate_portrait_snapshot(_portrait())
    # ISO format with timezone, e.g. "2026-06-14T10:00:00+00:00"
    from datetime import datetime
    # Should be parseable as ISO datetime
    parsed = datetime.fromisoformat(snap["last_synced"])
    assert parsed is not None


def test_telemetry_affects_focus_and_emotion():
    # No telemetry: focus should be base, emotion should be calm
    base = aggregate_portrait_snapshot(_portrait())
    # High idle telemetry: focus drops, emotion becomes frustrated
    snap = aggregate_portrait_snapshot(
        _portrait(),
        telemetry={"mouse_idle_ms": 10000, "scroll_speed": 100, "zone_dwell_ms": 5000},
    )
    assert snap["radar"]["focus_level"] <= base["radar"]["focus_level"]
    assert snap["panel"]["emotion_state"]["label"] == "frustrated"


def test_empty_portrait_does_not_crash():
    """Empty LearningPortrait should produce a valid (all-zero) snapshot."""
    snap = aggregate_portrait_snapshot(LearningPortrait())
    assert "radar" in snap
    assert "panel" in snap
    assert all(v >= 0 for v in snap["radar"].values())
