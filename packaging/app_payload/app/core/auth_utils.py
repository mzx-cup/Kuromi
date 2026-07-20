# -*- coding: utf-8 -*-
"""Auth utility helpers.

Currently exposes JWT decode without signature verification, used by
rate_limiter for per-user key extraction.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("starlearn.auth_utils")


def decode_jwt_no_verify(token: str) -> dict[str, Any] | None:
    """Decode a JWT WITHOUT verifying signature. Returns claims or None.

    Used by rate limiter to extract user_id from Authorization header
    for per-user rate limit keys. NEVER use for auth decisions.
    """
    try:
        # Lazy import to avoid pulling JWT lib at module load
        import jwt
        # decode without verification — signature check is bypassed
        return jwt.decode(token, options={"verify_signature": False})
    except Exception as e:
        logger.debug("decode_jwt_no_verify failed: %s", e)
        return None
