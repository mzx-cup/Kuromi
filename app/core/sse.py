from __future__ import annotations

import json
import time
from typing import Any, AsyncGenerator


def sse_event(event: str, data: Any) -> str:
    """Format a single SSE event string."""
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, ensure_ascii=False)
    elif isinstance(data, str):
        data_str = data
    else:
        data_str = str(data)
    return f"event: {event}\ndata: {data_str}\n\n"


def sse_heartbeat() -> str:
    """Generate an SSE heartbeat comment line."""
    return f":heartbeat {int(time.time())}\n\n"


def sse_done(agent_name: str = "", full_text: str = "") -> str:
    """Generate the terminal SSE 'done' event."""
    return sse_event("done", {"agent_name": agent_name, "full_text": full_text})


def sse_error(code: str, message: str) -> str:
    """Generate an SSE error event."""
    return sse_event("error", {"code": code, "message": message})


async def _to_sse_bytes(generator: AsyncGenerator[str, None]) -> AsyncGenerator[bytes, None]:
    """Wrap a string-SSE generator to yield UTF-8 bytes."""
    async for chunk in generator:
        yield chunk.encode("utf-8")
