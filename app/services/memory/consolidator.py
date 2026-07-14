"""Memory consolidator — episodic → semantic pipeline (slice-s6).

Core Innovation 2: 记忆巩固 (Memory Consolidation) end-to-end.
This module wires ``clustering`` + ``lifecycle`` + ``llm_extractor`` into a
single ``consolidate_user(user_id)`` call:

  1. Pull recent unconsolidated ``EpisodicMemory`` rows (last 7 days).
  2. Cluster them by embedding cosine (S6.1 ``clustering.cluster``).
  3. Open a ``MemoryConsolidationJob`` ledger row.
  4. For each cluster: ask the LLM extractor (S6.2) for a declarative
     pattern → match against existing ``SemanticMemory`` → either insert
     a new row or ``reinforce`` / ``weaken`` the match (S6.1 lifecycle).
  5. After the lifecycle update, apply the 90/180-day stale checks so
     the active → fading → retired transitions actually fire.
  6. Mark the cluster's episodes consolidated + close the job ledger row.

The reinforce-vs-weaken decision uses the LLM-reported pattern confidence
(> 0.5 → reinforce, ≤ 0.5 → weaken); a more nuanced similarity score is
deferred to a later slice when real embedding-based ``find_similar`` is
wired.

Embedding caveat: ``clustering.cluster`` requires an ``embedding`` field
on each episode. Today's S5 ``record_event`` does not embed the event
summary, so production episodes may arrive with ``embedding is None``;
those rows are skipped with a debug log. Tests mock the embeddings
directly.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.models.memory_consolidation_job import MemoryConsolidationJob
from app.models.semantic_memory import SemanticMemory
from app.repositories.orm.episodic_memory import OrmEpisodicMemoryRepository
from app.repositories.orm.semantic_memory import (
    OrmMemoryConsolidationJobRepository,
    OrmSemanticMemoryRepository,
)
from app.services.memory import lifecycle
from app.services.memory.clustering import cluster as _cluster
from app.services.memory.llm_extractor import extract_pattern


_log = logging.getLogger(__name__)

_EPS = 1e-9
# Threshold above which the LLM-extracted pattern is considered to
# reinforce an existing semantic memory (rather than weaken it).
# Intentionally a constant for the S6.2 stub boundary: the stub
# returns 0.7, so 0.5 → reinforce. Should become tunable once
# ``find_similar`` exposes a similarity score alongside
# ``extract_pattern``'s confidence.
_REINFORCE_CONFIDENCE_THRESHOLD = 0.5
# Minimum episodic events required to attempt consolidation.
_MIN_EPISODIC = 3
# Default cluster-window length (days). Mirrors ``record_event`` callers.
_DAYS_WINDOW = 7


def _semantic_to_dict(semantic: SemanticMemory) -> dict:
    """Materialise a SemanticMemory row as the dict shape ``lifecycle`` expects."""
    last = semantic.last_reinforced_at
    if last is not None and getattr(last, "tzinfo", None) is not None:
        # ``lifecycle`` uses naive ``datetime.utcnow()`` for the stale math,
        # so normalise both sides to naive UTC for arithmetic.
        last = last.replace(tzinfo=None)
    return {
        "id": semantic.id,
        "user_id": semantic.user_id,
        "statement": semantic.statement,
        "status": semantic.status,
        "confidence": float(semantic.confidence),
        "evidence_ids": list(semantic.evidence_ids or []),
        "last_reinforced_at": last,
    }


def _persist_semantic_dict(
    repo: OrmSemanticMemoryRepository,
    semantic_dict: dict,
    source: Optional[SemanticMemory] = None,
) -> None:
    """Push the lifecycle-mutated dict back to SQL and (if provided) mirror it
    onto the in-memory ``source`` row so callers see up-to-date attributes.

    Caveat: mutates the caller-supplied ORM row in addition to writing
    to SQL — convenient for tests, but couples in-memory and DB state."""
    sid = semantic_dict.get("id")
    if sid is None:
        return
    fields: dict[str, Any] = {
        "status": semantic_dict["status"],
        "confidence": float(semantic_dict["confidence"]),
        "evidence_ids": list(semantic_dict.get("evidence_ids", [])),
    }
    last = semantic_dict.get("last_reinforced_at")
    if last is not None:
        fields["last_reinforced_at"] = last
    repo.update_fields(sid, fields)
    # Keep the in-memory ORM row in sync (useful for tests + cross-session reads).
    if source is not None:
        source.status = fields["status"]
        source.confidence = fields["confidence"]
        source.evidence_ids = fields["evidence_ids"]
        if "last_reinforced_at" in fields:
            source.last_reinforced_at = fields["last_reinforced_at"]


def consolidate_user(user_id: str) -> dict:
    """Run the full consolidation pass for one user.

    Returns a small dict summarising the run. A pass that didn't run
    (too few episodes, no clusters of size >= 3) is reported with
    ``skipped: True`` and a ``reason``.
    """
    epi_repo = OrmEpisodicMemoryRepository()
    sem_repo = OrmSemanticMemoryRepository()
    job_repo = OrmMemoryConsolidationJobRepository()

    # Step 1: pull recent unconsolidated episodes.
    episodes = epi_repo.recent_unconsolidated(user_id=user_id, days=_DAYS_WINDOW)
    if len(episodes) < _MIN_EPISODIC:
        return {
            "skipped": True,
            "reason": f"< {_MIN_EPISODIC} episodic events in the last {_DAYS_WINDOW}d",
            "episodic_count": len(episodes),
        }

    # Step 2: cluster by embedding. Episodes missing ``embedding`` are
    # logged + dropped — production embedding lands in a later slice.
    cluster_input: list[dict] = []
    for e in episodes:
        emb = getattr(e, "embedding", None)
        if not emb:
            _log.debug("skipping episode %s without embedding", e.id)
            continue
        cluster_input.append(
            {
                "id": e.id,
                "user_id": e.user_id,
                "summary": getattr(e, "summary", ""),
                "embedding": emb,
            }
        )
    clusters = _cluster(cluster_input)
    if not clusters:
        return {
            "skipped": True,
            "reason": "no clusters of size >= 3",
            "episodic_count": len(episodes),
        }

    # Step 3: open the job ledger row.
    job = MemoryConsolidationJob(
        user_id=user_id,
        status="running",
        episodic_input_ids=[e.id for e in episodes],
    )
    job_id = job_repo.insert(job)
    job.id = job_id

    new_count = 0
    reinforce_count = 0
    weaken_count = 0

    try:
        # Step 4: iterate clusters.
        for c in clusters:
            try:
                cluster_episode_ids = [ev["id"] for ev in c]
                pattern = extract_pattern(user_id=user_id, cluster=c)

                existing_rows = sem_repo.find_similar(
                    user_id=user_id, statement=pattern["statement"],
                )

                if not existing_rows:
                    # New semantic memory row.
                    new_row = SemanticMemory(
                        user_id=user_id,
                        statement=pattern["statement"],
                        confidence=float(pattern.get("confidence", 0.0)),
                        evidence_ids=list(pattern.get("evidence_ids", [])),
                        status=lifecycle.ACTIVE,
                    )
                    sem_repo.insert(new_row)
                    new_count += 1
                else:
                    # Reinforce / weaken the first matching row (placeholder
                    # ``find_similar`` returns all rows; S6.3 picks the first).
                    target = existing_rows[0]
                    sdict = _semantic_to_dict(target)
                    confidence = float(pattern.get("confidence", 0.0))
                    if confidence > _REINFORCE_CONFIDENCE_THRESHOLD:
                        lifecycle.reinforce(sdict, pattern)
                        reinforce_count += 1
                    else:
                        lifecycle.weaken(sdict, pattern)
                        weaken_count += 1
                    # Apply the 90/180-day stale transitions after the mutation.
                    now = datetime.utcnow()
                    lifecycle.mark_fading_if_stale(sdict, now=now)
                    lifecycle.mark_retired_if_stale(sdict, now=now)
                    _persist_semantic_dict(sem_repo, sdict, source=target)

                # Step 5: mark the cluster's episodes consolidated.
                epi_repo.mark_consolidated(cluster_episode_ids, job_id)

            except Exception as exc:  # noqa: BLE001
                # One cluster's failure must not abort the rest.
                _log.exception(
                    "consolidator: cluster failed for user %s: %s", user_id, exc,
                )
                continue

        job.status = "done"
        return {
            "skipped": False,
            "clusters_processed": len(clusters),
            "new_semantics": new_count,
            "reinforced": reinforce_count,
            "weakened": weaken_count,
            "job_id": job_id,
        }
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = str(exc)
        raise
    finally:
        job.finished_at = datetime.utcnow()
        job_repo.update(job)
