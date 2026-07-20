# -*- coding: utf-8 -*-
"""Tests for TeacherChatRequest persona_id field, persona validation,
and the resolution contract enforced inside the /api/v2/teacher/chat handler.

The first four tests cover the schema and PersonaManager.is_valid() directly.
The last two tests lock in the resolution contract:
  - persona_id takes precedence over legacy persona
  - invalid persona_id falls back to the default expert_mentor
"""

import pytest
from fastapi.testclient import TestClient

from app.api.teacher_chat import TeacherChatRequest
from app.services.teacher.personas import get_persona_manager


def test_request_accepts_persona_id():
    r = TeacherChatRequest(message="hi", persona_id="caring_counselor")
    assert r.persona_id == "caring_counselor"


def test_request_defaults_both_none():
    r = TeacherChatRequest(message="hi")
    assert r.persona is None
    assert r.persona_id is None


def test_caring_counselor_is_valid():
    assert get_persona_manager().is_valid("caring_counselor") is True


def test_bogus_is_invalid():
    assert get_persona_manager().is_valid("not_a_real_persona") is False


# =============================================================================
# 解析契约测试 — 通过真实 handler 调用并捕获传给 pipeline.run 的 persona 参数
# =============================================================================


@pytest.fixture
def pipeline_capture(monkeypatch):
    """Patch app.api.teacher_chat so the legacy pipeline.run path is used and
    the `persona` kwarg passed to it is captured for assertion.

    The handler checks `_ENABLE_TUTOR_ENGINE`; forcing it False routes the
    request through the `pipeline.run` fallback, which is exactly the path
    where the resolution contract matters.
    """
    import app.api.teacher_chat as tc_module

    monkeypatch.setattr(tc_module, "_ENABLE_TUTOR_ENGINE", False)

    captured = {}

    async def fake_run(*, user_input, persona, **kwargs):
        captured["user_input"] = user_input
        captured["persona"] = persona
        captured["kwargs"] = kwargs
        # yield a single SSE-shaped event so StreamingResponse has something
        # to serialize
        yield {"event": "done", "data": {"agent": "teacher"}}

    class _FakePipeline:
        run = staticmethod(fake_run)

    monkeypatch.setattr(tc_module, "get_pipeline", lambda: _FakePipeline())
    return captured


def test_resolution_prefers_persona_id_over_persona(pipeline_capture):
    """When both persona_id and persona are sent, persona_id wins downstream."""
    from main import app

    client = TestClient(app)
    r = client.post(
        "/api/v2/teacher/chat",
        json={
            "message": "hi",
            "persona_id": "caring_counselor",
            "persona": "expert_mentor",
        },
    )
    assert r.status_code == 200, r.text
    assert pipeline_capture["persona"] == "caring_counselor"
    # Sanity: user_input forwarded unchanged
    assert pipeline_capture["user_input"] == "hi"


def test_invalid_falls_back_to_default(pipeline_capture):
    """When persona_id is not in the allow-list, the handler must fall back
    to the default 'expert_mentor' instead of forwarding the bogus value."""
    from main import app

    client = TestClient(app)
    r = client.post(
        "/api/v2/teacher/chat",
        json={"message": "hi", "persona_id": "bogus_id"},
    )
    assert r.status_code == 200, r.text
    assert pipeline_capture["persona"] == "expert_mentor"