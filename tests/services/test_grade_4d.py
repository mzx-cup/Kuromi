"""缺口2:4 维评分测试(知识 / 能力 / 过程 / 创新).

覆盖:
  - GradeResult 字段默认/构造
  - _parse_response 解析 4 维 + 兼容老 JSON(单 score 字段)
  - confidence 计算
  - compute_weighted_score 加权
  - to_dict 含 dimensions 字段
  - QuizRecord ORM 字段存在
"""
from __future__ import annotations

import json

import pytest

from app.services.teacher.grading import (
    GradeResult,
    SHORT_ANSWER_SYSTEM_PROMPT,
    get_grader,
)


# ============================================================
# GradeResult 默认/构造
# ============================================================

class TestGradeResultFields:
    def test_default_dimensions_are_zero(self):
        r = GradeResult(is_correct=True, score=80, total_points=100, feedback="ok")
        assert r.knowledge_dimension == 0.0
        assert r.ability_dimension == 0.0
        assert r.process_dimension == 0.0
        assert r.innovation_dimension == 0.0
        assert r.confidence == 1.0
        assert r.arbitration_triggered is False

    def test_dimension_weights_default(self):
        r = GradeResult(is_correct=True, score=0, total_points=100, feedback="")
        w = r.dimension_weights
        assert w["knowledge"] == 0.4
        assert w["ability"] == 0.3
        assert w["process"] == 0.2
        assert w["innovation"] == 0.1
        assert abs(sum(w.values()) - 1.0) < 1e-9

    def test_to_dict_includes_dimensions(self):
        r = GradeResult(
            is_correct=True, score=85.5, total_points=100, feedback="good",
            knowledge_dimension=90, ability_dimension=85, process_dimension=80,
            innovation_dimension=70, confidence=0.92,
        )
        d = r.to_dict()
        assert d["score"] == 85.5
        assert "dimensions" in d
        assert d["dimensions"]["knowledge"] == 90
        assert d["dimensions"]["ability"] == 85
        assert d["dimensions"]["process"] == 80
        assert d["dimensions"]["innovation"] == 70
        assert d["confidence"] == 0.92
        assert d["dimension_weights"]["knowledge"] == 0.4

    def test_compute_weighted_score(self):
        # 90 * 0.4 + 85 * 0.3 + 80 * 0.2 + 70 * 0.1 = 36 + 25.5 + 16 + 7 = 84.5
        s = GradeResult.compute_weighted_score(90, 85, 80, 70)
        assert abs(s - 84.5) < 1e-9

    def test_compute_weighted_score_custom_weights(self):
        s = GradeResult.compute_weighted_score(
            80, 60, 40, 20,
            weights={"knowledge": 0.7, "ability": 0.2, "process": 0.05, "innovation": 0.05},
        )
        # 80*0.7 + 60*0.2 + 40*0.05 + 20*0.05 = 56+12+2+1 = 71
        assert abs(s - 71.0) < 1e-9


# ============================================================
# _parse_response 解析 4 维
# ============================================================

class TestParseResponse4D:
    @pytest.mark.asyncio
    async def test_parse_short_answer_with_4_dim(self):
        grader = get_grader()
        raw = json.dumps({
            "is_correct": True,
            "score": 85,
            "knowledge_dimension": 90,
            "ability_dimension": 85,
            "process_dimension": 80,
            "innovation_dimension": 70,
            "feedback": "整体不错",
            "key_points_hit": ["A", "B"],
            "key_points_missed": ["C"],
        })
        r = grader._parse_response(raw, total_points=100, qtype="short_answer")
        assert r.knowledge_dimension == 90
        assert r.ability_dimension == 85
        assert r.process_dimension == 80
        assert r.innovation_dimension == 70
        # 综合分 = 90*0.4 + 85*0.3 + 80*0.2 + 70*0.1 = 84.5
        assert abs(r.score - 84.5) < 1e-9
        assert r.key_points_hit == ["A", "B"]
        assert r.key_points_missed == ["C"]
        # confidence: std/满分
        mean = (90 + 85 + 80 + 70) / 4
        variance = sum((d - mean) ** 2 for d in [90, 85, 80, 70]) / 4
        expected_confidence = max(0.0, 1.0 - (variance ** 0.5) / 100)
        assert abs(r.confidence - expected_confidence) < 1e-9

    @pytest.mark.asyncio
    async def test_parse_short_answer_legacy_single_score(self):
        """兼容老 JSON(只有 score 字段,无 4 维)— 缺口2 向后兼容."""
        grader = get_grader()
        raw = json.dumps({
            "is_correct": True,
            "score": 75,
            "feedback": "ok",
            "key_points_hit": [],
            "key_points_missed": [],
        })
        r = grader._parse_response(raw, total_points=100, qtype="short_answer")
        # 老 score 应被填到 knowledge_dimension
        assert r.knowledge_dimension == 75
        assert r.ability_dimension == 0
        assert r.process_dimension == 0
        assert r.innovation_dimension == 0
        # 综合分:75 * 0.4 = 30(只有 knowledge 有值)
        assert abs(r.score - 30.0) < 1e-9

    @pytest.mark.asyncio
    async def test_parse_choice_4_dim_uniform(self):
        """选择题无 4 维语义,4 维都等于 score."""
        grader = get_grader()
        raw = json.dumps({
            "is_correct": True,
            "score": 100,
            "feedback": "correct",
            "correct_option": "A",
        })
        r = grader._parse_response(raw, total_points=100, qtype="choice")
        assert r.score == 100
        assert r.knowledge_dimension == 100
        assert r.ability_dimension == 100
        assert r.process_dimension == 100
        assert r.innovation_dimension == 100

    @pytest.mark.asyncio
    async def test_parse_score_clamped(self):
        """score 超出 [0, total_points] 范围应被 clamp."""
        grader = get_grader()
        raw = json.dumps({
            "is_correct": True,
            "score": 150,
            "knowledge_dimension": 200,
            "ability_dimension": 0,
            "process_dimension": 0,
            "innovation_dimension": 0,
            "feedback": "x",
        })
        r = grader._parse_response(raw, total_points=100, qtype="short_answer")
        # clamp 到 100
        assert r.knowledge_dimension == 100
        # 综合分 = 100*0.4 + 0+0+0 = 40
        assert abs(r.score - 40.0) < 1e-9

    @pytest.mark.asyncio
    async def test_parse_invalid_json_returns_fallback(self):
        """解析失败时给一半分占位."""
        grader = get_grader()
        raw = "no json at all, just text"
        r = grader._parse_response(raw, total_points=100, qtype="short_answer")
        assert r.is_correct is False
        assert r.score == 50.0  # 0.5 * total_points
        assert r.feedback != ""


# ============================================================
# Prompt 4 维字段存在
# ============================================================

class TestPrompt4D:
    def test_short_answer_prompt_has_4_dim_keys(self):
        """SHORT_ANSWER_SYSTEM_PROMPT 必须含 4 维字段."""
        for key in (
            "knowledge_dimension", "ability_dimension",
            "process_dimension", "innovation_dimension",
        ):
            assert key in SHORT_ANSWER_SYSTEM_PROMPT, f"missing key {key}"

    def test_prompt_keeps_legacy_score_field(self):
        """保持 score 字段(向后兼容)."""
        assert '"score"' in SHORT_ANSWER_SYSTEM_PROMPT


# ============================================================
# QuizRecord ORM 字段
# ============================================================

class TestQuizRecordSchema:
    def test_quiz_record_has_4_dim_columns(self):
        from app.models.classroom import QuizRecord
        columns = {c.name for c in QuizRecord.__table__.columns}
        # 缺口2 4 维
        assert "knowledge_score" in columns
        assert "ability_score" in columns
        assert "process_score" in columns
        assert "innovation_score" in columns
        # 缺口4 人工校准字段
        assert "ai_score" in columns
        assert "ai_comment" in columns
        assert "teacher_comment" in columns
        assert "rubric" in columns
        assert "override_count" in columns
        assert "graded_by" in columns
        assert "graded_by_user_id" in columns
        assert "graded_at" in columns

    def test_quiz_record_grader_default_is_auto(self):
        from app.models.classroom import QuizRecord
        col = QuizRecord.__table__.columns["graded_by"]
        assert col.default.arg == "auto"


# ============================================================
# RadarArtifact 8 维
# ============================================================

class TestRadarArtifact2D:
    def test_radar_has_process_and_innovation(self):
        from app.services.course_schemas import RadarArtifact
        r = RadarArtifact()
        assert hasattr(r, "process")
        assert hasattr(r, "innovation")
        assert r.process == 0.0
        assert r.innovation == 0.0

    def test_radar_legacy_6_dim_still_default(self):
        """向后兼容:6 维老字段仍可读."""
        from app.services.course_schemas import RadarArtifact
        r = RadarArtifact(
            knowledge_mastery=60, code_skill=50, cognitive_level=70,
            learning_goal=80, weakness=40, focus_level=65,
            process=85, innovation=75,
        )
        d = r.model_dump()
        assert d["knowledge_mastery"] == 60
        assert d["process"] == 85
        assert d["innovation"] == 75