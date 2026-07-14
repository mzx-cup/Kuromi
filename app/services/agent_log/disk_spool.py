"""Disk spool (Layer 3, last-resort buffer) for ResilientBehaviorLogger.

This module exposes a module-level ``disk_append`` callable so that the
caller (``app.services.agent_log.resilient_logger``) can patch it in tests.

The default spool directory is portable across platforms: we use
``tempfile.gettempdir()`` instead of a hard-coded ``/tmp/agent_log_spool``
so that the code works on Windows (where ``/tmp`` does not exist). An
environment variable ``AGENT_LOG_SPOOL_DIR`` overrides the default.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _spool_dir() -> Path:
    """Resolve the disk-spool directory (portable across platforms)."""
    override = os.environ.get("AGENT_LOG_SPOOL_DIR")
    if override:
        return Path(override)
    return Path(tempfile.gettempdir()) / "agent_log_spool"


def disk_append(payload: Any, *, filename: str = "deferred.ndjson") -> bool:
    """Append a deferred log payload to the on-disk spool file.

    Returns True on success, False on any IO failure.
    """
    try:
        spool = _spool_dir()
        spool.mkdir(parents=True, exist_ok=True)
        target = spool / filename
        line = json.dumps(payload, default=str, ensure_ascii=False)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return True
    except OSError:
        return False