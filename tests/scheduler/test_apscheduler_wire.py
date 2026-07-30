"""Tests for APScheduler wiring (M4.6)."""
from __future__ import annotations

import pytest

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False


@pytest.mark.skipif(not HAS_APSCHEDULER, reason="apscheduler not installed")
def test_scheduler_wirer_registers_daily_review_job():
    """daily_review job 必须注册到 APScheduler。"""
    from app.services.scheduler.apscheduler_wire import SchedulerWirer

    scheduler = AsyncIOScheduler()
    wirer = SchedulerWirer(scheduler=scheduler)
    wirer.register_daily_review(hour=0, minute=0)
    jobs = scheduler.get_jobs()
    assert any("daily_review" in j.id for j in jobs)


@pytest.mark.skipif(not HAS_APSCHEDULER, reason="apscheduler not installed")
def test_scheduler_wirer_registers_parent_report_job():
    """parent_report job 必须注册到 APScheduler。"""
    from app.services.scheduler.apscheduler_wire import SchedulerWirer

    scheduler = AsyncIOScheduler()
    wirer = SchedulerWirer(scheduler=scheduler)
    wirer.register_parent_report(day=1, hour=8)
    jobs = scheduler.get_jobs()
    assert any("parent_report" in j.id for j in jobs)


@pytest.mark.skipif(not HAS_APSCHEDULER, reason="apscheduler not installed")
def test_scheduler_wirer_replace_existing_allows_re_registration():
    """重复注册必须能成功（不抛异常）。"""
    from app.services.scheduler.apscheduler_wire import SchedulerWirer

    scheduler = AsyncIOScheduler()
    wirer = SchedulerWirer(scheduler=scheduler)
    # 两次注册同一 id，必须不报错（replace_existing=True）
    wirer.register_daily_review(hour=0, minute=0)
    wirer.register_daily_review(hour=1, minute=30)
    jobs = scheduler.get_jobs()
    # 至少有一个 daily_review job
    assert any("daily_review" in j.id for j in jobs)


@pytest.mark.skipif(not HAS_APSCHEDULER, reason="apscheduler not installed")
def test_scheduler_wirer_registers_both_jobs():
    """一次 wirer 应该能注册 daily_review + parent_report 两个 job。"""
    from app.services.scheduler.apscheduler_wire import SchedulerWirer

    scheduler = AsyncIOScheduler()
    wirer = SchedulerWirer(scheduler=scheduler)
    wirer.register_daily_review()
    wirer.register_parent_report()
    jobs = scheduler.get_jobs()
    ids = {j.id for j in jobs}
    assert "daily_review" in ids
    assert "parent_report" in ids