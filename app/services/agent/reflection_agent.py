# -*- coding: utf-8 -*-
"""
ReflectionAgent — 反思日志 Agent(v2.0 P1)

每段学习结束(章节完成 / 课程关闭 / 学习会话终止)时触发,
弹出 3 个元认知问题,引导学生回顾自己的思考过程。
学生回答入库,影响学习画像(反思深度 → 学习策略评分)。

设计:
  - 3 个固定问题 + 学科/上下文相关的变体
  - 回答持久化到 chat_messages / user_learning_profile
  - 提供周报聚合接口
  - 失败不阻断学习主流程

元认知问题模板(v2.0):
  1. "你刚才在哪一步卡住了 / 觉得最难?"
  2. "如果换个条件 / 换种问法,你会怎么做?"
  3. "你今天学到的最关键的一点是什么?"
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("starlearn.reflection")


class ReflectionTrigger(str, Enum):
    """反思触发的时机"""
    CHAPTER_COMPLETE = "chapter_complete"
    COURSE_COMPLETE = "course_complete"
    SESSION_END = "session_end"
    EXAM_FINISH = "exam_finish"
    WEEKLY_DIGEST = "weekly_digest"


# 3 个核心元认知问题(必出)
_CORE_QUESTIONS = [
    "你刚才在哪一步卡住了 / 觉得最难?",
    "如果换个条件 / 换种问法,你会怎么做?",
    "你今天学到的最关键的一点是什么?",
]

# 学科变体(可选 1 个,与核心问题轮替)
_SUBJECT_VARIANTS = {
    "math": [
        "你觉得这个公式 / 定理可以用在哪些其他场景?",
    ],
    "coding": [
        "如果让你用另一种语言 / 库重写这段代码,你会怎么设计?",
    ],
    "language": [
        "你能不能用这个知识点写一个自己的例子?",
    ],
    "science": [
        "这个现象 / 规律在你生活中见过吗?",
    ],
}


@dataclass
class ReflectionPrompt:
    """反思问题集(展示给学生)"""
    trigger: ReflectionTrigger
    questions: list[str]
    context: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "trigger": self.trigger.value,
            "questions": self.questions,
            "context": self.context,
            "created_at": self.created_at,
        }


@dataclass
class ReflectionEntry:
    """学生提交的反思回答"""
    student_id: str
    trigger: ReflectionTrigger
    answers: dict[str, str]    # {question: answer}
    context: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "trigger": self.trigger.value,
            "answers": self.answers,
            "context": self.context,
            "created_at": self.created_at,
        }

    def depth_score(self) -> float:
        """
        简单评估反思深度(0-1):
        - 回答数量:答了 3 道得 1.0
        - 回答长度:平均 > 20 字得满分
        """
        if not self.answers:
            return 0.0
        n = len(self.answers)
        n_score = min(1.0, n / 3.0)
        avg_len = sum(len(a) for a in self.answers.values()) / max(1, n)
        len_score = min(1.0, avg_len / 20.0)
        return round((n_score * 0.5 + len_score * 0.5), 3)


class ReflectionAgent:
    """
    反思日志 Agent。

    使用:
        agent = ReflectionAgent()
        prompt = agent.build_prompt(
            student_id="u123",
            trigger=ReflectionTrigger.CHAPTER_COMPLETE,
            context={"chapter": "递归基础"},
        )
        # 前端展示 prompt.questions,学生答完
        entry = agent.record(
            student_id="u123",
            trigger=ReflectionTrigger.CHAPTER_COMPLETE,
            answers={"Q1": "...", "Q2": "...", "Q3": "..."},
            context={"chapter": "递归基础"},
        )
        print(entry.depth_score())  # 0.0 ~ 1.0
    """

    def __init__(self, llm_call: Optional[Any] = None) -> None:
        """
        Args:
            llm_call: 可选 LLM 调用函数,用于生成学科变体问题。
                       签名: (prompt: str) -> str。
                       传 None 则只用静态题库。
        """
        self.llm_call = llm_call

    def build_prompt(
        self,
        student_id: str,
        trigger: ReflectionTrigger,
        context: Optional[dict[str, Any]] = None,
        subject: Optional[str] = None,
    ) -> ReflectionPrompt:
        """
        构造反思问题集。

        Args:
            student_id: 学生 ID
            trigger: 触发时机
            context: 上下文(章节/课程/会话 ID 等)
            subject: 学科(math/coding/language/science/None)

        Returns:
            ReflectionPrompt
        """
        ctx = dict(context or {})
        questions: list[str] = list(_CORE_QUESTIONS)

        # 学科变体(如果提供)
        if subject and subject in _SUBJECT_VARIANTS:
            extra = _SUBJECT_VARIANTS[subject]
            if extra:
                # 用第 4 个位置插入,前端会展示 4 道题(可选)
                questions.append(extra[0])

        return ReflectionPrompt(
            trigger=trigger,
            questions=questions,
            context={"student_id": student_id, "subject": subject, **ctx},
        )

    def record(
        self,
        student_id: str,
        trigger: ReflectionTrigger,
        answers: dict[str, str],
        context: Optional[dict[str, Any]] = None,
    ) -> ReflectionEntry:
        """
        记录学生提交的反思。

        注意:本函数不直接落库(避免循环依赖),
        实际持久化由调用方负责(写到 chat_messages / user_learning_profile)。
        """
        # 简单清洗
        cleaned_answers = {
            str(q).strip()[:500]: str(a).strip()[:1000]
            for q, a in (answers or {}).items()
        }
        entry = ReflectionEntry(
            student_id=student_id,
            trigger=trigger,
            answers=cleaned_answers,
            context=dict(context or {}),
        )
        try:
            self._persist(entry)
        except Exception as e:  # noqa: BLE001 — 反思落库失败不阻断主流程
            logger.warning("[reflection] 持久化失败: %s (student=%s)", e, student_id)
        return entry

    def _persist(self, entry: ReflectionEntry) -> None:
        """
        持久化反思记录。

        实现:
          1. 优先尝试写入 chat_messages(kind="reflection_log")
          2. 失败则降级到日志(后续异步迁移)
        """
        try:
            # 延迟导入,避免循环依赖
            import db as database
            payload = {
                "kind": "reflection_log",
                "trigger": entry.trigger.value,
                "answers": entry.answers,
                "context": entry.context,
                "depth_score": entry.depth_score(),
            }
            if hasattr(database, "save_reflection_entry"):
                database.save_reflection_entry(
                    user_id=entry.student_id,
                    payload=json.dumps(payload, ensure_ascii=False),
                )
                return
            # 数据库没有这个方法,降级到日志
            logger.info(
                "[reflection] student=%s trigger=%s depth=%.2f",
                entry.student_id, entry.trigger.value, entry.depth_score(),
            )
        except Exception:
            # 失败再降级
            logger.info(
                "[reflection] student=%s trigger=%s answers=%s",
                entry.student_id, entry.trigger.value,
                json.dumps(entry.answers, ensure_ascii=False)[:300],
            )

    def weekly_summary(self, student_id: str, entries: list[ReflectionEntry]) -> dict:
        """
        汇总一周的反思,生成给画像 / 教师的报告。

        Returns:
            {
                "student_id": str,
                "entry_count": int,
                "avg_depth_score": float,
                "common_stuck_points": list[str],  # 卡住/困难相关答案的高频摘录
                "common_learnings": list[str],     # 学到/关键相关答案的高频摘录
            }
        """
        if not entries:
            return {
                "student_id": student_id,
                "entry_count": 0,
                "avg_depth_score": 0.0,
                "common_stuck_points": [],
                "common_learnings": [],
            }

        avg_depth = sum(e.depth_score() for e in entries) / len(entries)
        # 按答案内容分类:含"卡/难/不会"→stuck,含"学到/关键/掌握"→learnings
        stuck_words: list[str] = []
        learnings: list[str] = []
        stuck_kw = ("卡", "难", "不会", "不懂", "不会", "出错")
        learn_kw = ("学到", "关键", "掌握", "明白", "理解", "记住")
        for e in entries:
            for q, a in e.answers.items():
                a_lower = (a or "").lower()
                if any(kw in a or kw in a_lower for kw in stuck_kw):
                    stuck_words.append(a[:30])
                elif any(kw in a or kw in a_lower for kw in learn_kw):
                    learnings.append(a[:30])
        return {
            "student_id": student_id,
            "entry_count": len(entries),
            "avg_depth_score": round(avg_depth, 3),
            "common_stuck_points": stuck_words[:10],
            "common_learnings": learnings[:10],
        }


# 单例
_default_agent: Optional[ReflectionAgent] = None


def get_reflection_agent() -> ReflectionAgent:
    """获取默认反思 Agent(单例)"""
    global _default_agent
    if _default_agent is None:
        _default_agent = ReflectionAgent()
    return _default_agent
