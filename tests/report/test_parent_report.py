"""Tests for ParentReportGenerator (M5.1)."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_generator_creates_monthly_summary():
    """generate() 必须返回含 student_id / period / summary_text 的 ParentReport。"""
    from app.services.report.parent_report import ParentReport, ParentReportGenerator

    gen = ParentReportGenerator()
    report = await gen.generate(
        student_id="s_1",
        period="2026-07",
        data={
            "total_minutes": 2400,
            "topics_mastered": ["勾股定理", "一元二次方程"],
            "topics_struggling": ["三角函数"],
            "streak_days": 15,
        },
    )
    assert report.student_id == "s_1"
    assert report.period == "2026-07"
    assert "勾股定理" in report.summary_text
    assert "三角函数" in report.summary_text
    assert report.delivered_at is None
    assert isinstance(report, ParentReport)


@pytest.mark.asyncio
async def test_generator_marks_delivered_after_send():
    """send() 后 delivered_at 必须被设置。"""
    from app.services.report.parent_report import ParentReportGenerator

    gen = ParentReportGenerator()
    report = await gen.generate(student_id="s_2", period="2026-07", data={})
    delivered = await gen.send(report, channel="email", recipient="parent@example.com")
    assert delivered.delivered_at is not None


@pytest.mark.asyncio
async def test_generator_handles_empty_data():
    """data 为空时不能崩，summary 仍然可读。"""
    from app.services.report.parent_report import ParentReportGenerator

    gen = ParentReportGenerator()
    report = await gen.generate(student_id="s_3", period="2026-07", data={})
    assert "暂无" in report.summary_text or "无" in report.summary_text


@pytest.mark.asyncio
async def test_send_logs_channel_and_recipient():
    """send() 后必须把 channel / recipient 记录到 metadata。"""
    from app.services.report.parent_report import ParentReportGenerator

    gen = ParentReportGenerator()
    report = await gen.generate(student_id="s_4", period="2026-07", data={})
    delivered = await gen.send(report, channel="sms", recipient="13800138000")
    assert delivered.metrics.get("channel") == "sms"
    assert delivered.metrics.get("recipient") == "13800138000"