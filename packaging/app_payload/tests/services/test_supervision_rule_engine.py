"""S7.3 — RuleEngine + ChannelDispatcher tests (L3 supervision layer).

These tests use the ``patch.object(svc, "RepositoryClass")`` pattern
(matching ``test_weakness_timeline.py``). The ActionLedger cooldown is
replaced with an in-memory fake injected directly.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

from app.services.supervision import channel_dispatcher as ch
from app.services.supervision import rule_engine as eng


# ---------------------------------------------------------------------------
# S7.3.a — ChannelDispatcher
# ---------------------------------------------------------------------------


def test_channel_dispatcher_format_template():
    rule = {"name": "practice_prompt", "id": "SUP-001"}
    step = {
        "step": 1,
        "delay_hours": 0,
        "channels": ["inapp"],
        "template": "Hi {user_id}, try {topic} now!",
    }
    out = ch.dispatch(
        event=None, step=step, rule=rule, user_id="u-42", ctx={"topic": "loops"},
    )
    assert len(out) == 1
    assert out[0]["channel"] == "inapp"
    assert out[0]["message"] == "Hi u-42, try loops now!"


def test_channel_dispatcher_handles_multiple_channels():
    step = {
        "step": 2,
        "delay_hours": 24,
        "channels": ["inapp", "push", "email"],
        "template": "{name}",
    }
    out = ch.dispatch(
        event=None, step=step, rule={"id": "SUP-X"}, user_id="u", ctx={"name": "x"},
    )
    assert [r["channel"] for r in out] == ["inapp", "push", "email"]
    assert all(r["message"] == "x" for r in out)


def test_channel_dispatcher_handles_unknown_channel_string():
    """Forward-compatible: any string channel is accepted and recorded."""
    step = {"step": 1, "channels": ["slack"], "template": "hi"}
    out = ch.dispatch(
        event=None, step=step, rule={}, user_id="u", ctx={},
    )
    assert out[0]["channel"] == "slack"


# ---------------------------------------------------------------------------
# S7.3.b — RuleEngine (with patched repos + ActionLedger substitute)
# ---------------------------------------------------------------------------


class _FakeLedger:
    def __init__(self, recently: bool = False) -> None:
        self._recently = recently
        self.recorded: list[tuple[str, str, str]] = []

    def recently_exposed(self, user_id, action_type, **kwargs):
        return self._recently

    def record_exposure(self, user_id, action_type, source):
        self.recorded.append((user_id, action_type, source))


class _StubScheduler:
    def __init__(self) -> None:
        self.jobs: list[dict] = []

    def schedule_step(self, event_id: int, step: int, rule_id: str, delay_hours: int):
        self.jobs.append(
            {"event_id": event_id, "step": step, "rule_id": rule_id,
             "delay_hours": delay_hours}
        )


def _make_rule(rule_id: str, dsl: str, *, cooldown_hours: int = 24,
               chain_steps: int = 2) -> dict:
    steps = [
        {"step": i + 1, "delay_hours": 0 if i == 0 else 24 * i,
         "channels": ["inapp"], "template": "step-{step}: {user_id}"}
        for i in range(chain_steps)
    ]
    return {
        "id": rule_id,
        "name": f"legacy:{rule_id.lower()}",
        "description": "",
        "enabled": True,
        "priority": 100,
        "trigger_dsl": dsl,
        "context_keys": [],
        "cooldown_hours": cooldown_hours,
        "escalation_chain": {"steps": steps},
    }


def test_rule_engine_triggers_on_dsl_match():
    rule = _make_rule("SUP-001", "weakness < 0.4")
    with patch.object(eng, "OrmSupervisionRuleRepository") as MockRuleRepo, \
         patch.object(eng, "OrmSupervisionEventRepository") as MockEventRepo:
        MockRuleRepo.return_value.list_enabled.return_value = [rule]
        MockEventRepo.return_value.insert.return_value = 100
        ledger = _FakeLedger(recently=False)
        sched = _StubScheduler()
        eng.evaluate_all_active_users(
            user_ids=["u-1"],
            context_builder=lambda uid: {"weakness": 0.3, "user_id": uid},
            ledger=ledger,
            scheduler=sched,
        )
        MockEventRepo.return_value.insert.assert_called_once()
        event = MockEventRepo.return_value.insert.call_args[0][0]
        assert event.rule_id == "SUP-001"
        assert event.user_id == "u-1"
        assert event.status == "fired"
        assert event.current_step == 1


def test_rule_engine_skips_on_dsl_false():
    rule = _make_rule("SUP-002", "weakness < 0.4")
    with patch.object(eng, "OrmSupervisionRuleRepository") as MockRuleRepo, \
         patch.object(eng, "OrmSupervisionEventRepository") as MockEventRepo:
        MockRuleRepo.return_value.list_enabled.return_value = [rule]
        ledger = _FakeLedger()
        sched = _StubScheduler()
        eng.evaluate_all_active_users(
            user_ids=["u-1"],
            context_builder=lambda uid: {"weakness": 0.9, "user_id": uid},
            ledger=ledger,
            scheduler=sched,
        )
        MockEventRepo.return_value.insert.assert_not_called()


def test_rule_engine_skips_on_dsl_exception():
    rule = _make_rule("SUP-003", "garbled !!")
    with patch.object(eng, "OrmSupervisionRuleRepository") as MockRuleRepo, \
         patch.object(eng, "OrmSupervisionEventRepository") as MockEventRepo:
        MockRuleRepo.return_value.list_enabled.return_value = [rule]
        ledger = _FakeLedger()
        sched = _StubScheduler()
        eng.evaluate_all_active_users(
            user_ids=["u-1"],
            context_builder=lambda uid: {"user_id": uid},
            ledger=ledger,
            scheduler=sched,
        )
        MockEventRepo.return_value.insert.assert_not_called()


def test_rule_engine_respects_cooldown():
    rule = _make_rule("SUP-004", "weakness < 0.4")
    with patch.object(eng, "OrmSupervisionRuleRepository") as MockRuleRepo, \
         patch.object(eng, "OrmSupervisionEventRepository") as MockEventRepo:
        MockRuleRepo.return_value.list_enabled.return_value = [rule]
        ledger = _FakeLedger(recently=True)
        sched = _StubScheduler()
        eng.evaluate_all_active_users(
            user_ids=["u-1"],
            context_builder=lambda uid: {"weakness": 0.3, "user_id": uid},
            ledger=ledger,
            scheduler=sched,
        )
        MockEventRepo.return_value.insert.assert_not_called()


def test_rule_engine_inserts_supervision_event_with_correct_status():
    rule = _make_rule("SUP-005", "weakness < 0.4")
    with patch.object(eng, "OrmSupervisionRuleRepository") as MockRuleRepo, \
         patch.object(eng, "OrmSupervisionEventRepository") as MockEventRepo:
        MockRuleRepo.return_value.list_enabled.return_value = [rule]
        MockEventRepo.return_value.insert.return_value = 999
        ledger = _FakeLedger()
        sched = _StubScheduler()
        eng.evaluate_all_active_users(
            user_ids=["u-1"],
            context_builder=lambda uid: {"weakness": 0.3, "user_id": uid},
            ledger=ledger,
            scheduler=sched,
        )
        ev = MockEventRepo.return_value.insert.call_args[0][0]
        assert ev.status == "fired"
        assert ev.current_step == 1


def test_rule_engine_dispatches_step1_channels():
    rule = _make_rule("SUP-006", "weakness < 0.4", chain_steps=3)
    with patch.object(eng, "OrmSupervisionRuleRepository") as MockRuleRepo, \
         patch.object(eng, "OrmSupervisionEventRepository") as MockEventRepo:
        MockRuleRepo.return_value.list_enabled.return_value = [rule]
        MockEventRepo.return_value.insert.return_value = 1
        ledger = _FakeLedger()
        sched = _StubScheduler()
        eng.evaluate_all_active_users(
            user_ids=["u-9"],
            context_builder=lambda uid: {"weakness": 0.1, "user_id": uid},
            ledger=ledger,
            scheduler=sched,
        )
        assert len(sched.jobs) == 2
        step_jobs = [j for j in sched.jobs if j["step"] in (2, 3)]
        assert len(step_jobs) == 2
        delays = sorted(j["delay_hours"] for j in step_jobs)
        assert delays == [24, 48]
