"""AuditAgent: 越狱检测 + 防幻觉审核（M2.2 + M3.2 refactor）

四层防御：
  L0: 越狱正则检测（<50ms）— 使用 app.services.safety.JailbreakDetector
  L1: 引用锚定（基于知识源是否存在）
  L2: 输出长度 / 模板检测
  L3: 综合评分

命名实体化的审核 Agent。M3.2 阶段已替换为正式 JailbreakDetector。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("starlearn.agents.audit")


@dataclass
class AuditResult:
    user_id: str
    risk_level: str  # "low" | "medium" | "high"
    blocked: bool
    reason: str
    jailbreak_score: float = 0.0
    hallucination_score: float = 0.0


class AuditAgent:
    """命名实体化的审核 Agent（L0 越狱 + L1-L4 防幻觉）。"""

    name = "audit_agent"

    # 风险阈值
    JAILBREAK_BLOCK_THRESHOLD = 0.7  # > 此值则拦截
    HALLUCINATION_BLOCK_THRESHOLD = 0.6

    def __init__(self, jailbreak_detector=None) -> None:
        # M3.2: 接入正式 JailbreakDetector（懒加载）
        if jailbreak_detector is None:
            from app.services.safety.jailbreak_detector import JailbreakDetector
            jailbreak_detector = JailbreakDetector(level="L0")
        self._jailbreak = jailbreak_detector

    async def run(
        self,
        user_id: str,
        input_text: str,
        output_text: str,
        knowledge_source: list[str] | None = None,
    ) -> AuditResult:
        knowledge_source = knowledge_source or []

        # L0: 越狱检测（接入正式 JailbreakDetector）
        jb_result = await self._jailbreak.scan(input_text)
        jb_score = jb_result.risk_score
        jb_pattern = jb_result.pattern
        if jb_score >= self.JAILBREAK_BLOCK_THRESHOLD:
            return AuditResult(
                user_id=user_id,
                risk_level="high",
                blocked=True,
                reason=f"jailbreak detected: {jb_pattern} (matched: {jb_result.matched_text!r})",
                jailbreak_score=jb_score,
            )

        # L1-L4: 防幻觉（简化版：基于引用锚定 + 输出模板）
        h_score, h_reason = self._check_hallucination(output_text, knowledge_source)
        if h_score >= self.HALLUCINATION_BLOCK_THRESHOLD:
            return AuditResult(
                user_id=user_id,
                risk_level="medium",
                blocked=True,
                reason=f"hallucination risk: {h_reason}",
                jailbreak_score=jb_score,
                hallucination_score=h_score,
            )

        return AuditResult(
            user_id=user_id,
            risk_level="low",
            blocked=False,
            reason="all checks passed",
            jailbreak_score=jb_score,
            hallucination_score=h_score,
        )

    def _scan_jailbreak(self, text: str) -> tuple[float, str, str]:
        """兼容旧 API 的薄包装：现在走 self._jailbreaker.scan()（同步等待）。

        M3.2 重构后新代码请直接 await self._jailbreak.scan(text)。
        """
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(self._jailbreak.scan(text))
        return result.risk_score, result.pattern, result.matched_text

    def _check_hallucination(
        self,
        output_text: str,
        knowledge_source: list[str],
    ) -> tuple[float, str]:
        """L1-L4 防幻觉简化版。

        评分原则：
          - 没有知识源 + 输出过长 → 中风险
          - 输出与知识源完全无关关键词 → 高风险
          - 输出引用明确（"教材 P45"等） → 低风险
        """
        if not output_text or len(output_text.strip()) < 5:
            return 0.3, "output too short"

        if not knowledge_source:
            # 没有知识源时，输出超长（>500字）给中风险
            if len(output_text) > 500:
                return 0.5, "long output without knowledge source"
            return 0.2, "no knowledge source"

        # 简单锚定：输出是否提到知识源关键词
        source_terms = set()
        for src in knowledge_source:
            for word in re.findall(r"\w+", src):
                if len(word) >= 2:
                    source_terms.add(word.lower())
        out_lower = output_text.lower()
        overlap = sum(1 for term in source_terms if term in out_lower)
        if source_terms and overlap == 0:
            # 短答案 + 通识知识（如 "勾股定理 a²+b²=c²"）：放行
            if len(output_text) <= 200:
                return 0.2, "short general-knowledge answer"
            return 0.65, "no term overlap with knowledge source"

        return 0.1, "term overlap ok"