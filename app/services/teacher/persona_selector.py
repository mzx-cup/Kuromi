# -*- coding: utf-8 -*-
"""角色自动选择器 — 包含领域感知（academic vs counseling）"""


def auto_select_persona(profile: dict | None = None) -> str:
    if not profile:
        return "expert_mentor"

    preferred = profile.get("preferred_persona")
    if preferred and preferred in (
        "patient_tutor", "socratic_questioner",
        "energetic_lecturer", "expert_mentor", "caring_counselor",
    ):
        return preferred

    if profile.get("emotion_state") in ("anxious", "frustrated"):
        return "caring_counselor"

    level = profile.get("cognitive_level", "")
    socratic_rate = profile.get("socratic_pass_rate", 0.0)
    style = profile.get("learning_style", "")

    if level in ("beginner", "basic"):
        return "patient_tutor"
    if isinstance(socratic_rate, (int, float)) and socratic_rate > 0.7:
        return "socratic_questioner"
    if style in ("visual", "visual-kinesthetic"):
        return "energetic_lecturer"
    return "expert_mentor"


PERSONA_NAMES = {
    "patient_tutor": "陈默",
    "socratic_questioner": "林问",
    "energetic_lecturer": "周燃",
    "expert_mentor": "严铮",
    "caring_counselor": "苏语",
}