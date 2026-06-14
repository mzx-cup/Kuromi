from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, Field


class Envelope(BaseModel):
    msg_id: str
    trace_id: str
    parent_msg_id: str | None = None
    correlation_id: str | None = None
    from_: str = Field(alias="from")
    to: str
    type: Literal["request", "response", "event", "error", "heartbeat"]
    intent: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(5, ge=0, le=9)
    ttl_ms: int = 30000
    deadline: int = 0
    retry_count: int = 0
    max_retries: int = 1
    schema_version: str = "1.0"
    cost_ms: int = 0
    cost_tokens: int = 0
    timestamp: int

    model_config = {"populate_by_name": True}


class PipelineRequest(BaseModel):
    student_id: str
    course_id: str | None = None
    user_input: str
    trace_id: str | None = None


class PipelineEvent(BaseModel):
    event: Literal[
        "agent_step", "profile_updated", "asset_ready",
        "pipeline_complete", "error", "heartbeat",
    ]
    trace_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: int = 0


class ProfileSnapshot(BaseModel):
    radar: dict[str, float]   # 6 维
    panel: dict[str, dict]    # 4 卡
    last_synced: str