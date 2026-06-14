from __future__ import annotations
import uuid
from typing import Any
from agents import AgentStepLog


def agent_log_to_envelope(log: AgentStepLog, trace_id: str) -> dict[str, Any]:
    """把 AgentStepLog 序列化为 Envelope dict(JSON-ready).

    Failed logs use type=error; success logs use type=response.
    """
    is_error = log.status == "error"
    return {
        "msg_id": str(uuid.uuid4()),
        "trace_id": trace_id,
        "from": log.agent_name,
        "to": "orchestrator",
        "type": "error" if is_error else "response",
        "intent": log.agent_role,
        "payload": {
            "input_summary": log.input_summary,
            "output_summary": log.output_summary,
            "status": log.status,
            "error_message": log.error_message,
        },
        "cost_ms": log.processing_time_ms,
        "timestamp": int(log.timestamp.timestamp() * 1000),
        "schema_version": "1.0",
        "priority": 5,
    }
