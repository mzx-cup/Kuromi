"""
inference_rules.py — 语义推断规则 (用于 P0 修复)

将 CSS 变量名映射到合理的色值，供 fix_p0_tech_debt.py 使用。

推断策略 (优先级从高到低):
  1. 拆 var 名为 token，匹配 COLOR_NAMES
  2. avatar-gradient-{role} 模式匹配 ROLE_COLORS
  3. 都不匹配 → FALLBACK_COLOR + 注释 "TODO: refine color"
"""

# 颜色名 → 十六进制
COLOR_NAMES = {
    "amber": "#f59e0b", "rose": "#f43f5e", "violet": "#8b5cf6",
    "purple": "#8b5cf6", "teal": "#14b8a6", "blue": "#3b82f6",
    "green": "#10b981", "orange": "#f97316", "red": "#ef4444",
    "yellow": "#eab308", "pink": "#ec4899", "cyan": "#06b6d4",
    "indigo": "#6366f1", "lime": "#84cc16", "fuchsia": "#d946ef",
    "sky": "#0ea5e9", "glow": "#fef3c7", "hover": "#fde68a",
    "strong": "#1e40af", "index": "#3b82f6",
}

# 角色 → 颜色 (用于 avatar-gradient-* 模式)
ROLE_COLORS = {
    "agent": "#8b5cf6", "moderator": "#f59e0b",
    "student": "#3b82f6", "teacher": "#10b981",
    "user": "#3b82f6", "system": "#6b7280",
}

# fallback
FALLBACK_COLOR = "#9ca3af"


def infer_value(var_name: str) -> tuple[str, str]:
    """根据变量名推断色值

    Returns:
        (value, source_tag), source_tag ∈ {'mapped', 'role', 'fallback'}
    """
    # 策略 1: 拆 token 匹配 COLOR_NAMES
    for token in var_name.split("-"):
        if token in COLOR_NAMES:
            return COLOR_NAMES[token], "mapped"

    # 策略 2: avatar-gradient-{role} 模式
    if var_name.startswith("avatar-gradient-"):
        role = var_name.replace("avatar-gradient-", "", 1)
        if role in ROLE_COLORS:
            return ROLE_COLORS[role], "role"

    # 策略 3: fallback
    return FALLBACK_COLOR, "fallback"
