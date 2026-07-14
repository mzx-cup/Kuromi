"""Tests for HealthProbe L0-L4 state machine."""
import pytest
from app.services.health.health_probe import HealthProbe, Level


def test_health_probe_initial_level_is_L0():
    p = HealthProbe(component="qdrant")
    assert p.current_level == Level.L0


def test_health_probe_downgrades_on_3_failures():
    p = HealthProbe(component="qdrant", downgrade_fails=3, upgrade_passes=6)
    p.record(False)
    p.record(False)
    p.record(False)
    assert p.current_level == Level.L3


def test_health_probe_upgrades_on_6_passes_after_downgrade():
    p = HealthProbe(component="qdrant", downgrade_fails=3, upgrade_passes=6)
    for _ in range(3):
        p.record(False)
    assert p.current_level == Level.L3
    for _ in range(6):
        p.record(True)
    assert p.current_level == Level.L0


def test_health_probe_no_flicker_on_alternating_signals():
    """Jitter must NOT cause a downgrade when calls alternate pass/fail."""
    p = HealthProbe(component="qdrant", downgrade_fails=3)
    p.record(False)
    p.record(True)
    p.record(False)
    p.record(True)
    assert p.current_level == Level.L0
