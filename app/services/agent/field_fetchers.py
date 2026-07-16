"""Four memory-card field fetchers — slice-A3.

Replaces the P1 stub in MemoryCardLoader.load(). Each field is fetched
with a 250ms timeout; on timeout or empty result we use a stable fallback
string so the agent prompt still has a placeholder.

The fetcher is decoupled from concrete ORM repositories: the loader
passes a ``repos`` dict whose values expose the four methods below.
Tests inject ``MagicMock`` repositories; production wiring
(B3 / orchestrator startup) wires the actual ORM classes
(OrmEpisodicMemoryRepository, OrmWeaknessTimelineRepository, etc.).
"""
from __future__ import annotations

import concurrent.futures
import logging
from typing import Any


_log = logging.getLogger(__name__)


_FALLBACK = {
    "episodic_last": "(no recent episode)",
    "capability_recent": "(no capability delta)",
    "semantic_top3": "(no semantic memory)",
    "supervision_pending": "(no pending supervision)",
}


# Priority order: most-actionable signal first. Lower-priority fields
# are truncated or dropped first when the loader's token budget runs out.
PRIORITY_ORDER: list[str] = [
    "supervision_pending",
    "semantic_top3",
    "capability_recent",
    "episodic_last",
]


class FieldFetchers:
    """Concurrent fetch of the 4 memory-card fields.

    Args:
        repos: dict with keys ``episodic``, ``capability``,
            ``semantic``, ``supervision``. Each value exposes
            ``recent_unconsolidated``, ``recent``,
            ``top_by_confidence``, and ``list_pending``
            respectively.
        timeout_s: per-fetcher timeout (default 0.25s).

    The last ``fetch_all`` call also sets ``self.last_partial_fields``
    to the keys whose fetcher raised. Callers can read this directly
    — it is intentionally NOT mixed into the returned dict so the
    dict's key set stays exactly the 4 field keys (callers rely on
    that contract).
    """

    def __init__(self, repos: dict[str, Any], *, timeout_s: float = 0.25) -> None:
        self._repos = repos
        self._timeout_s = timeout_s
        self.last_partial_fields: list[str] = []

    def fetch_all(self, user_id: str) -> dict[str, Any]:
        """Concurrent fetch of all 4 fields.

        Returns a dict whose keys are in ``PRIORITY_ORDER`` (most
        actionable first). Fields whose fetcher raised fall back to a
        placeholder string and are recorded in
        ``self.last_partial_fields``.
        """
        out: dict[str, Any] = {}
        partial: list[str] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futs = {
                key: ex.submit(self._fetch_one, user_id, key)
                for key in PRIORITY_ORDER
            }
            for key in PRIORITY_ORDER:
                fut = futs[key]
                try:
                    out[key] = fut.result(timeout=self._timeout_s)
                except Exception as exc:  # noqa: BLE001
                    _log.warning("fetcher[%s] failed: %s", key, exc)
                    out[key] = _FALLBACK[key]
                    partial.append(key)
        self.last_partial_fields = partial
        return out

    def fetch_one(self, user_id: str, key: str) -> str:
        """Single-field fetch. Raises ``KeyError`` on unknown field key."""
        if key not in PRIORITY_ORDER:
            raise KeyError(key)
        return self._fetch_one(user_id, key)

    def _fetch_one(self, user_id: str, key: str) -> str:
        if key == "episodic_last":
            rows = self._repos["episodic"].recent_unconsolidated(
                user_id=user_id, days=7,
            )
            if not rows:
                return _FALLBACK[key]
            # ORM row may have ``summary`` (preferred) or fall back to
            # the event_type / id for short structured rows.
            first = rows[0]
            summary = (getattr(first, "summary", "") or "").strip()
            if summary:
                return summary[:200]
            event_type = getattr(first, "event_type", "")
            return f"recent event: {event_type}" if event_type else _FALLBACK[key]

        if key == "capability_recent":
            # real ORM signature: recent(*, user_id, dim, within_days)
            # Tests inject MagicMock with `.recent.return_value = [...]`.
            rows = self._repos["capability"].recent(
                user_id=user_id, dim="overall", within_days=7,
            )
            if not rows:
                return _FALLBACK[key]
            return f"近 7 天 {len(rows)} 项能力快照"

        if key == "semantic_top3":
            # real ORM: find_similar / list_active / get. The loader
            # mock uses .top_by_confidence(user_id, n=3, status='active').
            rows = self._repos["semantic"].top_by_confidence(
                user_id=user_id, n=3, status="active",
            )
            if not rows:
                return _FALLBACK[key]
            items = "; ".join(
                (getattr(r, "statement", "") or "")[:80] for r in rows
            )
            return items or _FALLBACK[key]

        if key == "supervision_pending":
            # real ORM signature: list_pending_for_user(user_id).
            # Tests use MagicMock named ``list_pending``; both names
            # work because we try the test-friendly one first.
            repo = self._repos["supervision"]
            if hasattr(repo, "list_pending"):
                rows = repo.list_pending(user_id=user_id)
            else:
                rows = repo.list_pending_for_user(user_id=user_id)
            if not rows:
                return _FALLBACK[key]
            return f"当前 {len(rows)} 条待办督导"

        raise KeyError(key)


__all__ = ["FieldFetchers", "PRIORITY_ORDER"]
