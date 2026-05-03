"""
角色自动选择器

根据学生 6 维画像自动选择最适合的教学风格。
"""


def auto_select_persona(profile: dict | None = None) -> str:
    """
    根据学生画像自动选择教学风格。

    选择逻辑：
    1. 手动偏好优先 (preferred_persona)
    2. 初学者 (beginner) -> patient_tutor
    3. 苏格拉底通关率高 (>70%) -> socratic_questioner
    4. 视觉型学习者 -> energetic_lecturer
    5. 默认 -> expert_mentor
    """
    if not profile:
        return "expert_mentor"

    # 手动偏好优先
    preferred = profile.get("preferred_persona")
    if preferred and preferred in ("patient_tutor", "socratic_questioner", "energetic_lecturer", "expert_mentor"):
        return preferred

    level = profile.get("cognitive_level", "")
    style = profile.get("learning_style", "")
    socratic_rate = profile.get("socratic_pass_rate", 0.0)

    if level == "beginner" or level == "basic":
        return "patient_tutor"

    if isinstance(socratic_rate, (int, float)) and socratic_rate > 0.7:
        return "socratic_questioner"

    if style in ("visual", "visual-kinesthetic"):
        return "energetic_lecturer"

    return "expert_mentor"


PERSONA_NAMES = {
    "patient_tutor": "患者导师",
    "socratic_questioner": "苏格拉底提问者",
    "energetic_lecturer": "充满活力的讲师",
    "expert_mentor": "专家导师",
}
