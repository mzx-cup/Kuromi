"""越狱检测：L0 正则（<50ms）+ L1 LLM 二次判定（<2s）（M3.2）

设计要点：
  - L0 同步正则，覆盖 5 类常见越狱 payload
  - L1 LLM 二次判定（默认关闭，需要 ENABLE_L1_JAILBREAK=true）
  - 返回 JailbreakResult（risk_score / pattern / matched_text）

被以下模块引用：
  - app/agents/audit.py  （M2.2 AuditAgent）
  - app/services/tutor_engine/engine.py  （M2.5 TutorDecisionEngine.process_chat_request）
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("starlearn.safety.jailbreak")


@dataclass
class JailbreakResult:
    risk_score: float  # 0.0-1.0
    pattern: str  # 命中的模式名
    matched_text: str = ""


class JailbreakDetector:
    """L0 正则 + L1 LLM 二次判定。"""

    # L0 正则模式（覆盖常见越狱 payload）
    L0_PATTERNS: list[tuple[str, re.Pattern]] = [
        (
            "ignore_previous",
            re.compile(r"ignore\s+(previous|all|above)\s+(instructions?|prompts?)", re.I),
        ),
        (
            "role_escape",
            re.compile(r"you\s+are\s+now\s+(DAN|jailbreak|evil|admin|developer)", re.I),
        ),
        (
            "system_prompt_leak",
            re.compile(r"(reveal|show|print|dump)\s+(your\s+)?(system\s+prompt|instructions|secret)", re.I),
        ),
        (
            "prompt_injection",
            re.compile(r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]|<<SYS>>", re.I),
        ),
        (
            "bypass_safety",
            re.compile(r"bypass\s+(safety|filter|restriction|jailbreak)", re.I),
        ),
    ]

    L0_SCORE = 0.85  # 命中任一 L0 pattern 给的固定分数

    def __init__(self, level: str = "L0") -> None:
        if level not in ("L0", "L1", "L0+L1"):
            raise ValueError(f"invalid level: {level!r}, expected L0/L1/L0+L1")
        self.level = level

    async def scan(self, text: str) -> JailbreakResult:
        """扫描输入文本，返回风险评估结果。"""
        # L0 正则检测
        max_score, matched_pattern, matched_text = self._scan_l0(text)

        # L1 LLM 二次判定（异步，可选；M3 默认未启用）
        if self.level in ("L1", "L0+L1") and max_score < 0.5:
            llm_score = await self._llm_check(text)
            if llm_score > max_score:
                max_score = llm_score
                matched_pattern = "llm_judge"

        return JailbreakResult(
            risk_score=max_score,
            pattern=matched_pattern,
            matched_text=matched_text,
        )

    def _scan_l0(self, text: str) -> tuple[float, str, str]:
        """L0 正则扫描。返回 (max_score, pattern_name, matched_text)。"""
        for pattern_name, regex in self.L0_PATTERNS:
            m = regex.search(text)
            if m:
                return self.L0_SCORE, pattern_name, m.group(0)
        return 0.0, "", ""

    async def _llm_check(self, text: str) -> float:
        """L1 LLM 二次判定（占位实现，未来接入 MiniMax LLM）。"""
        # 占位：返回 0.0 避免无谓 LLM 调用
        logger.debug(f"[JailbreakDetector] L1 LLM check skipped (placeholder): {text[:50]!r}")
        return 0.0