# -*- coding: utf-8 -*-
"""pytest 全局配置 — 自定义 markers + HTML 报告支持

使用方法:
  pytest tests/ -m "not slow and not ai"    # 跳过慢速和 AI 测试
  pytest tests/ -m "slow"                    # 只跑慢速测试
  pytest tests/ -v --html=reports/test-report.html --self-contained-html
"""

import pytest


def pytest_configure(config):
    """注册自定义 pytest markers"""
    config.addinivalue_line(
        "markers",
        "slow: 标记为慢速测试（需要实际 API 调用或 LLM 请求）"
    )
    config.addinivalue_line(
        "markers",
        "ai: 标记为 AI/LLM 相关测试（需消耗 API 配额）"
    )
    config.addinivalue_line(
        "markers",
        "cv: 标记为 CV 图像/视频相关测试"
    )
    config.addinivalue_line(
        "markers",
        "e2e: 标记为端到端测试（需要运行中的服务）"
    )
    config.addinivalue_line(
        "markers",
        "unit: 标记为单元测试（纯逻辑，无外部依赖）"
    )
