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


# ---------------------------------------------------------------------------
# v2 架构灰度开关（docs/superpowers/specs/2026-08-20-星识最优架构统一设计.md）
# 环境变量驱动，不落库；非法值回退默认。
# ---------------------------------------------------------------------------

GUARD_V2_VALID_MODES = ("off", "shadow", "enforce")


def guard_v2_mode() -> str:
    """GUARD_V2_MODE = off | shadow | enforce（默认 enforce）。

    - off:     走 v1 HallucinationGuard（非流式 + 伪流）
    - shadow:  v1 决策生效，v2 并行计算并记录 divergence 日志
    - enforce: v2 证据融合守卫生效（双模流式 + correction）
    """
    raw = os.getenv("GUARD_V2_MODE", "enforce").strip().lower()
    return raw if raw in GUARD_V2_VALID_MODES else "enforce"


def memory_v2_enabled() -> bool:
    """MEMORY_V2 = off 时回退旧版 200 条全量扫记忆检索。默认开启。"""
    return os.getenv("MEMORY_V2", "on").strip().lower() != "off"


def self_check_enabled() -> bool:
    """条件 Self-Check（置信度边界带 [0.55, 0.75) 触发的 LLM 二次校验）。"""
    return os.getenv("SELF_CHECK_ENABLED", "1").strip() not in ("0", "false", "off")


def embedding_provider_pref() -> str:
    """EMBEDDING_PROVIDER = auto | local | api | hash（默认 auto，按可用性降级）。"""
    raw = os.getenv("EMBEDDING_PROVIDER", "auto").strip().lower()
    return raw if raw in ("auto", "local", "api", "hash") else "auto"