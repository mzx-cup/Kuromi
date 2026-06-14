# -*- coding: utf-8 -*-
"""Tests for TeacherChatRequest persona_id field and persona validation."""

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
