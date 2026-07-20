"""Normalize API responses for contract comparison.

Strips noise fields that legitimately differ between backends.
"""
from __future__ import annotations

from typing import Any

NOISE_FIELDS = {
    "updated_at", "created_at", "last_synced_at",
    "request_id", "trace_id", "server_timestamp",
}


def normalize(payload: Any) -> Any:
    """Recursively strip noise fields."""
    if isinstance(payload, dict):
        return {
            k: normalize(v)
            for k, v in payload.items()
            if k not in NOISE_FIELDS
        }
    if isinstance(payload, list):
        return [normalize(x) for x in payload]
    return payload
