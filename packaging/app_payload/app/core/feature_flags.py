"""Feature flags for database merge cutover.

Provides percentage-based read path cutover and dual-write toggle.
"""
from __future__ import annotations

import hashlib
import os


def user_in_orm_read_path(user_id: str, percentage: int) -> bool:
    """Determine if a user should read from SQLAlchemy ORM.

    Stable per user_id: same user always gets same answer at same percentage.
    """
    if percentage <= 0:
        return False
    if percentage >= 100:
        return True
    h = hashlib.md5(f"orm-read:{user_id}".encode()).hexdigest()
    bucket = int(h[:8], 16) % 100
    return bucket < percentage


def get_read_percentage() -> int:
    """Read READ_BACKEND_PERCENTAGE from env. Invalid -> 0."""
    raw = os.getenv("READ_BACKEND_PERCENTAGE", "0")
    try:
        value = int(raw)
    except ValueError:
        return 0
    if value < 0:
        return 0
    if value > 100:
        return 100
    return value


def is_dual_write_enabled() -> bool:
    """Read DUAL_WRITE_LEGACY from env. Default false."""
    return os.getenv("DUAL_WRITE_LEGACY", "false").lower() == "true"


def is_orm_enabled() -> bool:
    """Master switch. If false, all routes use legacy regardless of percentage."""
    return os.getenv("ORM_ENABLED", "true").lower() != "false"