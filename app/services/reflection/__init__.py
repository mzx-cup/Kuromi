"""Reflection 服务命名空间（M5.4）。

导出 ReflectionLogAgent（极简版：generate_questions + aggregate_weekly）。
"""
from __future__ import annotations

from app.services.reflection.log_agent import ReflectionLogAgent

__all__ = ["ReflectionLogAgent"]