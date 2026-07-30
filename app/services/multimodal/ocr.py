"""多模态输入理解：OCR + 解题步骤逻辑分析（M5.6 / #23）

生产实现应接 Seedream / MiniMax-Vision；M5 阶段用占位实现。
"""
from __future__ import annotations

import base64
import logging

logger = logging.getLogger("starlearn.multimodal.ocr")


class MultimodalOCR:
    """OCR + 解题步骤分析。"""

    # 解题步骤数阈值
    MIN_STEP_COUNT = 2

    async def extract_text(self, image_base64: str) -> str:
        """从 base64 图片提取文字。占位：只验证 base64 合法性。

        Args:
            image_base64: base64 编码的图片字符串

        Returns:
            提取的文字（占位实现返回固定占位文本）
        """
        try:
            base64.b64decode(image_base64)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[MultimodalOCR] invalid base64 image: {exc}")
            return ""
        # 占位实现：未来接 Seedream OCR
        return "[OCR placeholder text]"

    async def analyze_solution(
        self,
        text: str,
        knowledge_point: str,
    ) -> dict:
        """分析解题步骤的逻辑完整性。

        Returns:
            {
              verdict: "正确" | "需检查",
              step_count: int,
              logic_break: str | None,
              knowledge_point: str,
            }
        """
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        step_count = len(lines)
        has_equals = "=" in text

        if has_equals and step_count >= self.MIN_STEP_COUNT:
            verdict = "正确"
            logic_break = None
        else:
            verdict = "需检查"
            logic_break = "步骤过少" if step_count < self.MIN_STEP_COUNT else "缺少等式推导"

        return {
            "verdict": verdict,
            "step_count": step_count,
            "logic_break": logic_break,
            "knowledge_point": knowledge_point,
        }