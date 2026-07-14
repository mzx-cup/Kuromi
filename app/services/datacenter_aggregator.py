"""Datacenter aggregator (Task C2).

Builds the per-user state dict that ``app/api/datacenter.py`` consumes.
Where possible, delegates to existing Repository methods; falls back to
``db.py`` helpers for tables not yet on the Repository protocol.

Return shape matches the slice used by ``_build_dashboard``:
``{user, stats, focus_history, learning_profile, learning_record}``.

For full fidelity with ``db.get_full_user_state`` (other fields like
``preferences``, ``garden``, ``pet`` etc.) we keep that megafunction
callable; new code paths should add fields here as their Repositories
land.
"""
from __future__ import annotations

import db as dbmod
from typing import Any

from app.core.repository_factory import get_repository_for_user


def build_full_user_state(user_id) -> dict[str, Any]:
    """Return the 5-field state shape consumed by ``_build_dashboard``.

    Other UI panes that need the wider state (calendar, garden, pet…)
    should keep calling ``db.get_full_user_state`` until their Repository
    surfaces land.
    """
    state: dict[str, Any] = {
        "user": None,
        "stats": {},
        "focus_history": [],
        "learning_profile": None,
        "learning_record": None,
    }
    user_key = str(user_id)

    state["learning_profile"] = dbmod.get_user_profile(user_id) or None
    state["stats"] = dbmod.get_user_stats(user_id) or {}
    focus = dbmod.get_user_focus_history(user_id)
    if isinstance(focus, list):
        state["focus_history"] = focus

    try:
        learning_repo = get_repository_for_user(user_key, repository_type="learning")
        rec = learning_repo.get_learning_record(user_key)
        if rec is not None:
            state["learning_record"] = rec
    except Exception:
        pass

    return state
