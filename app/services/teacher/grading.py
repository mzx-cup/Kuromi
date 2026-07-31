# -*- coding: utf-8 -*-
"""
智能评分模块 — Intelligent Grading

参考 OpenMAIC app/api/quiz-grade/route.ts 的逻辑：
  - 构造专用评分 Prompt，强制 LLM 输出结构化 JSON
  - 支持简答题 (short_answer) 和选择题 (choice) 两种题型
  - 返回 is_correct (bool) + feedback (个性化评语) + score (得分)

与 Star-Learn 现有 /api/grade-code 互补：grade-code 负责编程题，此模块负责理论题。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("starlearn.grading")


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class GradeResult:
    """评分结果(缺口2:扩展为 4 维 — 知识/能力/过程/创新)"""
    is_correct: bool
    score: float            # 综合分 = 4 维加权(默认 w_k=0.4 w_a=0.3 w_p=0.2 w_i=0.1)
    total_points: float     # 满分
    feedback: str           # 个性化反馈文本
    correct_answer: str = ""       # 标准答案（简答题）/ 正确选项（选择题）
    key_points_hit: list[str] = field(default_factory=list)   # 命中的知识点
    key_points_missed: list[str] = field(default_factory=list)  # 遗漏的知识点
    raw_llm_response: str = ""    # LLM 原始响应（调试用）

    # ---- 缺口2:4 维评分(对齐 PRD §4.2.6) ----
    knowledge_dimension: float = 0.0      # 知识覆盖度(0~total_points)
    ability_dimension: float = 0.0        # 能力迁移度
    process_dimension: float = 0.0        # 过程完整性
    innovation_dimension: float = 0.0     # 创新独到性
    dimension_weights: dict[str, float] = field(default_factory=lambda: {
        "knowledge": 0.4, "ability": 0.3, "process": 0.2, "innovation": 0.1,
    })
    confidence: float = 1.0               # 4 维一致性(1 - std/满分),供 EnsembleGrader 仲裁用
    arbitration_triggered: bool = False   # 标记是否经多源仲裁
    arbitration_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_correct": self.is_correct,
            "score": self.score,
            "total_points": self.total_points,
            "feedback": self.feedback,
            "correct_answer": self.correct_answer,
            "key_points_hit": self.key_points_hit,
            "key_points_missed": self.key_points_missed,
            "dimensions": {
                "knowledge": self.knowledge_dimension,
                "ability": self.ability_dimension,
                "process": self.process_dimension,
                "innovation": self.innovation_dimension,
            },
            "dimension_weights": self.dimension_weights,
            "confidence": self.confidence,
            "arbitration_triggered": self.arbitration_triggered,
        }

    @staticmethod
    def compute_weighted_score(
        knowledge: float, ability: float, process: float, innovation: float,
        weights: dict[str, float] | None = None,
    ) -> float:
        """按默认权重 4 维 → 综合分(缺口2 + 缺口3 共用工具)."""
        w = weights or {"knowledge": 0.4, "ability": 0.3, "process": 0.2, "innovation": 0.1}
        return (
            knowledge * w["knowledge"]
            + ability * w["ability"]
            + process * w["process"]
            + innovation * w["innovation"]
        )


# =============================================================================
# 评分 Prompt 模板 — 提取自 OpenMAIC quiz-grade + Star-Learn 需求
# =============================================================================

SHORT_ANSWER_SYSTEM_PROMPT = """你是一位专业的教育评估专家。请根据标准答案和评分要点，对学生的简答题答案进行评分。

【评分原则】
1. 不必要求学生与标准答案逐字一致，理解正确即可得分
2. 部分正确应给予部分分数，不要全有或全无
3. 评语要个性化、有建设性，帮助学生理解不足之处
4. 如果学生答错了，评语中应温和地指出正确方向
5. (缺口2)按"知识 / 能力 / 过程 / 创新"四维独立打分，每维 0~满分；综合分(score)由这 4 维按权重(0.4/0.3/0.2/0.1)自动算出,你也可以直接给 score

【必须输出纯JSON格式，不要包含其他内容】
{
  "is_correct": true/false,
  "score": <数字, 0到满分, 综合分>,
  "knowledge_dimension":  <0~满分, 知识覆盖度>,
  "ability_dimension":    <0~满分, 能力迁移度>,
  "process_dimension":    <0~满分, 过程完整性>,
  "innovation_dimension": <0~满分, 创新独到性>,
  "feedback": "<个性化评语, 1-3句话, 先肯定再指出不足>",
  "key_points_hit": ["<学生命中的知识点1>", "<知识点2>"],
  "key_points_missed": ["<学生遗漏的知识点1>", "<知识点2>"]
}"""

SHORT_ANSWER_USER_PROMPT = """【题目】
{question}

【标准答案 / 参考答案】
{standard_answer}

【满分】{total_points} 分

【评分要点】
{key_points}

【学生答案】
{user_answer}

请对以上简答题进行评分。"""

CHOICE_SYSTEM_PROMPT = """你是一位专业的教育评估专家。请对学生的选择题答案进行评判。

【评分原则】
1. 选择题正确即满分，错误即零分
2. 如果学生选错了，评语中应简要解释正确选项为什么是对的
3. 评语要简短、友善

【必须输出纯JSON格式，不要包含其他内容】
{
  "is_correct": true/false,
  "score": <满分 或 0>,
  "feedback": "<简短评语, 1-2句话>",
  "correct_option": "<正确选项>"
}"""

CHOICE_USER_PROMPT = """【题目】
{question}

【选项】
{options_text}

【正确答案】{correct_option}

【满分】{total_points} 分

【学生选择】{user_answer}

请对以上选择题进行评判。"""


# =============================================================================
# Grader 评分器
# =============================================================================

class Grader:
    """
    智能评分器。

    用法:
        grader = Grader()
        result = await grader.grade(
            question="什么是HDFS的架构?",
            standard_answer="HDFS采用主从架构...",
            user_answer="HDFS有NameNode和DataNode...",
            question_type="short_answer",
            total_points=10,
            key_points=["主从架构", "NameNode", "DataNode"],
        )
    """

    def __init__(self, llm_call_fn=None):
        """
        Args:
            llm_call_fn: async (system_prompt, user_prompt, temperature) -> str
                         默认使用 llm_stream.call_llm_async
        """
        self._llm_call = llm_call_fn

    async def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        if self._llm_call:
            return await self._llm_call(system_prompt, user_prompt, temperature)

        from llm_stream import call_llm_async
        return await call_llm_async(system_prompt, user_prompt, temperature)

    async def grade(
        self,
        question: str,
        standard_answer: str,
        user_answer: str,
        question_type: str = "short_answer",
        total_points: float = 10.0,
        key_points: list[str] | None = None,
        options: list[str] | None = None,
        correct_option: str = "",
    ) -> GradeResult:
        """
        评分入口。

        Args:
            question: 题目文本
            standard_answer: 标准答案（简答）/ 正确选项描述（选择）
            user_answer: 学生答案
            question_type: "short_answer" | "choice"
            total_points: 满分值
            key_points: 评分要点列表（简答题用）
            options: 选项列表（选择题用，如 ["A. xxx", "B. xxx"]）
            correct_option: 正确选项标签（选择题用，如 "A"）
        """
        if question_type == "choice":
            return await self._grade_choice(
                question, options or [], correct_option, user_answer, total_points
            )
        else:
            return await self._grade_short_answer(
                question, standard_answer, user_answer, total_points, key_points or []
            )

    # ---- 私有方法 ----

    async def _grade_short_answer(
        self,
        question: str,
        standard_answer: str,
        user_answer: str,
        total_points: float,
        key_points: list[str],
    ) -> GradeResult:
        key_points_text = "\n".join(f"- {kp}" for kp in key_points) if key_points else "无特殊评分要点"

        user_prompt = SHORT_ANSWER_USER_PROMPT.format(
            question=question,
            standard_answer=standard_answer,
            total_points=int(total_points),
            key_points=key_points_text,
            user_answer=user_answer,
        )

        return await self._call_and_parse(
            SHORT_ANSWER_SYSTEM_PROMPT, user_prompt, total_points, "short_answer"
        )

    async def _grade_choice(
        self,
        question: str,
        options: list[str],
        correct_option: str,
        user_answer: str,
        total_points: float,
    ) -> GradeResult:
        options_text = "\n".join(options) if options else ""

        user_prompt = CHOICE_USER_PROMPT.format(
            question=question,
            options_text=options_text,
            correct_option=correct_option,
            total_points=int(total_points),
            user_answer=user_answer,
        )

        return await self._call_and_parse(
            CHOICE_SYSTEM_PROMPT, user_prompt, total_points, "choice"
        )

    async def _call_and_parse(
        self, system_prompt: str, user_prompt: str, total_points: float, qtype: str
    ) -> GradeResult:
        try:
            raw = await self._call_llm(system_prompt, user_prompt, temperature=0.2)
            return self._parse_response(raw, total_points, qtype)
        except Exception as e:
            logger.error("Grading LLM call failed: %s", e)
            return GradeResult(
                is_correct=False,
                score=0,
                total_points=total_points,
                feedback=f"评分服务暂时不可用，请稍后重试。({e})",
                raw_llm_response=str(e),
            )

    def _parse_response(self, raw: str, total_points: float, qtype: str) -> GradeResult:
        """解析 LLM 返回的 JSON,带容错回退. 缺口2:支持 4 维评分字段."""
        try:
            # 尝试提取 JSON 块
            json_match = re.search(r'\{[\s\S]*\}', raw.strip())
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                raise ValueError("No JSON found in LLM response")

            is_correct = bool(data.get("is_correct", False))
            feedback = str(data.get("feedback", ""))

            # ---- 缺口2:解析 4 维评分 ----
            # 兼容老 JSON(无 dimensions 字段):score 全填到 knowledge_dimension
            knowledge = float(data.get("knowledge_dimension", data.get("score", 0)))
            ability = float(data.get("ability_dimension", 0))
            process = float(data.get("process_dimension", 0))
            innovation = float(data.get("innovation_dimension", 0))

            if qtype == "choice":
                # 选择题无 4 维语义,4 维都等于 score
                llm_score = float(data.get("score", 0))
                score = max(0.0, min(total_points, llm_score))
                knowledge = ability = process = innovation = score
            else:
                # 简答题:综合分 = 4 维加权
                # clamp 每维
                knowledge = max(0.0, min(total_points, knowledge))
                ability = max(0.0, min(total_points, ability))
                process = max(0.0, min(total_points, process))
                innovation = max(0.0, min(total_points, innovation))
                score = GradeResult.compute_weighted_score(
                    knowledge, ability, process, innovation,
                )

            # 计算 confidence = 1 - 4 维标准差 / 满分(仲裁输入)
            if total_points > 0 and qtype == "short_answer":
                mean_dim = (knowledge + ability + process + innovation) / 4
                variance = ((knowledge - mean_dim) ** 2 + (ability - mean_dim) ** 2
                           + (process - mean_dim) ** 2 + (innovation - mean_dim) ** 2) / 4
                std = variance ** 0.5
                confidence = max(0.0, 1.0 - std / total_points)
            else:
                confidence = 1.0

            result = GradeResult(
                is_correct=is_correct,
                score=score,
                total_points=total_points,
                feedback=feedback,
                knowledge_dimension=knowledge,
                ability_dimension=ability,
                process_dimension=process,
                innovation_dimension=innovation,
                confidence=confidence,
                raw_llm_response=raw,
            )

            if qtype == "short_answer":
                result.correct_answer = str(data.get("correct_answer", ""))
                result.key_points_hit = data.get("key_points_hit", [])
                result.key_points_missed = data.get("key_points_missed", [])
            elif qtype == "choice":
                result.correct_answer = str(data.get("correct_option", ""))

            return result

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to parse grading JSON: %s, raw=%s", e, raw[:200])
            # 回退:给一半分 + 通用评语
            fallback_score = total_points * 0.5
            return GradeResult(
                is_correct=False,
                score=fallback_score,
                total_points=total_points,
                feedback="已收到你的答案，请参考标准答案进行对照学习。",
                raw_llm_response=raw,
            )


# 默认实例
_grader: Grader | None = None


def get_grader() -> Grader:
    global _grader
    if _grader is None:
        _grader = Grader()
    return _grader
