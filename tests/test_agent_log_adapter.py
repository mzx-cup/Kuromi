import time
import uuid
from datetime import datetime
from agents import AgentStepLog
from app.services.agent_log_adapter import agent_log_to_envelope


def _make_log(status="success", role="画像分析"):
    return AgentStepLog(
        agent_name="profiler", agent_role=role,
        input_summary="input x", output_summary="output y",
        processing_time_ms=320, status=status,
        error_message="", timestamp=datetime.now(),
    )


def test_success_log_to_envelope():
    env = agent_log_to_envelope(_make_log(), trace_id="t1")
    assert env["type"] == "response"
    assert env["from"] == "profiler"
    assert env["intent"] == "画像分析"
    assert env["cost_ms"] == 320
    assert env["payload"]["status"] == "success"
    assert env["payload"]["output_summary"] == "output y"


def test_failed_log_emits_error_type():
    env = agent_log_to_envelope(_make_log(status="error"), trace_id="t1")
    assert env["type"] == "error"
    assert env["payload"]["error_message"] == ""
