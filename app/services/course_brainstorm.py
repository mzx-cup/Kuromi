# -*- coding: utf-8 -*-
"""Phase 2 — 3 轮脑暴对话 + OBG/PBL 判定 + CourseOutline 候选.

职责:
  1. start_brainstorm(requirement, student_id)
     → 启动 1 个 in-memory session, 出第 1 轮 LLM 多选题(slot=goal)
  2. turn_brainstorm(brainstorm_id, user_choice | user_text | skip)
     → 推进 1 轮, 3 轮收齐后 LLM 判定 OBG/PBL + 出 CourseOutline
  3. confirm_brainstorm(brainstorm_id, outline_edit, obg_pbl_override)
     → 锁定大纲, 标记可生成 9 件套

槽位顺序: goal → base → path (case 由 path 那轮同一 prompt 里夹带)
状态存储: 进程内 dict(BRAINSTORM_STORE), 短会话不上 DB.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.llm_json import LLMJsonError, llm_json
from db import get_student_portrait
from prompts import build_prompt
from state import LearningPortrait

logger = logging.getLogger("starlearn.course_brainstorm")

# ============================================================
# 槽位顺序(固定 3 轮)
# ============================================================

SLOT_ORDER: tuple[str, ...] = ("goal", "base", "path")
TOTAL_TURNS: int = 3
# case 不单独占轮, 由 path 那轮同一 prompt 顺带问

# 槽位缺省 fallback(画像读不到时用)
SLOT_FALLBACK = {
    "goal": "(未指定, 假设为技能进阶)",
    "base": "(未指定, 假设为零基础)",
    "path": "(未指定, 假设为系统学习)",
    "case": "",
}


# ============================================================
# 内存 session
# ============================================================

@dataclass
class BrainstormState:
    """单次脑暴会话的进程内状态."""
    brainstorm_id: str
    student_id: str
    requirement: str
    turn: int = 0                                # 已记录答案数(0/1/2/3);3 = 收齐待 confirm
    slots: dict[str, Optional[str]] = field(default_factory=lambda: {
        "goal": None, "base": None, "path": None, "case": None,
    })
    turns_log: list[dict[str, Any]] = field(default_factory=list)
    # 收齐 3 轮后填充
    outline: dict[str, Any] = field(default_factory=dict)
    obg_pbl_mode: str = ""
    obg_pbl_rationale: str = ""
    confirmed: bool = False
    created_at: float = field(default_factory=time.time)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


BRAINSTORM_STORE: dict[str, BrainstormState] = {}
STORE_LOCK = asyncio.Lock()


async def _save(state: BrainstormState) -> None:
    async with STORE_LOCK:
        BRAINSTORM_STORE[state.brainstorm_id] = state


async def _load(brainstorm_id: str) -> BrainstormState:
    async with STORE_LOCK:
        st = BRAINSTORM_STORE.get(brainstorm_id)
    if st is None:
        raise KeyError(f"brainstorm_id={brainstorm_id} 不存在或已过期")
    return st


# ============================================================
# 画像 -> variables
# ============================================================

def _load_portrait(student_id: str) -> dict[str, Any]:
    """从 db 读 6 维画像, 转成 dict(失败给空 dict)."""
    if not student_id:
        return {}
    try:
        portrait_dict = get_student_portrait(int(student_id))
        if isinstance(portrait_dict, dict):
            return portrait_dict
    except Exception as e:
        logger.warning(f"[brainstorm] 读画像失败 student_id={student_id}: {e}")
    return {}


def _portrait_to_learning_portrait(portrait_dict: dict) -> Optional[LearningPortrait]:
    if not portrait_dict:
        return None
    try:
        return LearningPortrait.model_validate(portrait_dict)
    except Exception as e:
        logger.warning(f"[brainstorm] LearningPortrait 解析失败: {e}")
        return None


# ============================================================
# LLM 出题(per-slot)
# ============================================================

async def _ask_one_slot(
    slot: str,
    state: BrainstormState,
    portrait_dict: dict[str, Any],
) -> dict[str, Any]:
    """用 brainstorm_question prompt 出 1 道多选题.

    Returns:
        {slot, question, options[]}
    """
    variables = {
        "requirement": state.requirement,
        "slot": slot,
        "slot_goal": state.slots["goal"] or "(空)",
        "slot_base": state.slots["base"] or "(空)",
        "slot_path": state.slots["path"] or "(空)",
        "slot_case": state.slots["case"] or "(空)",
    }
    raw = await _call_brainstorm_question(variables)
    # 兜底: slot 与参数一致(options 必填)
    if not raw.get("options"):
        raw["options"] = _fallback_options(slot)
    raw.setdefault("slot", slot)
    raw.setdefault("question", _fallback_question(slot))
    return raw


def _fallback_question(slot: str) -> str:
    return {
        "goal": "你学习这个主题, 主要想达成什么目标?",
        "base": "你目前对这块的基础是什么?",
        "path": "你希望的学习路径更偏哪一种?",
    }.get(slot, "请补充")


def _fallback_options(slot: str) -> list[str]:
    return {
        "goal": ["求职面试", "学业考试", "项目实现", "兴趣探索", "技能进阶"],
        "base": ["零基础", "看过书/视频", "写过简单脚本", "做过完整项目"],
        "path": ["系统学习", "速成上手", "案例驱动", "理论先行"],
    }.get(slot, ["选项 A", "选项 B", "选项 C"])


async def _call_brainstorm_question(variables: dict) -> dict[str, Any]:
    """走 llm_json 失败时退化为 _fallback_options(不算硬错)."""
    from pydantic import BaseModel
    class _Q(BaseModel):
        slot: str = ""
        question: str = ""
        options: list[str] = []
    try:
        instance = await llm_json("brainstorm_question", variables, _Q, temperature=0.4)
        d = instance.model_dump()
        if d.get("options"):
            return d
    except LLMJsonError as e:
        logger.warning(f"[brainstorm] question slot={variables.get('slot')} 走 fallback: {e}")
    return {
        "slot": variables.get("slot", ""),
        "question": _fallback_question(variables.get("slot", "")),
        "options": _fallback_options(variables.get("slot", "")),
    }


# ============================================================
# 3 轮收齐 → OBG/PBL 判定 + CourseOutline
# ============================================================

async def _decide_obg_pbl_and_outline(
    state: BrainstormState,
    portrait_dict: dict[str, Any],
) -> dict[str, Any]:
    """收齐 goal/base/path 后, 调 LLM 判定 OBG/PBL + 出 CourseOutline 候选.

    始终返回 dict; LLM 失败走 _fallback_decide.
    """
    variables = {
        "requirement": state.requirement,
        "learning_goals": portrait_dict.get("learning_goal", {}).get("current", "")
        if isinstance(portrait_dict.get("learning_goal"), dict)
        else "",
        "knowledge_base": portrait_dict.get("knowledge_mastery", {}).get("level", "")
        if isinstance(portrait_dict.get("knowledge_mastery"), dict)
        else "",
        "code_skill": portrait_dict.get("code_skill", {}).get("level", "")
        if isinstance(portrait_dict.get("code_skill"), dict)
        else "",
        "slot_goal": state.slots["goal"] or "(未填, 用画像默认)",
        "slot_base": state.slots["base"] or "(未填, 用画像默认)",
        "slot_path": state.slots["path"] or "(未填, 用画像默认)",
        "slot_case": state.slots["case"] or "(未填, 可空)",
    }
    from pydantic import BaseModel, Field
    class _Outline(BaseModel):
        title: str = ""
        description: str = ""
        scenes: list[dict] = Field(default_factory=list)
    class _Decide(BaseModel):
        mode: str = "obg"  # obg / pbl
        rationale: str = ""
        outline: _Outline = Field(default_factory=_Outline)

    try:
        instance = await llm_json("brainstorm_decide_obg_pbl", variables, _Decide, temperature=0.4)
        d = instance.model_dump()
        d.setdefault("mode", "obg")
        d.setdefault("rationale", "未生成")
        if "outline" not in d or not d["outline"]:
            d["outline"] = {"title": state.requirement[:12], "description": "", "scenes": []}
        return d
    except LLMJsonError as e:
        logger.warning(f"[brainstorm] decide_obg_pbl 走 fallback: {e}")
        return _fallback_decide(state)


def _fallback_decide(state: BrainstormState) -> dict[str, Any]:
    """LLM 全挂时的兜底大纲 — 3 个 scene, OBG 模式."""
    title = (state.requirement or "新课程")[:12]
    return {
        "mode": "obg",
        "rationale": "LLM 暂不可用, 默认 OBG + 3 场景兜底",
        "outline": {
            "title": title,
            "description": f"系统学习 {state.requirement}",
            "scenes": [
                {"id": "s1", "title": "入门", "description": f"{state.requirement} 基础概念", "key_points": ["核心概念"], "type": "slide", "duration_min": 10},
                {"id": "s2", "title": "进阶", "description": f"{state.requirement} 深入用法", "key_points": ["实践"], "type": "slide", "duration_min": 12},
                {"id": "s3", "title": "实战", "description": f"{state.requirement} 综合应用", "key_points": ["综合"], "type": "slide", "duration_min": 15},
            ],
        },
    }


# ============================================================
# 公开 API
# ============================================================

async def start_brainstorm(requirement: str, student_id: str = "") -> dict[str, Any]:
    """启动 3 轮脑暴, 返回 brainstorm_id + 第 1 轮 question."""
    bs_id = f"bs_{uuid.uuid4().hex[:16]}"
    state = BrainstormState(
        brainstorm_id=bs_id,
        student_id=student_id,
        requirement=requirement,
    )
    portrait_dict = _load_portrait(student_id)

    # 第 1 轮 — 出题但 state.turn=0(尚未收到答案)
    q = await _ask_one_slot("goal", state, portrait_dict)
    state.turns_log.append({
        "turn": 1,
        "slot": "goal",
        "question": q["question"],
        "options": q["options"],
    })
    await _save(state)

    return {
        "brainstorm_id": bs_id,
        "turn": 1,
        "total_turns": TOTAL_TURNS,
        "slot": "goal",
        "question": q["question"],
        "options": q["options"],
        "allow_custom": True,
        "allow_skip": True,
    }


async def turn_brainstorm(
    brainstorm_id: str,
    user_choice: Optional[str] = None,
    user_text: Optional[str] = None,
    skip: bool = False,
) -> dict[str, Any]:
    """推进 1 轮; 3 轮收齐后返回 OBG/PBL + CourseOutline.

    Returns:
        {brainstorm_id, turn, total_turns, done, slot, question, options, ...}
        done=False: 等待下一题
        done=True:  返回 obg_pbl_mode, obg_pbl_rationale, outline
    """
    state = await _load(brainstorm_id)
    portrait_dict = _load_portrait(state.student_id)

    async with state.lock:
        # state.turn = 已记录答案数(0 / 1 / 2)
        # 本轮要记录的槽位 = SLOT_ORDER[state.turn]
        if state.turn >= TOTAL_TURNS:
            raise ValueError(f"brainstorm_id={brainstorm_id} 已收齐 3 轮, 请走 confirm_brainstorm")
        current_slot = SLOT_ORDER[state.turn]

        # 记录本轮答案
        if skip:
            answer = None
        elif user_text and user_text.strip():
            answer = user_text.strip()
        elif user_choice:
            answer = user_choice
        else:
            answer = None

        state.slots[current_slot] = answer
        # 顺手把 path 那轮的 case 槽(若用户填了文本)记上(同一 prompt 顺带问)
        if current_slot == "path" and isinstance(answer, str) and "案例" in state.turns_log[-1]["question"]:
            state.slots["case"] = answer
            state.slots["path"] = None
        state.turns_log[-1]["answer"] = answer
        state.turn += 1  # 已记录 +1

        if state.turn < TOTAL_TURNS:
            # 出下一题
            next_slot = SLOT_ORDER[state.turn]
            q = await _ask_one_slot(next_slot, state, portrait_dict)
            state.turns_log.append({
                "turn": state.turn + 1,
                "slot": next_slot,
                "question": q["question"],
                "options": q["options"],
            })
            await _save(state)
            return {
                "brainstorm_id": state.brainstorm_id,
                "turn": state.turn + 1,
                "total_turns": TOTAL_TURNS,
                "done": False,
                "slot": next_slot,
                "question": q["question"],
                "options": q["options"],
            }

        # 3 轮收齐, 判定 + 出大纲
        try:
            decision = await _decide_obg_pbl_and_outline(state, portrait_dict)
        except Exception as e:
            logger.warning(f"[brainstorm] decide 未捕获异常, 走 fallback: {e}")
            decision = _fallback_decide(state)
        state.outline = decision.get("outline", {})
        state.obg_pbl_mode = decision.get("mode", "obg")
        state.obg_pbl_rationale = decision.get("rationale", "")
        await _save(state)

        return {
            "brainstorm_id": state.brainstorm_id,
            "turn": TOTAL_TURNS,
            "total_turns": TOTAL_TURNS,
            "done": True,
            "obg_pbl_mode": state.obg_pbl_mode,
            "obg_pbl_rationale": state.obg_pbl_rationale,
            "outline": state.outline,
        }


async def confirm_brainstorm(
    brainstorm_id: str,
    outline_edit: dict[str, Any] | None = None,
    obg_pbl_override: str = "",
) -> dict[str, Any]:
    """锁定大纲; 用户可编辑场景 / 强制覆盖 OBG/PBL."""
    state = await _load(brainstorm_id)
    async with state.lock:
        if not state.outline:
            raise ValueError(f"brainstorm_id={brainstorm_id} 尚未完成 3 轮, 不可 confirm")

        # 应用 outline_edit
        if outline_edit:
            for k, v in outline_edit.items():
                if k in state.outline:
                    if isinstance(state.outline[k], dict) and isinstance(v, dict):
                        state.outline[k].update(v)
                    elif isinstance(state.outline[k], list) and isinstance(v, list):
                        state.outline[k] = v
                    else:
                        state.outline[k] = v

        mode = obg_pbl_override or state.obg_pbl_mode
        if mode not in ("obg", "pbl"):
            mode = state.obg_pbl_mode or "obg"
        state.obg_pbl_mode = mode
        state.confirmed = True
        await _save(state)

        # 构造 outline_summary 给 9 件套 prompt
        scenes = state.outline.get("scenes", []) or []
        outline_summary = {
            "title": state.outline.get("title", ""),
            "description": state.outline.get("description", ""),
            "total_scenes": len(scenes),
            "scene_titles": [s.get("title", "") for s in scenes if isinstance(s, dict)],
            "estimated_min": sum(s.get("duration_min", 0) for s in scenes if isinstance(s, dict)),
        }
        return {
            "brainstorm_id": state.brainstorm_id,
            "locked": True,
            "obg_pbl_mode": mode,
            "outline": state.outline,
            "outline_summary": outline_summary,
        }


# ============================================================
# 给 course_bundle 用的 helper
# ============================================================

async def get_brainstorm_for_bundle(brainstorm_id: str) -> tuple[dict, dict, Optional[LearningPortrait]]:
    """给 course_bundle 喂数据: 返回 (outline, slots, LearningPortrait)."""
    state = await _load(brainstorm_id)
    portrait_dict = _load_portrait(state.student_id)
    return state.outline, state.slots, _portrait_to_learning_portrait(portrait_dict)
