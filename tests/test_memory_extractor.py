# -*- coding: utf-8 -*-
"""Tests for memory_extractor._parse_extraction_result."""

import json
import pytest
from app.services.memory_extractor import _parse_extraction_result


class TestParseExtractionResultNewTypes:
    """Verify that _parse_extraction_result correctly handles the three new
    memory types: learning_trait, personality, interaction.
    """

    def test_learning_trait(self):
        raw = json.dumps([
            {
                "memory_type": "learning_trait",
                "content": "喜欢通过图表和视觉化方式理解抽象概念",
                "confidence": 0.85,
                "is_update": False,
            }
        ])
        result = _parse_extraction_result(raw)
        assert len(result) == 1
        assert result[0]["memory_type"] == "learning_trait"
        assert result[0]["content"] == "喜欢通过图表和视觉化方式理解抽象概念"
        assert result[0]["confidence"] == 0.85
        assert result[0]["is_update"] is False

    def test_personality(self):
        raw = json.dumps([
            {
                "memory_type": "personality",
                "content": "性格内向，倾向于先独立思考再提问",
                "confidence": 0.78,
                "is_update": False,
            }
        ])
        result = _parse_extraction_result(raw)
        assert len(result) == 1
        assert result[0]["memory_type"] == "personality"

    def test_interaction(self):
        raw = json.dumps([
            {
                "memory_type": "interaction",
                "content": "习惯在每次对话结束时总结要点",
                "confidence": 0.82,
                "is_update": False,
            }
        ])
        result = _parse_extraction_result(raw)
        assert len(result) == 1
        assert result[0]["memory_type"] == "interaction"

    def test_all_new_types_together(self):
        raw = json.dumps([
            {
                "memory_type": "learning_trait",
                "content": "偏好视频学习",
                "confidence": 0.9,
                "is_update": False,
            },
            {
                "memory_type": "personality",
                "content": "做事有条理",
                "confidence": 0.8,
                "is_update": False,
            },
            {
                "memory_type": "interaction",
                "content": "喜欢用emoji表达情绪",
                "confidence": 0.75,
                "is_update": False,
            },
        ])
        result = _parse_extraction_result(raw)
        assert len(result) == 3
        types = [r["memory_type"] for r in result]
        assert "learning_trait" in types
        assert "personality" in types
        assert "interaction" in types

    def test_legacy_types_still_work(self):
        raw = json.dumps([
            {
                "memory_type": "background",
                "content": "计算机专业大二学生",
                "confidence": 0.95,
                "is_update": False,
            },
            {
                "memory_type": "emotion",
                "content": "最近对考试感到焦虑",
                "confidence": 0.7,
                "is_update": False,
            },
        ])
        result = _parse_extraction_result(raw)
        assert len(result) == 2
        assert result[0]["memory_type"] == "background"
        assert result[1]["memory_type"] == "emotion"
