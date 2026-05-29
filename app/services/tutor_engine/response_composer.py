# -*- coding: utf-8 -*-
"""
ResponseComposer — 响应组装器

将 TutorDecisionEngine 的各子组件输出组装为统一、兼容现有前端的 SSE 事件流。

设计原则：
  - 零前端改动：输出格式与现有 SSE 处理逻辑（js/index.js:smartAgent）完全兼容
  - 统一事件类型：data 事件承载文本，links/citations/proactive 事件承载结构化数据
  - 明确终止：以 [DONE] 标记结束流式传输
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Optional

from app.services.tutor_engine.models import (
    Citation,
    Link,
    ProactiveAction,
    ResponseEnvelope,
)

logger = logging.getLogger("starlearn.tutor_engine")


class ResponseComposer:
    """
    响应组装器。

    负责将 Engine 的决策结果组装为前端可用的 SSE 流。
    支持两种模式：
      1. 流式模式（streaming）—— 用于问答场景，文本逐字输出
      2. 通知模式（notification）—— 用于纯推送场景，直接输出结构化数据
    """

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # 流式模式：问答场景
    # ------------------------------------------------------------------

    async def stream_answer(
        self,
        envelope: ResponseEnvelope,
    ) -> AsyncIterator[str]:
        """
        组装完整 SSE 流，兼容现有前端。

        输出序列:
          1. data: {chunk}  —— 回答文本流
          2. data: [METADATA]{{...}}  —— 结构化数据（链接、引用、推送）
          3. data: [DONE]   —— 流式结束标记
        """
        trace = envelope.engine_trace or []
        trace.append("📦 ResponseComposer 组装 SSE 流...")

        # Step 1: 文本流（如果存在）
        if envelope.answer_stream is not None:
            async for chunk in envelope.answer_stream:
                if chunk:
                    yield chunk
        elif envelope.answer_text:
            yield envelope.answer_text

        # Step 2: 结构化元数据事件
        # 将链接、引用、推送打包为一个 JSON 对象
        metadata = self._build_metadata(envelope)
        if metadata:
            # 使用特殊前缀让前端可以识别这是元数据而非普通文本
            yield f"\n\n[METADATA]{json.dumps(metadata, ensure_ascii=False)}"

        # Step 3: 结束标记
        yield "\n\n[DONE]"

    # ------------------------------------------------------------------
    # 通知模式：主动推送场景
    # ------------------------------------------------------------------

    async def stream_notification(
        self,
        envelope: ResponseEnvelope,
    ) -> AsyncIterator[str]:
        """
        纯通知/推送场景的 SSE 流。

        无文本流，直接输出推送动作和链接。
        """
        # 仅输出推送动作
        for action in envelope.proactive_actions:
            yield self._format_action_sse(action)

        # 如果有链接，也输出
        if envelope.links:
            metadata = {"links": [link.to_dict() for link in envelope.links]}
            yield f"[METADATA]{json.dumps(metadata, ensure_ascii=False)}"

        yield "\n\n[DONE]"

    # ------------------------------------------------------------------
    # 静态输出：非流式场景
    # ------------------------------------------------------------------

    @staticmethod
    def to_json(envelope: ResponseEnvelope) -> dict[str, Any]:
        """将 Envelope 转为完整 JSON（供 REST API 使用）"""
        return {
            "answer": envelope.answer_text,
            "citations": [c.to_dict() for c in envelope.citations],
            "links": [l.to_dict() for l in envelope.links],
            "proactive_actions": [
                {
                    "type": a.action_type.value,
                    "priority": a.priority.value,
                    "title": a.title,
                    "content": a.content,
                    "action_label": a.action_label,
                    "delay_seconds": a.delay_seconds,
                    "link": a.attached_link.to_dict() if a.attached_link else None,
                }
                for a in envelope.proactive_actions
            ],
            "confidence": envelope.confidence_report.to_dict() if envelope.confidence_report else None,
            "trace": envelope.engine_trace,
        }

    # ------------------------------------------------------------------
    # 私有辅助方法
    # ------------------------------------------------------------------

    def _build_metadata(self, envelope: ResponseEnvelope) -> dict[str, Any]:
        """组装元数据对象"""
        metadata: dict[str, Any] = {}

        # 链接
        if envelope.links:
            metadata["links"] = [link.to_dict() for link in envelope.links]

        # 引用
        if envelope.citations:
            metadata["citations"] = [c.to_dict() for c in envelope.citations]

        # 主动推送
        if envelope.proactive_actions:
            metadata["proactive"] = [
                {
                    "type": a.action_type.value,
                    "priority": a.priority.value,
                    "title": a.title,
                    "content": a.content,
                    "action_label": a.action_label,
                    "delay_seconds": a.delay_seconds,
                    "link": a.attached_link.to_dict() if a.attached_link else None,
                }
                for a in envelope.proactive_actions
            ]

        # 置信度报告（调试模式）
        if envelope.confidence_report:
            metadata["confidence"] = envelope.confidence_report.to_dict()

        return metadata

    @staticmethod
    def _format_action_sse(action: ProactiveAction) -> str:
        """格式化单个推送动作为 SSE 数据"""
        data = {
            "type": "proactive",
            "action_type": action.action_type.value,
            "priority": action.priority.value,
            "title": action.title,
            "content": action.content,
            "action_label": action.action_label,
            "delay_seconds": action.delay_seconds,
            "link": action.attached_link.to_dict() if action.attached_link else None,
        }
        return f"[METADATA]{json.dumps(data, ensure_ascii=False)}"
