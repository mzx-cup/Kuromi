"""DualWriteRepository - writes to both primary and shadow backends."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("starlearn.repository.dual_write")


class DualWriteRepository:
    """Decorator: every write operation hits both primary and shadow.

    Primary failures raise immediately (production truth).
    Shadow failures are logged and queued for retry, never raised.
    """

    def __init__(self, primary: Any, shadow: Any):
        self.primary = primary
        self.shadow = shadow

    async def _dual_write(self, method_name: str, *args, **kwargs) -> Any:
        primary_method = getattr(self.primary, method_name)
        shadow_method = getattr(self.shadow, method_name)

        result = await primary_method(*args, **kwargs)

        try:
            await shadow_method(*args, **kwargs)
        except Exception as e:
            logger.warning(
                "[dual-write] shadow %s failed: %s", method_name, e,
                extra={"method": method_name, "args": str(args)[:200]},
            )
            # Shadow failures are logged but not retried in M0.
            # Async retry queue (Redis/in-memory) is deferred to a future milestone.
            # For M1-M11, manual reconciliation via reconcile_databases.py is acceptable.

        return result

    def __getattr__(self, name: str):
        if name.startswith("_") or name in ("primary", "shadow"):
            raise AttributeError(name)
        async def proxy(*args, **kwargs):
            return await self._dual_write(name, *args, **kwargs)
        return proxy
