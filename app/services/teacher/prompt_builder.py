"""
System Prompt 组装器

对应 OpenMAIC lib/orchestration/prompt-builder.ts 的 buildStructuredPrompt()
将角色设定、碎片化规则、UI动作描述、学生画像、场景状态组装为完整 System Prompt。
"""

from app.services.teacher.personas import PERSONA_SYSTEM_PROMPTS
from app.services.teacher.action_schemas import get_ui_action_descriptions

# ---- 碎片化交织规则 ----

INTERLEAVING_RULES = """
# 输出粒度规则 (CRITICAL - 违反将导致教学效果严重下降)

## 核心原则：交织而非堆叠
你的每一次输出都必须将 speech 和 visual action 细粒度地交织在一起。
每个 speech 对象最多 1-2 句话（中文不超过 30 字，英文不超过 20 词）。
每讲完一个知识点立即跟一个对应的视觉动作，然后再讲下一句。

## 粒度约束
- speech 对象的 content 字段长度硬限制：中文 ≤ 30 字符，英文 ≤ 20 词
- 单个 speech 只表达一个概念单元。如果需要解释多个概念，拆分为多个 speech
- 视觉动作（spotlight/laser/wb_draw_*）必须紧跟其描述的 speech，不得滞后
- 严禁连续输出 2 个及以上的 speech 对象而不穿插任何视觉动作

## 输出结构模板
你的输出应遵循此模式：
1. speech (引入主题，1-2 句) → action (打开白板/聚焦元素)
2. speech (讲解第一个要点) → action (绘制/指向)
3. speech (讲解第二个要点) → action (绘制/指向)
4. ...重复...
5. speech (总结/提问，1-2 句)

## 禁止的输出模式
- 禁止: [speech(长段落), speech(长段落), ..., action]  - 连续说话不动作
- 禁止: [speech(50字以上)]                              - 单个 speech 太长
- 禁止: [action, action, action, ..., speech]           - 连续动作不说话
- 禁止: [speech("我先讲...然后再...接着我们...最后...")]    - 试图"预告"后续内容
"""

# ---- Few-Shot 示例 ----

INTERLEAVING_EXAMPLES = """
# Few-Shot 示例

## Good Example (碎片化交织) ✓
[
  {"type":"speech","content":"集合有三个特性：确定性、互异性、无序性。"},
  {"type":"spotlight","params":{"elementId":"set_properties"}},
  {"type":"speech","content":"确定性就是每个元素要么在集合里，要么不在。"},
  {"type":"wb_draw_text","params":{"content":"确定性: ∀x, x∈A 或 x∉A","x":100,"y":100,"fontSize":20}},
  {"type":"speech","content":"互异性是说集合里的元素不能重复。"},
  {"type":"wb_draw_text","params":{"content":"互异性: {1,1,2} = {1,2}","x":100,"y":160,"fontSize":20}},
  {"type":"speech","content":"无序性--顺序不重要。"},
  {"type":"wb_draw_text","params":{"content":"无序性: {1,2,3} = {3,1,2}","x":100,"y":220,"fontSize":20}},
  {"type":"speech","content":"这三个性质，你记住了吗？"}
]

## Bad Example (粗粒度堆叠) ✗
[
  {"type":"speech","content":"集合有三个重要性质：第一是确定性，就是每个元素要么在集合里要么不在集合里。第二是互异性，就是集合里的元素不能重复出现。第三是无序性，就是元素排列顺序不重要。"},
  {"type":"wb_draw_text","params":{"content":"确定性: ... 互异性: ... 无序性: ...","x":100,"y":100,"fontSize":18}}
]
"""

# ---- JSON 输出格式说明 ----

OUTPUT_FORMAT_RULES = """
# 输出格式
你 MUST 输出一个 JSON 数组。每个元素是一个对象，包含 type 字段：

## 格式规则
1. 输出单个 JSON 数组 -- 不要有解释、不要用代码块包裹
2. `type:"speech"` 对象包含 `content` (教师旁白文本，中文≤30字)
3. `type:"action"` 对象包含 `name` 和 `params`
4. speech 和 action 对象可以自由交织排列
5. 每个响应必须是一个完整、独立的 JSON 数组
6. 不要说"我来..."、"现在我要..." -- 直接做，不要预告
"""


def build_teacher_system_prompt(
    persona: str = "expert_mentor",
    student_profile: dict | None = None,
    state_context: dict | None = None,
    allowed_ui_actions: list[str] | None = None,
    discussion_context: dict | None = None,
) -> str:
    """
    组装 AI 教师完整的 System Prompt。

    对应 OpenMAIC lib/orchestration/prompt-builder.ts 的 buildStructuredPrompt()
    """
    if allowed_ui_actions is None:
        allowed_ui_actions = ["spotlight", "laser", "wb_open", "wb_draw_svg",
                              "wb_draw_text", "wb_draw_shape", "wb_draw_latex",
                              "wb_draw_chart", "wb_draw_table", "wb_draw_line",
                              "wb_draw_code", "wb_close", "speech", "text"]

    # 1. 角色设定
    persona_prompt = PERSONA_SYSTEM_PROMPTS.get(persona, PERSONA_SYSTEM_PROMPTS["expert_mentor"])

    # 2. 输出格式
    output_format = OUTPUT_FORMAT_RULES

    # 3. 碎片化规则
    interleaving = INTERLEAVING_RULES

    # 4. Few-Shot 示例
    examples = INTERLEAVING_EXAMPLES

    # 5. UI 动作描述
    ui_actions_desc = get_ui_action_descriptions(allowed_ui_actions)

    # 6. 学生画像
    student_section = _build_student_section(student_profile)

    # 7. 场景状态
    state_section = _build_state_section(state_context)

    # 8. 讨论上下文
    discussion_section = _build_discussion_section(discussion_context)

    # 组装
    parts = [
        persona_prompt,
        output_format,
        interleaving,
        examples,
        "# 可用 UI 动作\n" + ui_actions_desc,
        student_section,
        state_section,
        discussion_section,
        "\n请使用中文进行教学。所有 speech 的 content 必须是中文。",
        "记住: 边说边画，边说边指。像真人教师一样自然。",
    ]

    return "\n\n".join(p for p in parts if p.strip())


def _build_student_section(profile: dict | None) -> str:
    if not profile:
        return ""
    lines = ["## 学生信息"]
    if profile.get("cognitive_level"):
        lines.append(f"- 基础水平: {profile['cognitive_level']}")
    if profile.get("learning_style"):
        lines.append(f"- 学习风格: {profile['learning_style']}")
    if profile.get("learning_goals"):
        lines.append(f"- 学习目标: {profile['learning_goals']}")
    if profile.get("latest_weaknesses"):
        lines.append(f"- 当前短板: {profile['latest_weaknesses']}")
    return "\n".join(lines) if len(lines) > 1 else ""


def _build_state_section(state: dict | None) -> str:
    if not state:
        return ""
    lines = ["## 当前场景", f"- 场景类型: {state.get('scene_type', 'slide')}"]
    if state.get("slide_elements"):
        lines.append(f"- 幻灯片元素: {state['slide_elements']}")
    if state.get("whiteboard_elements"):
        lines.append(f"- 白板已有元素: {state['whiteboard_elements']}")
    return "\n".join(lines)


def _build_discussion_section(ctx: dict | None) -> str:
    if not ctx:
        return ""
    return f"## 讨论上下文\n当前讨论主题: {ctx.get('topic', '')}"
