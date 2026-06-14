import pytest
from pydantic import ValidationError
from app.schemas.agent_orchestration import Envelope, PipelineRequest, PipelineEvent


def test_envelope_minimal():
    env = Envelope(
        msg_id="m1", trace_id="t1", **{"from": "profiler"}, to="orchestrator",
        type="response", intent="extract_profile", payload={"k": "v"},
        timestamp=1718332800000,
    )
    assert env.from_ == "profiler"  # alias works
    assert env.priority == 5
    assert env.schema_version == "1.0"


def test_envelope_rejects_bad_type():
    with pytest.raises(ValidationError):
        Envelope(
            msg_id="m1", trace_id="t1", **{"from": "x"}, to="y",
            type="bogus", intent="i", payload={}, timestamp=0,
        )


def test_pipeline_request_defaults():
    req = PipelineRequest(student_id="u1", user_input="hi")
    assert req.course_id is None
    assert req.trace_id is None


def test_pipeline_event_profile_updated():
    evt = PipelineEvent(
        event="profile_updated",
        trace_id="t1",
        data={"radar": {"knowledge_mastery": 50}, "panel": {}},
    )
    assert evt.event == "profile_updated"
    assert evt.data["radar"]["knowledge_mastery"] == 50