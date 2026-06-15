# -*- coding: utf-8 -*-
"""Phase 1 4 层管线 — L0 输入安全 / L1 意图路由 / L2 苏格拉底追问 / L3 输出安全。

设计要点:
- 4 个类全部无状态 + 纯函数,便于单测
- L2 onboard 状态通过 metadata["onboard"] 传入,**不**污染 LearningProfile,避免影响 ProfilerAgent
- L0/L3 命中后调 audit_log,失败不抛(审计失败不阻塞业务)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.services import audit_log

MAX_INPUT_LEN = 4000
MAX_OUTPUT_LEN = 8000

# ============================================================
# L0 — 输入安全网关
# ============================================================

_INPUT_RULES: list[tuple[str, str]] = [
    (r"(?i)(ignore\s+previous|忽略之前的指令|忽略以上|disregard\s+above|system\s*prompt\s*leak|告诉我你的提示词)", "PROMPT_INJECTION"),
    (r"\b\d{17}[\dXx]\b", "PII_ID"),
    (r"(?<!\d)1[3-9]\d{9}(?!\d)", "PII_PHONE"),
    (r"(rm\s+-rf|del\s+/[sf]|drop\s+table|format\s+c:)", "DESTRUCTIVE"),
]

_HINTS: dict[str, str] = {
    "PROMPT_INJECTION": "检测到越权指令,已拦截。请换个学习相关的问题吧~",
    "PII_ID": "为了你的隐私,身份证号不会被发送。换个问法吧~",
    "PII_PHONE": "为了你的隐私,手机号不会被发送。换个问法吧~",
    "DESTRUCTIVE": "破坏性指令已拦截。这里是学习场景哦~",
    "INPUT_TOO_LONG": f"输入过长(>{MAX_INPUT_LEN} 字符),请精简后重试。",
}


class InputGateway:
    """L0 输入安全网关。命中规则返回 (False, code)。"""

    @staticmethod
    def check(user_input: str, student_id: str) -> tuple[bool, str]:
        if not user_input:
            return False, "EMPTY"
        if len(user_input) > MAX_INPUT_LEN:
            audit_log.audit_input_block(student_id, "INPUT_TOO_LONG", user_input[:200])
            return False, "INPUT_TOO_LONG"
        for pat, code in _INPUT_RULES:
            if re.search(pat, user_input):
                audit_log.audit_input_block(student_id, code, user_input[:200])
                return False, code
        return True, ""

    @staticmethod
    def hint(code: str) -> str:
        return _HINTS.get(code, "输入未通过安全检查,请换个问法。")

    @staticmethod
    def all_codes() -> list[str]:
        return list(_HINTS.keys())


# ============================================================
# L1 — 意图路由器
# ============================================================

_COURSE_KW = [
    "生成课程", "生成一门", "生成一个", "出一门课", "出一门", "帮我做课",
    "课程大纲", "帮我设计", "设计一门", "设计一个", "学习路径", "学习计划",
    "教我", "我想学", "我要学",
    "create a course", "build a course", "design a course",
    "learning path", "study plan", "course outline",
    "teach me", "i want to learn", "i'd like to learn",
]
_NAV_KW = [
    "去课程页", "去个人中心", "跳到代码", "跳到个人", "打开个人中心",
    "进入心流", "去看看", "导航到", "切换到", "打开",
    "go to", "navigate to", "open ", "openmaic", "switch to",
]


class IntentRouter:
    """L1 意图路由 — 关键词规则,Phase 2 升级 LLM。"""

    @staticmethod
    def route(user_input: str) -> str:
        s = (user_input or "").lower().strip()
        if not s:
            return "socratic_qa"
        if any(kw in s for kw in _COURSE_KW):
            return "course_generate"
        if any(kw in s for kw in _NAV_KW):
            return "navigate"
        return "socratic_qa"

    @staticmethod
    def is_terminal(intent: str) -> bool:
        """Phase 1: 所有意图都仍走苏格拉底,本期不真跳转/不真触发课程生成。"""
        return False


# ============================================================
# L2 — 苏格拉底引擎 (主动追问)
# ============================================================

GAP_HINTS: dict[str, str] = {
    "gap_goal":  "你这次学习的目标是? 求职 / 项目 / 考试 / 兴趣?",
    "gap_level": "你目前的编程基础如何? 零基础 / 写过脚本 / 做过项目?",
    "gap_style": "你更偏好哪种讲解? 例子驱动 / 原理先行 / 图文并茂?",
}
DIFFICULTY_CHECK_HINT = "这个难度对你合适吗? 需要更简单或更深入?"
ONBOARD_REDIRECT_HINT = "在我们开始之前,先花 30 秒认识一下你吧~"


class SocraticEngine:
    """L2 苏格拉底引擎 — 画像缺口检测 + 主动追问事件生成。"""

    @staticmethod
    def collect_questions(onboard: dict[str, Any], profile: dict[str, Any]) -> list[dict[str, str]]:
        """返回追问事件列表(可能为空)。事件格式: {kind, message, deeplink?}"""
        out: list[dict[str, str]] = []

        # 1) 首访未完成 → 引导
        if not onboard.get("completed_at"):
            out.append({
                "kind": "onboard_redirect",
                "message": ONBOARD_REDIRECT_HINT,
                "deeplink": "#onboard-overlay",
            })
            return out

        # 2) 画像缺口检测
        goals = profile.get("learning_goals") or []
        pref = profile.get("learning_preference") or {}
        if not goals or goals == ["应对考试"]:
            out.append({
                "kind": "gap_goal",
                "message": GAP_HINTS["gap_goal"],
                "deeplink": "#onboard-overlay",
            })

        if not pref.get("base"):
            out.append({
                "kind": "gap_level",
                "message": GAP_HINTS["gap_level"],
                "deeplink": "#onboard-overlay",
            })

        if not pref.get("style"):
            out.append({
                "kind": "gap_style",
                "message": GAP_HINTS["gap_style"],
                "deeplink": "#onboard-overlay",
            })

        # 3) 周期性难度确认
        ic = int(profile.get("interaction_count") or 0)
        if ic > 0 and ic % 5 == 0 and len(out) == 0:
            out.append({
                "kind": "difficulty_check",
                "message": DIFFICULTY_CHECK_HINT,
            })

        return out

    @staticmethod
    async def emit_pre_questions(state, push_fn) -> None:
        """main.py 调用的入口。从 state 抽取 onboard + profile 摘要,推送 proactive_question 事件。"""
        metadata = getattr(state, "metadata", None) or {}
        onboard = metadata.get("onboard") or {}

        profile_obj = getattr(state, "profile", None)
        profile_summary: dict[str, Any] = {}
        if profile_obj is not None:
            try:
                profile_summary = {
                    "learning_goals": list(getattr(profile_obj, "learning_goals", []) or []),
                    "learning_preference": dict(getattr(profile_obj, "learning_preference", {}) or {}),
                    "interaction_count": int(getattr(profile_obj, "interaction_count", 0) or 0),
                    "cognitive_level": str(getattr(profile_obj, "cognitive_level", "basic")),
                }
            except Exception:
                profile_summary = {}

        for q in SocraticEngine.collect_questions(onboard, profile_summary):
            await push_fn("proactive_question", q)


# ============================================================
# L3 — 输出安全网关
# ============================================================

_OUTPUT_RULES: list[tuple[str, str]] = [
    (r"\b\d{17}[\dXx]\b", "PII_ID"),
    (r"(?<!\d)1[3-9]\d{9}(?!\d)", "PII_PHONE"),
]


@dataclass
class FilteredOutput:
    answer_text: str
    replaced_codes: list[str] = field(default_factory=list)
    truncated: bool = False


class OutputGateway:
    """L3 输出安全网关 — 长度截断 + PII 替换。"""

    @staticmethod
    def filter(answer_text: str, student_id: str = "") -> FilteredOutput:
        if not answer_text:
            return FilteredOutput(answer_text="")

        replaced: list[str] = []
        out = answer_text

        for pat, code in _OUTPUT_RULES:
            new_out, n = re.subn(pat, "***", out)
            if n > 0:
                replaced.append(code)
                out = new_out

        truncated = False
        if len(out) > MAX_OUTPUT_LEN:
            out = out[:MAX_OUTPUT_LEN] + "\n\n(内容过长,已截断)"
            replaced.append("TRUNCATED")
            truncated = True

        if replaced and student_id:
            audit_log.audit_output_replace(student_id, "+".join(replaced), count=1)

        return FilteredOutput(answer_text=out, replaced_codes=replaced, truncated=truncated)
