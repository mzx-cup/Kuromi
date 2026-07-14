"""SemanticMemory lifecycle state machine (S6.1).

States: active → fading → retired.
Reinforce raises confidence and may reactivate a fading row.
Weaken lowers confidence; falling below 0.3 demotes active → fading.
Time-based stale checks (90d → fading, 180d → retired) sweep long-idle rows
through the stages.

S6.1 operates on plain dicts because the SQLAlchemy ``SemanticMemory``
model is not yet defined — that lands in S6.3 alongside the consolidator
that wires this module up. The public functions mutate the dict in place
and the keys are documented below:

    status: str                 # one of ACTIVE / FADING / RETIRED
    confidence: float           # [0.0, 1.0]
    evidence_ids: list[str]     # unique episode ids supporting this memory
    last_reinforced_at: datetime  # UTC, used by stale checks
"""
from __future__ import annotations

from datetime import datetime, timedelta

ACTIVE = "active"
FADING = "fading"
RETIRED = "retired"

_FADING_AFTER = timedelta(days=90)
_RETIRED_AFTER = timedelta(days=180)

_REINFORCE_GAIN = 0.1
_WEAKEN_LOSS = 0.1

_REACTIVATE_THRESHOLD = 0.5
_DEMOTE_THRESHOLD = 0.3


def reinforce(semantic: dict, pattern: dict) -> None:
    """Strengthen a semantic memory based on a fresh cluster pattern.

    - ``confidence += pattern["confidence"] * _REINFORCE_GAIN`` (cap 1.0).
    - Append ``pattern["evidence_ids"]`` to ``evidence_ids`` (deduped).
    - If currently fading and the new confidence crosses the reactivate
      threshold, transition back to active.
    """
    confidence = semantic["confidence"] + pattern["confidence"] * _REINFORCE_GAIN
    semantic["confidence"] = min(confidence, 1.0)

    existing = set(semantic.get("evidence_ids", []))
    existing.update(pattern.get("evidence_ids", []))
    semantic["evidence_ids"] = list(existing)

    if (
        semantic.get("status") == FADING
        and semantic["confidence"] >= _REACTIVATE_THRESHOLD
    ):
        semantic["status"] = ACTIVE


def weaken(semantic: dict, pattern: dict) -> None:
    """Decay a semantic memory.

    - ``confidence -= _WEAKEN_LOSS`` (floor 0.0).
    - If currently active and the new confidence falls below the demote
      threshold, transition to fading.
    - The ``pattern`` argument is accepted for symmetry with ``reinforce``
      (a future revision may scale the loss by a contradicting-evidence
      weight) but is unused in S6.1.
    """
    confidence = semantic["confidence"] - _WEAKEN_LOSS
    semantic["confidence"] = max(confidence, 0.0)

    if (
        semantic.get("status") == ACTIVE
        and semantic["confidence"] < _DEMOTE_THRESHOLD
    ):
        semantic["status"] = FADING


def mark_fading_if_stale(semantic: dict, *, now: datetime) -> None:
    """Demote an active row to fading if it has not been reinforced in 90+ days."""
    if semantic.get("status") != ACTIVE:
        return
    last = semantic.get("last_reinforced_at")
    if last is None:
        return
    if now - last > _FADING_AFTER:
        semantic["status"] = FADING


def mark_retired_if_stale(semantic: dict, *, now: datetime) -> None:
    """Retire a fading row that has gone another 180 days without reinforcement."""
    if semantic.get("status") != FADING:
        return
    last = semantic.get("last_reinforced_at")
    if last is None:
        return
    if now - last > _RETIRED_AFTER:
        semantic["status"] = RETIRED