"""缺口3:多 Agent 联合打分测试.

覆盖:
  - 加权平均(分数差距小 → 不仲裁)
  - 仲裁触发(分数差距 > 25%)
  - Judge 失败 fallback 到中位数
  - 所有 grader 失败 → 0 分 + error arbitration
  - 与 Grader 接口向后兼容(签名一致)
  - EnsembleGradeResult 含 source_scores / arbitration
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.teacher.grading import GradeResult
from app.services.teacher.ensemble_grading import (
    EnsembleGradeResult,
    EnsembleGrader,
    SourceScore,
)


# ============================================================
# 测试辅助 - 假 Grader
# ============================================================

class FakeGrader:
    """测试用 grader,返回预设分数."""

    def __init__(self, name: str, scores: list[float] | float):
        self.name = name
        if isinstance(scores, (int, float)):
            self._scores = [float(scores)] * 5
        else:
            self._scores = list(scores)
        self._call_count = 0

    async def grade(self, *args, **kwargs):
        score = self._scores[self._call_count % len(self._scores)]
        self._call_count += 1
        return GradeResult(
            is_correct=score > 50,
            score=score,
            total_points=100.0,
            feedback=f"fake {self.name}",
            knowledge_dimension=score,
            ability_dimension=score,
            process_dimension=score,
            innovation_dimension=score,
            confidence=0.9,
        )


# ============================================================
# 加权平均 — 差距小,不仲裁
# ============================================================

class TestWeightedAverage:
    @pytest.mark.asyncio
    async def test_no_arbitration_when_close(self):
        grader = EnsembleGrader(
            graders=[FakeGrader("a", 80), FakeGrader("b", 82)],
            grader_names=["llm_low", "llm_high"],
            weights={"llm_low": 0.5, "llm_high": 0.5},
        )
        r = await grader.grade(
            question="Q", standard_answer="A", user_answer="ua",
            question_type="short_answer", total_points=100,
        )
        assert isinstance(r, EnsembleGradeResult)
        assert abs(r.score - 81.0) < 1e-9  # (80+82)/2
        assert r.arbitration["triggered"] is False
        assert len(r.source_scores) == 2

    @pytest.mark.asyncio
    async def test_custom_weights(self):
        grader = EnsembleGrader(
            graders=[FakeGrader("a", 80), FakeGrader("b", 100)],
            grader_names=["llm_low", "llm_high"],
            weights={"llm_low": 0.7, "llm_high": 0.3},
        )
        r = await grader.grade(
            question="Q", standard_answer="A", user_answer="ua",
            total_points=100,
        )
        # 80*0.7 + 100*0.3 = 56+30 = 86
        assert abs(r.score - 86.0) < 1e-9


# ============================================================
# 仲裁 — 差距 > 阈值
# ============================================================

class TestArbitration:
    @pytest.mark.asyncio
    async def test_arbitration_triggered_when_std_high(self):
        """std/total = 25 / 100 = 0.25 → 刚到阈值,触发."""
        grader = EnsembleGrader(
            graders=[FakeGrader("a", 50), FakeGrader("b", 100)],
            grader_names=["llm_low", "llm_high"],
            arbitration_threshold=0.20,  # 20% 阈值,50-100 差距 25% > 20%
            judge_factory=lambda: AsyncMock(
                appeal=AsyncMock(return_value=85.0),
            ),
        )
        r = await grader.grade(
            question="Q", standard_answer="A", user_answer="ua",
            total_points=100,
        )
        assert r.arbitration["triggered"] is True
        assert r.arbitration["judge_score"] == 85.0
        assert r.score == 85.0  # 采纳 Judge

    @pytest.mark.asyncio
    async def test_judge_failure_fallback_to_median(self):
        """Judge 抛异常 → fallback 中位数."""
        class FailingJudge:
            async def appeal(self, **kwargs):
                raise RuntimeError("Judge service down")

        grader = EnsembleGrader(
            graders=[FakeGrader("a", 60), FakeGrader("b", 100)],
            grader_names=["llm_low", "llm_high"],
            arbitration_threshold=0.10,  # 10% 必触发
            judge_factory=lambda: FailingJudge(),
        )
        r = await grader.grade(
            question="Q", standard_answer="A", user_answer="ua",
            total_points=100,
        )
        assert r.arbitration["triggered"] is True
        assert r.arbitration["judge_score"] is None
        assert "Judge 失败" in r.arbitration["reason"]
        # 中位数 = 80
        assert r.score == 80.0


# ============================================================
# 全失败
# ============================================================

class TestAllGradersFailing:
    @pytest.mark.asyncio
    async def test_all_failing_returns_zero(self):
        class FailingGrader:
            async def grade(self, *args, **kwargs):
                raise RuntimeError("LLM timeout")

        grader = EnsembleGrader(
            graders=[FailingGrader(), FailingGrader()],
            grader_names=["g1", "g2"],
        )
        r = await grader.grade(
            question="Q", standard_answer="A", user_answer="ua",
            total_points=100,
        )
        assert r.score == 0.0
        assert r.arbitration["reason"] == "all_graders_failed"
        assert r.arbitration["source_count"] == 0

    @pytest.mark.asyncio
    async def test_partial_failure_uses_remaining(self):
        class FailingGrader:
            async def grade(self, *args, **kwargs):
                raise RuntimeError("down")

        grader = EnsembleGrader(
            graders=[FailingGrader(), FakeGrader("b", 75)],
            grader_names=["a", "b"],
            weights={"a": 0.5, "b": 0.5},
        )
        r = await grader.grade(
            question="Q", standard_answer="A", user_answer="ua",
            total_points=100,
        )
        # 只 b 跑成功 → 分数 75(无加权平均)
        assert r.score == 75.0
        assert len(r.source_scores) == 1


# ============================================================
# SourceScore / 继承
# ============================================================

class TestSourceScoreAndInheritance:
    @pytest.mark.asyncio
    async def test_source_scores_preserve_grader_names(self):
        grader = EnsembleGrader(
            graders=[FakeGrader("x", 80), FakeGrader("y", 80)],
            grader_names=["custom_a", "custom_b"],
        )
        r = await grader.grade(
            question="Q", standard_answer="A", user_answer="ua",
            total_points=100,
        )
        names = [s.grader_name for s in r.source_scores]
        assert names == ["custom_a", "custom_b"]
        for s in r.source_scores:
            assert s.score == 80
            assert s.confidence == 0.9

    @pytest.mark.asyncio
    async def test_inherits_4_dim_from_last_grader(self):
        """EnsembleGradeResult 应保留 4 维评分(来自最后一次成功的 grader)."""
        grader = EnsembleGrader(
            graders=[FakeGrader("a", 80), FakeGrader("b", 80)],
        )
        r = await grader.grade(
            question="Q", standard_answer="A", user_answer="ua",
            total_points=100,
        )
        assert r.knowledge_dimension == 80
        assert r.ability_dimension == 80
        assert r.process_dimension == 80
        assert r.innovation_dimension == 80


# ============================================================
# 单例
# ============================================================

class TestSingleton:
    def test_get_ensemble_grader_returns_singleton(self):
        from app.services.teacher.ensemble_grading import (
            get_ensemble_grader,
            set_ensemble_grader,
        )
        g1 = get_ensemble_grader()
        g2 = get_ensemble_grader()
        assert g1 is g2

    def test_set_ensemble_grader_injects_custom(self):
        from app.services.teacher.ensemble_grading import (
            get_ensemble_grader,
            set_ensemble_grader,
        )
        custom = EnsembleGrader(graders=[FakeGrader("x", 70)])
        set_ensemble_grader(custom)
        assert get_ensemble_grader() is custom