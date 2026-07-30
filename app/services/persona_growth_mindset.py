# -*- coding: utf-8 -*-
"""
Growth Mindset 反馈框架注入器

基于 Carol Dweck 的成长型思维理论。
在所有面向学生的 AI 反馈场景中，自动注入反馈规则。

使用示例:
    from app.services.persona_growth_mindset import inject_growth_mindset

    system_prompt = "你是星识的 AI 导师。"
    system_prompt = inject_growth_mindset(system_prompt)
    # 现在 system_prompt 自动带上成长型思维反馈规则
"""

from __future__ import annotations

from pathlib import Path

_SNIPPET_PATH = (
    Path(__file__).resolve().parents[2] / "prompts" / "snippets" / "growth-mindset-feedback.md"
)

# 内嵌的精简版（不依赖文件 IO，方便 import 时立即可用）
_INJECT_RULES = """## 反馈风格（强制 · 成长型思维）

你必须遵循 Dweck 成长型思维（Growth Mindset）框架给反馈：
- 夸努力和策略，不夸天赋和聪明
- 失败归因到可控因素（方法/努力/前置知识），不归因到能力
- 用"还没 + 条件"的句式，不用"不能/不会"
- 主动求助要鼓励，不嘲笑
- 创新解法要展开讨论，不压制

**禁止**："你好聪明" / "你不擅长这块" / "这么简单都不会" / "你就是粗心"
**推荐**："你刚才的思路很清晰" / "这块还没完全串起来，我们补一下前置" / "你这次试了好几种方法，这种坚持很棒"
"""

# 场景化的额外规则
_SCENE_EXTRA = {
    "grading": """
（评分场景额外约束）
- 给分时附上"具体可改进的下一步建议"，避免只给一个冷冰冰的数字
- 低分也要肯定过程（"虽然这道题错了，但你前面的分析步骤是对的"）
- 高分要说明"哪一步特别关键"，让好经验可复用
""",
    "socratic": """
（苏格拉底追问场景额外约束）
- 学生答不出时，**绝对不要**说"你怎么没想到" / "这都不会"
- 改为："我们把这一步拆小一点再试试？" / "哪个前置概念你还记得吗？"
- 学生答对时，引导他复述思路（"你能用自己的话讲一遍刚才是怎么想到的吗？"）
""",
    "evaluation": """
（学习评估场景额外约束）
- 评估报告避免用"差/弱"等负面标签，改用"待提升点"
- 给出至少 1 个具体可执行的"下一步建议"
- 强调"通过 X 努力可以 Y 进步"，让评估成为行动起点而非评判
""",
    "feedback_default": "",
}


def inject_growth_mindset(
    system_prompt: str,
    scene: str = "feedback_default",
    *,
    include_full_reference: bool = False,
) -> str:
    """
    把成长型思维反馈规则注入到 system prompt。

    Args:
        system_prompt: 原始 system prompt
        scene: 反馈场景，可选 "grading" / "socratic" / "evaluation" / "feedback_default"
        include_full_reference: 是否在末尾追加完整的 markdown 参考文档（默认 False，只注入精简规则）

    Returns:
        注入了成长型思维规则的 system prompt
    """
    extra = _SCENE_EXTRA.get(scene, _SCENE_EXTRA["feedback_default"])
    injected = f"{system_prompt}\n\n{_INJECT_RULES}{extra}"

    if include_full_reference:
        try:
            full_doc = _SNIPPET_PATH.read_text(encoding="utf-8")
            injected += f"\n\n---\n## 完整参考（成长型思维框架）\n\n{full_doc}\n"
        except OSError:
            # 文件读取失败不影响主流程
            pass

    return injected


def has_growth_mindset_marker(system_prompt: str) -> bool:
    """
    检查 system prompt 是否已经注入了成长型思维规则（用于去重）。
    """
    return "成长型思维" in system_prompt or "Growth Mindset" in system_prompt
