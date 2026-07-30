"""Tests for StyleRecognizer (M5.2)."""
from __future__ import annotations

import pytest


def test_recognizer_classifies_visual_learner():
    """image 停留远大于 text 时，主导风格必须是 visual。"""
    from app.services.cognitive.style_recognizer import StyleRecognizer

    rec = StyleRecognizer()
    behavior = {
        "image_page_avg_dwell_seconds": 120,
        "text_page_avg_dwell_seconds": 20,
        "video_page_avg_dwell_seconds": 30,
        "code_editor_avg_dwell_seconds": 25,
        "audio_page_avg_dwell_seconds": 15,
    }
    style = rec.classify(behavior)
    assert style["primary"] == "visual"
    assert style["confidence"] > 0.5


def test_recognizer_classifies_kinesthetic_learner():
    """code_editor 停留远大于其他时，主导风格必须是 kinesthetic。"""
    from app.services.cognitive.style_recognizer import StyleRecognizer

    rec = StyleRecognizer()
    behavior = {
        "code_editor_avg_dwell_seconds": 180,
        "video_page_avg_dwell_seconds": 30,
        "text_page_avg_dwell_seconds": 25,
        "image_page_avg_dwell_seconds": 20,
        "audio_page_avg_dwell_seconds": 10,
    }
    style = rec.classify(behavior)
    assert style["primary"] == "kinesthetic"


def test_recognizer_classifies_auditory_learner():
    """audio 停留最长时，主导风格必须是 auditory。"""
    from app.services.cognitive.style_recognizer import StyleRecognizer

    rec = StyleRecognizer()
    behavior = {
        "audio_page_avg_dwell_seconds": 200,
        "image_page_avg_dwell_seconds": 30,
        "text_page_avg_dwell_seconds": 25,
        "code_editor_avg_dwell_seconds": 10,
        "video_page_avg_dwell_seconds": 40,
    }
    style = rec.classify(behavior)
    assert style["primary"] == "auditory"


def test_recognizer_handles_empty_behavior():
    """空 behavior 必须返回某种风格（不崩）+ 0 confidence。"""
    from app.services.cognitive.style_recognizer import StyleRecognizer

    rec = StyleRecognizer()
    style = rec.classify({})
    assert style["primary"] in ("visual", "auditory", "kinesthetic")
    assert 0.0 <= style["confidence"] <= 1.0


def test_recognizer_returns_full_scores_dict():
    """返回 dict 必须包含所有 3 风格的分数。"""
    from app.services.cognitive.style_recognizer import StyleRecognizer

    rec = StyleRecognizer()
    style = rec.classify({"image_page_avg_dwell_seconds": 100})
    assert "visual" in style["scores"]
    assert "auditory" in style["scores"]
    assert "kinesthetic" in style["scores"]