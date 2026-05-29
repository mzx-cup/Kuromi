# -*- coding: utf-8 -*-
"""
TutorDecisionEngine — 统一智能导师决策引擎

将问答、防幻觉、链接推荐、主动推送统一到一个决策管道中。
所有学生交互（提问、困难上报、登录、遥测）都经过此引擎，
由它统一决定输出什么内容、附什么链接、是否推送主动消息。

入口: TutorDecisionEngine.decide(event: TutorEvent) -> ResponseEnvelope
"""

from __future__ import annotations

from app.services.tutor_engine.engine import TutorDecisionEngine
from app.services.tutor_engine.models import (
    TutorEvent,
    TutorEventType,
    RichContext,
    ResponseEnvelope,
    Citation,
    Link,
    ProactiveAction,
    MessagePriority,
    ActionType,
    ConfidenceReport,
)
from app.services.tutor_engine.response_composer import ResponseComposer
from app.services.tutor_engine.context_aggregator import ContextAggregator
from app.services.tutor_engine.action_ledger import ActionLedger

__all__ = [
    "TutorDecisionEngine",
    "TutorEvent",
    "TutorEventType",
    "RichContext",
    "ResponseEnvelope",
    "Citation",
    "Link",
    "ProactiveAction",
    "MessagePriority",
    "ActionType",
    "ConfidenceReport",
    "ResponseComposer",
    "ContextAggregator",
    "ActionLedger",
]