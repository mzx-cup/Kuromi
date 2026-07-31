"""缺口3:多 Agent 联合打分(加权平均 + 差异仲裁).

设计:
  - 组合多个 Grader 实例(默认 2 个不同温度的 LLM Grader)并发评分
  - 加权平均得最终分
  - 标准差/满分 > 0.25 时触发 JudgeAgent 仲裁,采纳 Judge 重判分数
  - 仲裁失败时退化为中位数
  - 与现有 Grader 接口向后兼容

公开 API:
  - EnsembleGrader(graders, weights, judge_factory, arbitration_threshold)
  - ensemble.grade(...) -> EnsembleGradeResult
  - get_ensemble_grader() -> 全局单例
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from statistics import median
from typing import Any, Awaitable, Callable, Optional

from app.services.teacher.grading import GradeResult, Grader

logger = logging.getLogger("starlearn.ensemble_grading")


@dataclass
class SourceScore:
    """单个评分员的输出快照."""
    grader_name: str
    score: float
    confidence: float = 1.0
    raw: dict = field(default_factory=dict)


@dataclass
class EnsembleGradeResult(GradeResult):
    """联合打分结果,继承 GradeResult 全部字段 + 新增 source_scores / arbitration."""
    source_scores: list[SourceScore] = field(default_factory=list)
    arbitration: dict = field(default_factory=dict)
    """    {"triggered": bool, "std": float, "threshold": float,
            "judge_score": float | None, "reason": str, "source_count": int}
    """


# ============================================================
# 默认 Judge(直接调 LLM,Prompt 提取自 SocraticEvaluator 思路)
# ============================================================

JUDGE_SYSTEM_PROMPT = """你是评分仲裁师。{n} 位评分员对同一答案给出了不一致的分数:

{sources}

差异原因可能:
  - 某评分员理解偏差
  - 标准答案模糊导致主观解读
  - 学生答案本身多解(开放题)

请你重新评判,以学生原始答案为输入,综合考虑:
  - 与标准答案的匹配度
  - 关键知识点的覆盖
  - 推理/过程的完整性
  - 是否体现独到见解

请输出 JSON: {{"judge_score": <0~total_points>}}

题目:{question}
标准答案:{standard_answer}
学生答案:{user_answer}
满分:{total_points}
"""


async def _default_judge_appeal(
    question: str,
    standard_answer: str,
    user_answer: str,
    total_points: float,
    sources: list[SourceScore],
) -> float:
    """默认 Judge:直接调 LLM 重新评分."""
    sources_text = "\n".join(
        f"  - {s.grader_name}: {s.score:.1f} 分 (置信度 {s.confidence:.2f})"
        for s in sources
    )
    from llm_stream import call_llm_async
    import json
    import re

    prompt = JUDGE_SYSTEM_PROMPT.format(
        n=len(sources),
        sources=sources_text,
        question=question,
        standard_answer=standard_answer or "(无)",
        user_answer=user_answer or "(空)",
        total_points=int(total_points),
    )
    raw = await call_llm_async(
        system_prompt="你是评分仲裁师,严格按 JSON 输出。",
        user_prompt=prompt,
        temperature=0.2,
    )
    m = re.search(r'\{[\s\S]*\}', raw)
    if m:
        try:
            data = json.loads(m.group(0))
            score = float(data.get("judge_score", 0))
            return max(0.0, min(total_points, score))
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
    # 解析失败 → 中位数
    return median([s.score for s in sources])


# ============================================================
# EnsembleGrader 主类
# ============================================================

class EnsembleGrader:
    """多 Agent 联合打分 — 加权平均 + 差异仲裁.

    默认 graders = [Grader(temperature=0.1), Grader(temperature=0.4)]
    默认 weights = {"llm_low": 0.5, "llm_high": 0.5}
    仲裁阈值 ARBITRATION_THRESHOLD = 0.25(标准差/满分比例)
    """

    DEFAULT_WEIGHTS = {
        "llm_low": 0.5,      # temperature=0.1 的稳定 LLM
        "llm_high": 0.5,     # temperature=0.4 的发散 LLM
    }
    ARBITRATION_THRESHOLD = 0.25  # std/total_points > 25% 触发

    def __init__(
        self,
        graders: Optional[list[Grader]] = None,
        weights: Optional[dict[str, float]] = None,
        judge_factory: Optional[Callable[[], Any]] = None,
        arbitration_threshold: float = ARBITRATION_THRESHOLD,
        grader_names: Optional[list[str]] = None,
    ):
        # 默认 graders = 2 个 Grader 实例(同一 LLM,不同 temperature 通过 llm_call_fn 注入)
        # 实际生产环境通过 dependencies 注入 temperature 不同的 grader
        if graders is None:
            self.graders = [Grader(), Grader()]
        else:
            self.graders = graders
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.judge_factory = judge_factory
        self.arbitration_threshold = arbitration_threshold
        # grader name 列表,默认按 index 取名 llm_low / llm_high
        if grader_names is None:
            self.grader_names = [f"llm_{'low' if i == 0 else 'high'}" for i in range(len(self.graders))]
        else:
            self.grader_names = grader_names

    async def grade(
        self,
        question: str,
        standard_answer: str,
        user_answer: str,
        question_type: str = "short_answer",
        total_points: float = 10.0,
        key_points: Optional[list[str]] = None,
        options: Optional[list[str]] = None,
        correct_option: str = "",
        **kwargs: Any,
    ) -> EnsembleGradeResult:
        """联合评分入口.

        Returns:
            EnsembleGradeResult 含 source_scores / arbitration 信息
        """
        # 1. 并发跑所有 grader
        tasks = [
            g.grade(
                question, standard_answer, user_answer,
                question_type, total_points, key_points, options, correct_option,
            )
            for g in self.graders
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        sources: list[SourceScore] = []
        last_ok: Optional[GradeResult] = None
        for name, r in zip(self.grader_names, results):
            if isinstance(r, Exception):
                logger.warning(f"[ensemble] grader {name} 异常: {r}")
                continue
            assert isinstance(r, GradeResult)
            sources.append(SourceScore(
                grader_name=name,
                score=r.score,
                confidence=r.confidence,
                raw=r.to_dict(),
            ))
            last_ok = r

        if not sources or last_ok is None:
            # 所有 grader 全失败 → 退化为 0 分
            return EnsembleGradeResult(
                is_correct=False,
                score=0.0,
                total_points=total_points,
                feedback="所有评分源失败",
                arbitration={"triggered": False, "reason": "all_graders_failed", "source_count": 0},
            )

        # 2. 加权平均
        total_w = sum(self.weights.get(s.grader_name, 0.3) for s in sources)
        final = sum(
            s.score * self.weights.get(s.grader_name, 0.3)
            for s in sources
        ) / total_w

        # 3. 仲裁判定
        vals = [s.score for s in sources]
        if len(vals) >= 2:
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / len(vals)
            std = variance ** 0.5
        else:
            std = 0.0
        triggered = (std / total_points) > self.arbitration_threshold if total_points > 0 else False

        arbitration = {
            "triggered": triggered,
            "std": std,
            "threshold": self.arbitration_threshold * total_points,
            "judge_score": None,
            "reason": "",
            "source_count": len(sources),
        }

        if triggered:
            arbitration["reason"] = f"std={std:.2f} 超过阈值 {self.arbitration_threshold * total_points:.2f}"
            # 调 Judge 重判
            try:
                if self.judge_factory is not None:
                    judge = self.judge_factory()
                    judge_score = await judge.appeal(
                        question=question,
                        standard_answer=standard_answer,
                        user_answer=user_answer,
                        total_points=total_points,
                        sources=sources,
                    )
                else:
                    judge_score = await _default_judge_appeal(
                        question=question,
                        standard_answer=standard_answer,
                        user_answer=user_answer,
                        total_points=total_points,
                        sources=sources,
                    )
                arbitration["judge_score"] = judge_score
                # 采纳 Judge 分数作为最终分
                final = judge_score
            except Exception as e:
                logger.warning(f"[ensemble] Judge 失败: {e}; 退回中位数")
                arbitration["reason"] += f"; Judge 失败 {e}, 退回中位数"
                final = median(vals)

        # 4. 组装结果(继承 last_ok 的 4 维,只覆盖 score + arbitration)
        # last_ok.__dict__ 已含 score 等字段,显式覆盖时需先 pop 避免冲突
        result_fields = dict(last_ok.__dict__)
        result_fields["score"] = final
        result_fields["arbitration_triggered"] = triggered
        return EnsembleGradeResult(
            **result_fields,
            source_scores=sources,
            arbitration=arbitration,
        )


# ============================================================
# 全局单例
# ============================================================

_ensemble: Optional[EnsembleGrader] = None


def get_ensemble_grader() -> EnsembleGrader:
    global _ensemble
    if _ensemble is None:
        _ensemble = EnsembleGrader()
    return _ensemble


def set_ensemble_grader(grader: EnsembleGrader) -> None:
    """注入自定义 ensemble(测试用)."""
    global _ensemble
    _ensemble = grader