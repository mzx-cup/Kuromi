"""CriticAgent: L3 防幻觉独立 Agent（专门挑错）（M4.4）

与 AuditAgent 的区别：
  - AuditAgent 检查「输出是否符合知识源」（L1-L4 防幻觉）
  - CriticAgent 独立审视「答案是否真的回答了问题」（L3 独立评审）

使用场景：
  - 在 AuditAgent 放行后，作为最后一道质量门
  - 在 SocraticEvaluatorAgent 评分时，提供额外评分维度
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CritiqueResult:
    quality: str  # "low" | "medium" | "high"
    score: float  # 0.0-1.0
    issues: list[str]


class CriticAgent:
    """L3 防幻觉独立 Agent。"""

    name = "critic_agent"

    # 评分阈值
    HIGH_QUALITY_THRESHOLD = 0.8
    MEDIUM_QUALITY_THRESHOLD = 0.5
    MIN_ANSWER_LENGTH = 10  # 短于 10 字符判 answer_too_short

    async def review(self, answer: str, reference: str) -> CritiqueResult:
        """审视答案质量。

        Args:
            answer: 学生/AI 的回答
            reference: 参考答案（或知识源片段）

        Returns:
            CritiqueResult(quality, score, issues)
        """
        score = self._score(answer, reference)
        if score > self.HIGH_QUALITY_THRESHOLD:
            quality = "high"
        elif score >= self.MEDIUM_QUALITY_THRESHOLD:
            quality = "medium"
        else:
            quality = "low"

        issues = []
        if len(answer.strip()) < self.MIN_ANSWER_LENGTH:
            issues.append("answer_too_short")
        if reference and not self._has_key_terms(answer, reference):
            issues.append("missing_key_terms")

        return CritiqueResult(quality=quality, score=score, issues=issues)

    def _score(self, answer: str, reference: str) -> float:
        """基于关键词重合度计算分数。"""
        if not reference:
            return 0.5

        ref_words = set(self._tokenize(reference))
        ans_words = set(self._tokenize(answer))
        if not ref_words:
            return 0.5

        overlap = len(ref_words & ans_words)
        return min(1.0, overlap / len(ref_words))

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """中英文混合分词（简化版）。"""
        import re

        # 拆出 ASCII 单词 + 单个中文字符
        tokens: list[str] = []
        for match in re.finditer(r"[A-Za-z]+|[0-9]+|[一-鿿]", text):
            tok = match.group().lower()
            if tok:
                tokens.append(tok)
        return tokens

    @staticmethod
    def _has_key_terms(answer: str, reference: str) -> bool:
        """答案是否包含 reference 的前 5 个关键词中的至少一个。"""
        ref_tokens = CriticAgent._tokenize(reference)[:5]
        ans_lower = answer.lower()
        return any(tok in ans_lower for tok in ref_tokens)