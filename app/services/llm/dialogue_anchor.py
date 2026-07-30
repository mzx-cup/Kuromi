# -*- coding: utf-8 -*-
"""
DialogueAnchor — 对话锚点机制

解决多轮苏格拉底对话"越聊越散"的问题。
每轮对话自动提取并维护两个状态：
  - 已确认共识 (consensus): 学生和老师都同意的知识点 / 结论
  - 待解决问题 (open_questions): 还没解决的疑问 / 矛盾点

使用场景:
  - 苏格拉底对话: 注入到 system prompt，防止 LLM 失忆
  - 复盘总结: 把 anchors 序列化成学习档案
  - 学习画像: open_questions 长期未关闭会触发"知识盲区"提醒

设计原则:
  - 无状态核心 + 可插拔持久化 (默认 in-memory，生产可换 Redis/DB)
  - 按 (user_id, session_id) 隔离
  - 提取采用规则 + 启发式，不强依赖 LLM (避免循环调用)
"""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class Anchor:
    """单个锚点"""
    text: str                                  # 锚点内容
    kind: str                                  # "consensus" | "open_question"
    turn: int                                  # 第几轮提出
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None        # open_question 关闭时填

    def to_dict(self) -> dict:
        return asdict(self)

    def is_open(self) -> bool:
        return self.kind == "open_question" and self.resolved_at is None


# 触发"已确认共识"的关键词（中文 + 英文）
_CONSENSUS_TRIGGERS = re.compile(
    r"(?:^|\s|，|。|；)"                              # 行首或标点
    r"(?:"
    r"我(?:明白了|懂了|理解了|知道了|想通了|get 了)"        # 我明白了
    r"|原来(?:是|如此|这样)"                              # 原来是
    r"|对(?:了|的|吧|呢|！|!)"                            # 对了
    r"|是的|没错|确实|好的"                              # 肯定回应
    r"|I (?:see|understand|got it)"                    # 英文
    r"|(?:so|oh),? (?:it'?s|that'?s|now I)"            # 英文承接
    r")",
    re.IGNORECASE,
)

# 触发"待解决问题"的关键词
_OPEN_TRIGGERS = re.compile(
    r"(?:"
    r"(?:我)?(?:还)?(?:不|没)(?:明白|懂|清楚|理解|知道)"  # 还没明白
    r"|(?:有|还有)(?:什么|哪些|啥)(?:疑问|问题|不懂)"        # 还有什么疑问
    r"|(?:为)?什么.{0,12}\?$"                              # 问号结尾的为什么
    r"|怎么.{0,8}\?$"                                       # 怎么XXX？
    r"|(?:I |still )?(?:don'?t|do not) (?:know|understand|get)"  # 英文
    r")",
    re.IGNORECASE,
)


class DialogueAnchorStore:
    """
    对话锚点存储

    按 (user_id, session_id) 维护一个锚点列表。
    线程安全。
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # _store[(user_id, session_id)] = [Anchor, ...]
        self._store: dict[tuple[str, str], list[Anchor]] = {}

    def _key(self, user_id: str, session_id: str) -> tuple[str, str]:
        return (user_id, session_id)

    def add_consensus(
        self, user_id: str, session_id: str, text: str, turn: int
    ) -> Anchor:
        """新增一个已确认共识"""
        return self._add(user_id, session_id, text, "consensus", turn)

    def add_open_question(
        self, user_id: str, session_id: str, text: str, turn: int
    ) -> Anchor:
        """新增一个待解决问题"""
        return self._add(user_id, session_id, text, "open_question", turn)

    def _add(
        self, user_id: str, session_id: str, text: str, kind: str, turn: int
    ) -> Anchor:
        anchor = Anchor(text=text.strip(), kind=kind, turn=turn)
        with self._lock:
            self._store.setdefault(self._key(user_id, session_id), []).append(anchor)
        return anchor

    def resolve_open_question(
        self, user_id: str, session_id: str, anchor: Anchor
    ) -> None:
        """关闭一个 open_question（移入 consensus）"""
        with self._lock:
            anchor.resolved_at = time.time()
            anchor.kind = "consensus"
            key = self._key(user_id, session_id)
            if anchor in self._store.get(key, []):
                # 已经是共识，无需额外操作
                return

    def get_active(
        self, user_id: str, session_id: str, max_items: int = 20
    ) -> list[Anchor]:
        """获取当前会话的所有未解决锚点（consensus + open）"""
        with self._lock:
            items = list(self._store.get(self._key(user_id, session_id), []))
        return items[-max_items:]

    def get_open_questions(
        self, user_id: str, session_id: str
    ) -> list[Anchor]:
        """获取当前会话所有未关闭的待解决问题"""
        with self._lock:
            return [
                a for a in self._store.get(self._key(user_id, session_id), [])
                if a.is_open()
            ]

    def snapshot(self, user_id: str, session_id: str) -> dict[str, Any]:
        """导出当前会话锚点快照（用于序列化 / 持久化）"""
        with self._lock:
            items = self._store.get(self._key(user_id, session_id), [])
            return {
                "user_id": user_id,
                "session_id": session_id,
                "consensus": [a.to_dict() for a in items if a.kind == "consensus"],
                "open_questions": [a.to_dict() for a in items if a.is_open()],
                "total": len(items),
            }

    def clear(self, user_id: str, session_id: str) -> None:
        """清空一个会话的锚点（会话结束时调用）"""
        with self._lock:
            self._store.pop(self._key(user_id, session_id), None)


# 进程内单例（生产可替换为 Redis-backed 实现）
_default_store: Optional[DialogueAnchorStore] = None
_store_lock = threading.Lock()


def get_anchor_store() -> DialogueAnchorStore:
    """获取默认的锚点存储（单例）"""
    global _default_store
    with _store_lock:
        if _default_store is None:
            _default_store = DialogueAnchorStore()
        return _default_store


# ============================================================
# 启发式提取（不依赖 LLM 调用）
# ============================================================

def extract_from_student_reply(
    reply: str, turn: int
) -> tuple[list[str], list[str]]:
    """
    从学生回答里启发式提取共识和待解决问题。

    Returns:
        (consensus_list, open_questions_list)
    """
    consensus: list[str] = []
    open_questions: list[str] = []

    # 按句子切分
    sentences = re.split(r"(?<=[。！？!?\n])", reply)
    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent) > 200:
            continue
        if _CONSENSUS_TRIGGERS.search(sent):
            consensus.append(sent)
        elif _OPEN_TRIGGERS.search(sent):
            open_questions.append(sent)

    return consensus, open_questions


def render_for_prompt(snapshot: dict[str, Any], max_chars: int = 600) -> str:
    """
    把锚点快照渲染成可注入 prompt 的字符串。

    Args:
        snapshot: DialogueAnchorStore.snapshot() 的输出
        max_chars: 最大字符数（防止 prompt 膨胀）

    Returns:
        格式化的锚点状态文本
    """
    if not snapshot.get("total"):
        return ""

    parts: list[str] = ["## 对话锚点（防止失忆）\n"]
    consensus = snapshot.get("consensus", [])
    open_qs = snapshot.get("open_questions", [])

    if consensus:
        parts.append("### 已确认共识（不要再追问这些）")
        for a in consensus[-5:]:  # 最多展示最近 5 条
            text = a["text"]
            if len(text) > 80:
                text = text[:77] + "..."
            parts.append(f"- {text}")
        parts.append("")

    if open_qs:
        parts.append("### 待解决问题（继续聚焦这些）")
        for a in open_qs[-5:]:  # 最多展示最近 5 条
            text = a["text"]
            if len(text) > 80:
                text = text[:77] + "..."
            parts.append(f"- {text}")
        parts.append("")

    rendered = "\n".join(parts)
    if len(rendered) > max_chars:
        rendered = rendered[: max_chars - 3] + "..."
    return rendered
