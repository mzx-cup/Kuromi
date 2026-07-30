"""Tests for MultimodalOCR (M5.6)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_ocr_extracts_text_from_base64_image():
    """extract_text() 必须返回字符串（哪怕占位）。"""
    from app.services.multimodal.ocr import MultimodalOCR

    ocr = MultimodalOCR()
    # 1x1 透明 PNG
    png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    result = await ocr.extract_text(image_base64=png_b64)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_ocr_returns_empty_for_invalid_base64():
    """非法 base64 必须返回空字符串（不崩）。"""
    from app.services.multimodal.ocr import MultimodalOCR

    ocr = MultimodalOCR()
    result = await ocr.extract_text(image_base64="!!!not-base64!!!")
    assert result == ""


@pytest.mark.asyncio
async def test_ocr_analyzes_solution_correctly():
    """analyze_solution 必须能判断标准解法为正确。"""
    from app.services.multimodal.ocr import MultimodalOCR

    ocr = MultimodalOCR()
    solution_text = (
        "已知 a=3, b=4, 求 c\n"
        "步骤 1: c² = a² + b² = 9 + 16 = 25\n"
        "步骤 2: c = √25 = 5"
    )
    analysis = await ocr.analyze_solution(solution_text, knowledge_point="勾股定理")
    assert "verdict" in analysis
    assert analysis["verdict"] == "正确"
    assert analysis["step_count"] >= 2


@pytest.mark.asyncio
async def test_ocr_flags_short_solution_as_incomplete():
    """步骤过少必须判为需检查 + 标记 logic_break。"""
    from app.services.multimodal.ocr import MultimodalOCR

    ocr = MultimodalOCR()
    analysis = await ocr.analyze_solution("a=3, b=4", knowledge_point="勾股定理")
    assert analysis["verdict"] == "需检查"
    assert analysis["logic_break"] == "步骤过少"