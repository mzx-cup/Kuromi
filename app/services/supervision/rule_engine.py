"""S7.3 — Supervision rule engine.

Iterates enabled ``SupervisionRule`` rows against active users, evaluates
the DSL trigger against a per-user context, respects the per-rule
``cooldown_hours`` (delegated to ``ActionLedger``), and creates a
``SupervisionEvent`` (status="fired", ``current_step=1``) when the
trigger fires.

Step-2+ deliveries are *scheduled*, not eagerly sent — the scheduler
is a thin callable interface so unit tests can use an in-memory stub.
Production wiring (APScheduler / Celery) lands in a later slice.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Iterable, Optional

from app.models.supervision import SupervisionEvent, SupervisionRule
from app.repositories.orm.supervision import (
    OrmSupervisionEventRepository,
    OrmSupervisionRuleRepository,
)
from app.services.supervision import channel_dispatcher
from app.services.supervision.dsl import safe_eval


_log = logging.getLogger(__name__)


class ActionLedgerLike:
    """Protocol-style hint — production code passes a real ``ActionLedger``.

    Tests substitute ``_FakeLedger`` from ``test_supervision_rule_engine``.
    """

    def recently_exposed(self, user_id: str, action_type: str, **kw) -> bool: ...
    def record_exposure(self, user_id: str, action_type: str, source: str) -> None: ...


class SchedulerLike:
    """Protocol-style hint — tests pass ``_StubScheduler``."""

    def schedule_step(self, event_id: int, step: int, rule_id: str,
                      delay_hours: int) -> None: ...


def _list_active_user_ids() -> list[str]:
    """S7.3 stub: hard-coded single demo user.

    Replaced with ``CapabilityProfileRepository.list_active_user_ids``
    when the cold-start slice (S11) lands.
    """
    return ["u-demo-user"]


def _default_context_builder(user_id: str) -> dict[str, Any]:
    """S7.3 stub: fixed-shape context so the DSL has something to navigate.

    The DSL only requires the keys it actually references, so this stub
    is intentionally minimal. Real context (L4 weakness, deadlines,
    LearningState) lands in a follow-up slice once the orchestration
    wiring is in place.
    """
    return {
        "user_id": user_id,
        "weakness": 0.5,
        "today_minutes": 30,
        "days_since_last": 1,
        "topic": "",
    }


def _coerce_rule(rule: Any) -> dict[str, Any]:
    """Allow callers to pass either an ORM model or a plain dict (seeder)."""
    if isinstance(rule, dict):
        return rule
    return {
        "id": rule.id,
        "name": rule.name,
        "trigger_dsl": rule.trigger_dsl,
        "cooldown_hours": rule.cooldown_hours,
        "escalation_chain": rule.escalation_chain or {},
        "priority": rule.priority,
    }


def _build_event(rule_dict: dict[str, Any], user_id: str) -> SupervisionEvent:
    now = datetime.utcnow()
    return SupervisionEvent(
        rule_id=rule_dict["id"],
        user_id=user_id,
        current_step=1,
        status="fired",
        fired_at=now,
        last_step_at=now,
        metadata_={"rule_name": rule_dict.get("name", ""), "step_history": [1]},
    )


def _step_for(chain: dict[str, Any], step_idx: int) -> Optional[dict[str, Any]]:
    for s in chain.get("steps") or []:
        if int(s.get("step", 0)) == step_idx:
            return s
    return None


def _fire_for_user(
    *,
    rule_dict: dict[str, Any],
    user_id: str,
    ctx: dict[str, Any],
    event_repo: Any,
    ledger: ActionLedgerLike,
    scheduler: SchedulerLike,
    now: datetime,
) -> bool:
    """Evaluate trigger for ``user_id``, return True iff event inserted."""
    try:
        triggered = bool(safe_eval(rule_dict["trigger_dsl"], ctx))
    except Exception as exc:  # noqa: BLE001 — any DSL error → safe skip
        _log.warning(
            "rule_engine: DSL eval failed (rule=%s user=%s exc=%s)",
            rule_dict.get("id"), user_id, exc,
        )
        return False

    if not triggered:
        return False

    cooldown_hours = int(rule_dict.get("cooldown_hours") or 24)
    if ledger.recently_exposed(user_id, rule_dict["id"], hours=cooldown_hours):
        return False

    event = _build_event(rule_dict, user_id)
    event_id = event_repo.insert(event)

    chain = rule_dict.get("escalation_chain") or {}
    step1 = _step_for(chain, 1)
    if step1 is not None:
        channel_dispatcher.dispatch(
            event=event, step=step1, rule=rule_dict, user_id=user_id, ctx=ctx,
        )
        ledger.record_exposure(user_id, rule_dict["id"], "supervision_step1")

    for step_idx in range(2, len(chain.get("steps") or []) + 1):
        step = _step_for(chain, step_idx)
        if step is None:
            continue
        delay_hours = int(step.get("delay_hours") or 0)
        scheduler.schedule_step(event_id, step_idx, rule_dict["id"], delay_hours)

    _log.info(
        "rule_engine: triggered (rule=%s user=%s event_id=%s)",
        rule_dict["id"], user_id, event_id,
    )
    return True


def evaluate_all_active_users(
    *,
    user_ids: Optional[Iterable[str]] = None,
    context_builder: Optional[Callable[[str], dict[str, Any]]] = None,
    rule_repo_factory: Optional[Callable[[], Any]] = None,
    event_repo_factory: Optional[Callable[[], Any]] = None,
    ledger: Optional[ActionLedgerLike] = None,
    scheduler: Optional[SchedulerLike] = None,
) -> dict[str, Any]:
    """Evaluate every enabled rule against every active user.

    ``user_ids``, ``context_builder``, ``rule_repo_factory``,
    ``event_repo_factory``, ``ledger``, ``scheduler`` are all injection
    points for testing. Production callers pass ``None`` for the
    factories (they default to ``OrmSupervisionRuleRepository()`` /
    ``OrmSupervisionEventRepository()``) and rely on the default
    user list / context builder.

    Note: the repo classes are referenced via the *module-level* imports
    (top of this file) rather than a local re-import — a local
    ``from ... import`` would shadow them and defeat ``patch.object(eng,
    ...)`` used by the unit tests.
    """
    rule_repo = (rule_repo_factory or OrmSupervisionRuleRepository)()
    event_repo = (event_repo_factory or OrmSupervisionEventRepository)()
    rule_rows = rule_repo.list_enabled()
    rules = [_coerce_rule(r) for r in rule_rows]

    ids = list(user_ids) if user_ids is not None else _list_active_user_ids()
    cb = context_builder or _default_context_builder
    ld = ledger if ledger is not None else _default_ledger()
    sch = scheduler if scheduler is not None else _default_scheduler()

    now = datetime.utcnow()
    fired_count = 0
    for uid in ids:
        try:
            ctx = cb(uid)
        except Exception as exc:  # noqa: BLE001
            _log.warning("rule_engine: context build failed (user=%s exc=%s)", uid, exc)
            continue
        for rd in rules:
            try:
                if _fire_for_user(
                    rule_dict=rd, user_id=uid, ctx=ctx,
                    event_repo=event_repo, ledger=ld, scheduler=sch, now=now,
                ):
                    fired_count += 1
            except Exception as exc:  # noqa: BLE001 — one rule's bug must NOT kill the loop
                _log.warning(
                    "rule_engine: rule loop crashed (rule=%s user=%s exc=%s)",
                    rd.get("id"), uid, exc,
                )
    return {"rules_evaluated": len(rules), "users_evaluated": len(ids),
            "fired_count": fired_count}


def _default_ledger() -> ActionLedgerLike:
    """Late-import the real ``ActionLedger`` to keep import-time cost low."""
    from app.services.tutor_engine.action_ledger import ActionLedger
    return ActionLedger()


class _NoopScheduler:
    def schedule_step(self, event_id: int, step: int, rule_id: str,
                      delay_hours: int) -> None:
        _log.info(
            "rule_engine: NOOP schedule (event=%s step=%s rule=%s delay_h=%s)",
            event_id, step, rule_id, delay_hours,
        )


def _default_scheduler() -> SchedulerLike:
    return _NoopScheduler()


__all__ = ["evaluate_all_active_users", "build_user_context"]


def build_user_context(user_id: str) -> dict[str, Any]:
    """Convenience wrapper — current implementation is the S7.3 stub."""
    return _default_context_builder(user_id)
