"""Embedding-based greedy single-pass clustering (S6.1).

Algorithm: for each event in input order, place it into the first existing
cluster whose first (representative) event has cosine similarity ≥ threshold.
Otherwise start a new cluster. After all events are placed, clusters with
fewer than 3 members are dropped — singleton / doubleton "clusters" lack the
evidence density to be promoted into a SemanticMemory row, so we discard
them rather than burden the consolidator with low-quality patterns.
"""
from __future__ import annotations

import numpy as np


_EPS = 1e-12


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Safe for zero vectors."""
    arr_a = np.array(a, dtype=float)
    arr_b = np.array(b, dtype=float)
    denom = np.linalg.norm(arr_a) * np.linalg.norm(arr_b) + _EPS
    return float(np.dot(arr_a, arr_b) / denom)


def cluster(events: list[dict], threshold: float = 0.75) -> list[list[dict]]:
    """Group events into clusters by embedding cosine similarity.

    Greedy single-pass: each new event joins the first existing cluster
    whose representative embedding is similar enough; otherwise a new
    cluster is started. Clusters with fewer than 3 events are dropped.
    """
    clusters: list[list[dict]] = []
    for event in events:
        placed = False
        for c in clusters:
            if _cosine(event["embedding"], c[0]["embedding"]) >= threshold:
                c.append(event)
                placed = True
                break
        if not placed:
            clusters.append([event])
    return [c for c in clusters if len(c) >= 3]