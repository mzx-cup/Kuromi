"""slice-B1 — S7 supervision flow E2E (rule engine + escalation + dispatch).

These 6 cases exercise the real supervision APIs end-to-end. The plan's
original snippet used a hypothetical ``SupervisionRuleEngine.evaluate_for_user``
/ ``record_eval_failure`` API that does not exist in this codebase; the
tests below are adapted to the actual public surface:

  * ``rule_engine.evaluate_all_active_users`` (module function, injectable
    repos / ledger / scheduler)
  * ``EscalationChain`` (schedule step 2/3, cancel on response)
  * ``channel_dispatcher.dispatch`` (format + retry-with-backoff sender)
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.models.supervision import SupervisionEvent, SupervisionRule
from app.services.supervision import channel_dispatcher as ch
from app.services.supervision import rule_engine as eng
from app.services.supervision.escalation_chain import EscalationChain


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_STALE_DSL = "today_minutes == 0 and days_since_last >= 3"


def _rule(
    rule_id: str = "R-001",
    dsl: str = _STALE_DSL,
    *,
    enabled: bool = True,
    cooldown_hours: int = 24,
    chain_steps: int = 3,
) -> SupervisionRule:
    steps = [
        {
            "step": i + 1,
            "delay_hours": 0 if i == 0 else 24 * i,
            "channels": ["inapp"],
            "template": "step-{step}: {user_id}",
        }
        for i in range(chain_steps)
    ]
    return SupervisionRule(
        id=rule_id,
        name="stale_3d",
        description="3 days inactive",
        enabled=enabled,
        priority=10,
        trigger_dsl=dsl,
        context_keys=[],
        cooldown_hours=cooldown_hours,
        escalation_chain={"steps": steps},
    )


class _FakeLedger:
    def __init__(self, recently: bool = False) -> None:
        self._recently = recently
        self.recorded: list[tuple] = []

    def recently_exposed(self, user_id, action_type, **kw):
        return self._recently

    def record_exposure(self, user_id, action_type, source):
        self.recorded.append((user_id, action_type, source))


class _StubScheduler:
    def __init__(self) -> None:
        self.jobs: list[tuple] = []

    def schedule_step(self, event_id, step, rule_id, delay_hours):
        self.jobs.append((event_id, step, rule_id, delay_hours))


def _stale_ctx(uid: str) -> dict:
    return {"today_minutes": 0, "days_since_last": 4, "user_id": uid}


# ---------------------------------------------------------------------------
# case 1 — step 1 fires
# ---------------------------------------------------------------------------


def test_e2e_step1_fires():
    with patch.object(eng, "OrmSupervisionRuleRepository") as MRule, \
         patch.object(eng, "OrmSupervisionEventRepository") as MEvent:
        MRule.return_value.list_enabled.return_value = [_rule()]
        MEvent.return_value.insert.return_value = 100
        ch.reset_sent_log()
        res = eng.evaluate_all_active_users(
            user_ids=["u-stale"],
            context_builder=_stale_ctx,
            ledger=_FakeLedger(),
            scheduler=_StubScheduler(),
        )
        assert res["fired_count"] == 1
        ev = MEvent.return_value.insert.call_args[0][0]
        assert ev.rule_id == "R-001"
        assert ev.current_step == 1
        assert ev.status == "fired"


# ---------------------------------------------------------------------------
# case 2 — user responds → step 2/3 cancelled
# ---------------------------------------------------------------------------


def test_e2e_step2_cancel_after_respond():
    calls: list[tuple] = []
    chain = EscalationChain(
        scheduler=lambda eid, step, hours: calls.append(("sched", eid, step, hours)),
        canceller=lambda eid, step: calls.append(("cancel", eid, step)),
    )
    event = SupervisionEvent(
        id=7, rule_id="R-001", user_id="u-stale", current_step=1, status="fired",
    )
    chain.schedule_steps(event)
    cancelled = chain.user_responded(event.id)

    assert cancelled == 2
    assert ("cancel", 7, 2) in calls
    assert ("cancel", 7, 3) in calls
    # default no-op chain also cancels both steps without raising
    assert EscalationChain().user_responded(999) == 2


# ---------------------------------------------------------------------------
# case 3 — channel dispatch retries transient failures with backoff
# ---------------------------------------------------------------------------


def test_e2e_channel_retry_after_failure(monkeypatch):
    monkeypatch.setattr(ch.time, "sleep", lambda _s: None)  # skip real backoff
    attempts = {"n": 0}

    def flaky(channel, message):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("transient")

    ch.reset_sent_log()
    out = ch.dispatch(
        event=SupervisionEvent(
            id=1, rule_id="r", user_id="u", current_step=1, status="fired",
        ),
        step={"step": 1, "channels": ["push"], "template": "hi {user_id}"},
        rule={"id": "r"},
        user_id="u",
        ctx={},
        sender=flaky,
    )
    assert attempts["n"] == 3  # failed twice, succeeded on the 3rd attempt
    assert out[0]["channel"] == "push"
    assert len(ch.list_sent()) == 1  # recorded once, only after success


def test_e2e_channel_retry_exhausts_and_raises(monkeypatch):
    monkeypatch.setattr(ch.time, "sleep", lambda _s: None)

    def always_fail(channel, message):
        raise RuntimeError("down")

    ch.reset_sent_log()
    with pytest.raises(RuntimeError, match="down"):
        ch.dispatch(
            event=None,
            step={"step": 1, "channels": ["push"], "template": "x"},
            rule={"id": "r"},
            user_id="u",
            ctx={},
            sender=always_fail,
            max_retries=3,
        )
    assert ch.list_sent() == []  # nothing recorded on total failure


# ---------------------------------------------------------------------------
# case 4 — a rule whose DSL raises is skipped, others keep firing
# ---------------------------------------------------------------------------


def test_e2e_eval_exception_keeps_safe():
    bad = _rule("B-1", "a +", chain_steps=1)  # syntax error → skip
    good = _rule("G-1", _STALE_DSL)
    with patch.object(eng, "OrmSupervisionRuleRepository") as MRule, \
         patch.object(eng, "OrmSupervisionEventRepository") as MEvent:
        MRule.return_value.list_enabled.return_value = [bad, good]
        MEvent.return_value.insert.return_value = 1
        res = eng.evaluate_all_active_users(
            user_ids=["u"],
            context_builder=lambda uid: {
                "today_minutes": 0, "days_since_last": 5, "a": 1, "user_id": uid,
            },
            ledger=_FakeLedger(),
            scheduler=_StubScheduler(),
        )
        assert res["fired_count"] == 1  # only the good rule fired
        ev = MEvent.return_value.insert.call_args[0][0]
        assert ev.rule_id == "G-1"


# ---------------------------------------------------------------------------
# case 5 — escalation delays default to 24h / 72h
# ---------------------------------------------------------------------------


def test_e2e_step_2_24h_delay():
    chain = EscalationChain(step_delays_h=(24, 72))
    assert chain._delays == (24, 72)

    scheduled: list[tuple] = []
    chain2 = EscalationChain(
        scheduler=lambda eid, step, hours: scheduled.append((step, hours)),
    )
    chain2.schedule_steps(
        SupervisionEvent(id=1, rule_id="r", user_id="u", current_step=1, status="fired"),
    )
    assert (2, 24) in scheduled
    assert (3, 72) in scheduled


# ---------------------------------------------------------------------------
# case 6 — cooldown fail-safe: recently-exposed user is not re-fired
# ---------------------------------------------------------------------------


def test_e2e_stop_condition_fail_safe():
    """Anti-spam stop condition — cooldown blocks a repeat fire."""
    with patch.object(eng, "OrmSupervisionRuleRepository") as MRule, \
         patch.object(eng, "OrmSupervisionEventRepository") as MEvent:
        MRule.return_value.list_enabled.return_value = [_rule()]
        res = eng.evaluate_all_active_users(
            user_ids=["u-stale"],
            context_builder=lambda uid: {
                "today_minutes": 0, "days_since_last": 9, "user_id": uid,
            },
            ledger=_FakeLedger(recently=True),  # cooldown active
            scheduler=_StubScheduler(),
        )
        assert res["fired_count"] == 0
        MEvent.return_value.insert.assert_not_called()
