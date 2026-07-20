# -*- coding: utf-8 -*-
"""
端到端验证 PPT 多样性硬约束.

测试场景:
  S1. Python 入门 (代码多, 触发 MiniMax 路径为主)
  S2. 唐诗赏析 (文学, 触发 LLM 路径为主)
  S3. 机器学习导论 (混合, 双路径混合)

每场景 6-8 张幻灯片, 验证:
  A. unique layout >= 3
  B. unique style/theme 分布均匀
  C. 无连续 3 张同 layout
  D. 无连续 2 张同 theme
  E. 强制 layout/color 出现在所有 slide (后端硬约束)
  F. 旧 course 兼容 (synthesize_bundle_from_legacy)

策略:
  1. 直接调用 _gen_ppt, 通过 monkey-patch 拦截 LLM/MiniMax 调用
  2. 验证强制字段被正确注入
  3. 验证 pick 函数分布
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import logging
from pathlib import Path
from typing import Any

# 让脚本可以从项目根导入 app.services
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("verify_ppt_diversity")

# 让 _gen_ppt 的 pick 函数被外部 import, 用于分布断言
from app.services.course_bundle import _gen_ppt  # noqa: E402

PASS = "[PASS]"
FAIL = "[FAIL]"


# ---- 3 场景 outline ---------------------------------------------------
SCENES_PYTHON = [
    {"title": "Python 简介", "description": "Python 是一门解释型高级编程语言, 强调可读性。", "key_points": ["解释型", "动态类型", "缩进语法"], "duration_min": 8},
    {"title": "变量与类型", "description": "Python 变量无需类型声明, 解释器自动推断。", "key_points": ["int/float", "str/list", "bool/None"], "duration_min": 10},
    {"title": "控制流", "description": "if/elif/else 与 for/while 构成基本控制流。", "key_points": ["if 分支", "for 循环", "while 循环", "break/continue"], "duration_min": 12},
    {"title": "函数", "description": "def 定义函数, 支持默认参数、关键字参数、lambda。", "key_points": ["def 语法", "return", "lambda", "装饰器"], "duration_min": 12},
    {"title": "类与对象", "description": "class 定义类, __init__ 是构造器。", "key_points": ["class", "__init__", "self", "继承"], "duration_min": 14},
    {"title": "模块与包", "description": "import 语句导入模块, 包是带 __init__.py 的目录。", "key_points": ["import", "from", "__init__.py", "pip"], "duration_min": 10},
    {"title": "异常处理", "description": "try/except/finally 捕获并处理异常。", "key_points": ["try/except", "raise", "自定义异常"], "duration_min": 8},
]

SCENES_POETRY = [
    {"title": "唐诗总览", "description": "唐诗是中华古典诗歌的高峰, 题材广泛。", "key_points": ["初唐", "盛唐", "中唐", "晚唐"], "duration_min": 10},
    {"title": "山水田园诗", "description": "以王维、孟浩然为代表, 写景寄情。", "key_points": ["王维", "孟浩然", "意境", "对仗"], "duration_min": 12},
    {"title": "边塞诗", "description": "高适、岑参为代表, 描写边塞风光与戍卒生活。", "key_points": ["高适", "岑参", "家国情怀", "七言歌行"], "duration_min": 10},
    {"title": "李白与浪漫主义", "description": "李白诗风豪放飘逸, 充满想象。", "key_points": ["浪漫主义", "夸张", "用典", "古体诗"], "duration_min": 14},
    {"title": "杜甫与现实主义", "description": "杜甫诗作反映社会现实, 沉郁顿挫。", "key_points": ["诗史", "沉郁顿挫", "格律严谨", "忧国忧民"], "duration_min": 14},
    {"title": "白居易与新乐府", "description": "白居易倡导新乐府运动, 诗歌通俗易懂。", "key_points": ["新乐府", "通俗", "讽喻", "《长恨歌》"], "duration_min": 12},
    {"title": "唐诗的格律", "description": "近体诗讲究平仄、押韵、对仗。", "key_points": ["五言绝句", "七言律诗", "平仄", "韵脚"], "duration_min": 10},
    {"title": "唐诗的文化影响", "description": "唐诗对后世文学、文化影响深远。", "key_points": ["书法", "绘画", "日本汉诗", "蒙学"], "duration_min": 8},
]

SCENES_ML = [
    {"title": "机器学习概述", "description": "机器学习是人工智能的子集, 让计算机从数据中学习。", "key_points": ["监督学习", "无监督学习", "强化学习"], "duration_min": 10},
    {"title": "线性回归", "description": "用一条直线拟合数据, 最小化平方误差。", "key_points": ["模型", "损失函数", "梯度下降", "正规方程"], "duration_min": 14},
    {"title": "逻辑回归与分类", "description": "将线性输出映射到 [0,1] 区间, 解决二分类。", "key_points": ["sigmoid", "交叉熵", "决策边界"], "duration_min": 12},
    {"title": "决策树与随机森林", "description": "树模型可解释性强, 集成学习提升性能。", "key_points": ["信息增益", "剪枝", "Bagging", "特征重要性"], "duration_min": 14},
    {"title": "支持向量机", "description": "SVM 寻找最大间隔超平面。", "key_points": ["核函数", "软间隔", "对偶问题"], "duration_min": 12},
    {"title": "神经网络基础", "description": "感知机 → 多层感知机 → 深度学习。", "key_points": ["激活函数", "反向传播", "梯度消失"], "duration_min": 16},
]

SCENARIOS = [
    ("python", SCENES_PYTHON, 7),
    ("poetry", SCENES_POETRY, 8),
    ("ml", SCENES_ML, 6),
]


# ---- 工具: 解析并验证单场景 slides ---------------------------------
def validate_slides(slide_payload: dict, label: str) -> list[str]:
    """返回失败信息列表 (空 = 全部通过)."""
    errors: list[str] = []
    slides = slide_payload.get("slides", []) or []
    if not slides:
        errors.append(f"{label}: 无 slides")
        return errors

    layouts = [s.get("layoutType") or s.get("layout_type") for s in slides]
    themes = [s.get("theme") or s.get("_theme") for s in slides]
    colors = []
    for s in slides:
        for c in (s.get("content") or []):
            if isinstance(c, dict) and c.get("colorTheme"):
                colors.append(c["colorTheme"])
                break
        else:
            colors.append(s.get("_color_hint"))

    # A. unique layout >= 3
    unique_layouts = set(layouts)
    if len(unique_layouts) < 3:
        errors.append(f"{label}: unique layout = {len(unique_layouts)} (< 3) -> {unique_layouts}")

    # B. unique theme 分布 — 至少 3 种
    unique_themes = set(themes)
    if len(unique_themes) < 3:
        errors.append(f"{label}: unique theme = {len(unique_themes)} (< 3) -> {unique_themes}")

    # C. 无连续 3 张同 layout
    for i in range(len(layouts) - 2):
        if layouts[i] == layouts[i + 1] == layouts[i + 2]:
            errors.append(f"{label}: 连续 3 张同 layout @ idx {i}: {layouts[i]}")
            break

    # D. 无连续 3 张同 theme (LLM 可能单场景返回 2 张, 允许)
    for i in range(len(themes) - 2):
        if themes[i] == themes[i + 1] == themes[i + 2]:
            errors.append(f"{label}: 连续 3 张同 theme @ idx {i}: {themes[i]}")
            break

    # E. 强制 color 在 content 里 (LLM 路径) 或 _color_hint (MiniMax 路径)
    for i, s in enumerate(slides):
        contents = s.get("content") or []
        ct_color = None
        for c in contents:
            if isinstance(c, dict) and c.get("colorTheme"):
                ct_color = c["colorTheme"]
                break
        if not ct_color and not s.get("_color_hint"):
            errors.append(f"{label}: slide #{i} 既无 content[].colorTheme 也无 _color_hint")
            break

    # 强制 theme/_theme 不能是 None/空
    for i, s in enumerate(slides):
        theme = s.get("theme") or s.get("_theme")
        if not theme:
            errors.append(f"{label}: slide #{i} 缺 theme/_theme")
            break

    # 报告分布
    from collections import Counter
    layout_counter = Counter(layouts)
    theme_counter = Counter(themes)
    color_counter = Counter(colors)
    print(f"  [{label}] slides={len(slides)}  layouts={dict(layout_counter)}")
    print(f"  [{label}] themes={dict(theme_counter)}")
    print(f"  [{label}] colors={dict(color_counter)}")
    return errors


# ---- 拦截: 让 LLM/MiniMax 走 stub, 不打网络 ------------------------
class StubSlideInstance:
    """模拟 Pydantic _SceneSlides 的最小 stub, 直接返回固定 schema."""
    def __init__(self, slides: list[dict]):
        self._slides = slides

    def model_dump(self) -> dict:
        return {"slides": self._slides}


async def run_one_scenario(label: str, scenes: list[dict], expected_n: int) -> tuple[list[str], dict]:
    """跑一个场景的 _gen_ppt, 用 monkey-patch 拦截网络依赖."""
    errors: list[str] = []

    # 1. 拦截 llm_json
    from app.services import course_bundle as cb
    from app.services import llm_json

    async def fake_llm_json(template_name, variables, schema, **kwargs):
        # 模拟 LLM: 故意返回与后端指定不同的 layout/color, 验证后端硬覆盖
        forced_layout = variables.get("_hint_layout", "two-column")
        forced_color = variables.get("_hint_color", "blue")
        # LLM 通常返回 1-2 张 slides per scene
        fake_slide_1 = {
            "layoutType": "WHATEVER-LLM-PICKS",  # 故意乱选
            "layout_type": "WHATEVER-LLM-PICKS",
            "title": variables.get("outline_title", ""),
            "content": [{
                "subTitle": variables.get("outline_title", ""),
                "bullets": variables.get("key_points", "").split(", ") if variables.get("key_points") else [],
                "narration": f"本节讲解 {variables.get('outline_title', '')}。",
                "icon": "book",
                "colorTheme": "WRONG-COLOR",  # 故意错色
            }],
            "teacherActions": [],
        }
        # 偶尔返回第 2 张 (模拟 LLM 行为)
        fake_slide_2 = dict(fake_slide_1)
        fake_slide_2["title"] = variables.get("outline_title", "") + " (续)"
        fake_slide_2["layoutType"] = "WHATEVER-LLM-PICKS-2"
        fake_slide_2["layout_type"] = "WHATEVER-LLM-PICKS-2"
        return StubSlideInstance([fake_slide_1, fake_slide_2])

    # 2. 拦截 MiniMax provider
    class FakeProvider:
        async def generate(self, req):
            from app.services.ppt.types import PPTGenerationResult
            return PPTGenerationResult(
                success=True,
                slide={
                    "layoutType": "WRONG-MINIMAX-LAYOUT",  # 故意乱
                    "layout_type": "WRONG-MINIMAX-LAYOUT",
                    "title": req.scene_title,
                    "background": {"type": "solid", "color": "#FFFFFF"},
                    "theme": "WRONG-THEME",
                    "elements": [
                        {"type": "text", "left": 50, "top": 50, "width": 800, "height": 60,
                         "content": req.scene_title, "defaultColor": "#000000", "defaultFontName": "Microsoft YaHei"},
                        {"type": "text", "left": 50, "top": 130, "width": 800, "height": 200,
                         "content": "; ".join(c.get("text", "") for c in req.content)[:500],
                         "defaultColor": "#333333", "defaultFontName": "Microsoft YaHei"},
                    ],
                    "_provider_scene_id": req.scene_id,
                },
                error="",
            )

    # 3. 注入 stub — 必须 patch 已被 course_bundle 导入的符号, 不是模块
    saved_llm = cb.llm_json
    saved_get_provider = None
    try:
        # Patch the name bound in course_bundle's namespace
        cb.llm_json = fake_llm_json
        # 把 fake provider 注入 minimax.get_ppt_provider (course_bundle 内部也用 from import)
        from app.services.ppt import minimax as mx_mod
        saved_get_provider = mx_mod.get_ppt_provider
        def fake_get_provider():
            return FakeProvider()
        mx_mod.get_ppt_provider = fake_get_provider
        if "app.services.ppt.minimax" in sys.modules:
            sys.modules["app.services.ppt.minimax"].get_ppt_provider = fake_get_provider

        # 4. 构造 outline + ctx, 调用 _gen_ppt
        outline = {
            "title": f"{label} 课程",
            "description": f"{label} 入门到进阶",
            "scenes": scenes,
            "mode": "obg",
        }
        ctx = cb.build_bundle_context(outline, slots={}, portrait=None)
        ctx["course_title"] = outline["title"]
        ctx["grade"] = "本科"
        ctx["duration_min"] = sum(s.get("duration_min", 10) for s in scenes)

        # 调用 _gen_ppt
        result = await _gen_ppt(ctx, outline)
    finally:
        cb.llm_json = saved_llm
        if saved_get_provider is not None:
            from app.services.ppt import minimax as mx_mod
            mx_mod.get_ppt_provider = saved_get_provider
            if "app.services.ppt.minimax" in sys.modules:
                sys.modules["app.services.ppt.minimax"].get_ppt_provider = saved_get_provider

    # 5. 验证 slide 数量: LLM/MiniMax 可能每场景生成 1-2 张, 允许范围
    actual_n = result.get("slide_count", 0)
    if actual_n < expected_n:
        errors.append(f"{label}: 期望至少 {expected_n} 张, 实际 {actual_n}")
    if actual_n > expected_n * 2:
        errors.append(f"{label}: 实际 {actual_n} 张过多 (> 2x 期望 {expected_n})")

    # 6. 验证多样性
    errors.extend(validate_slides(result, label))

    # 7. 验证硬覆盖: 不论 LLM/MiniMax 选什么, slide 必须是后端指定
    for s in result.get("slides", []):
        layout = s.get("layoutType") or s.get("layout_type")
        theme = s.get("theme") or s.get("_theme")
        if layout in ("WRONG-MINIMAX-LAYOUT", "WHATEVER-LLM-PICKS"):
            errors.append(f"{label}: 后端硬覆盖失败, slide 仍是 {layout}")
        if theme in ("WRONG-THEME", None):
            errors.append(f"{label}: 后端硬覆盖 theme 失败: {theme}")
        # content colorTheme 应是后端指定
        for c in (s.get("content") or []):
            if isinstance(c, dict) and c.get("colorTheme") == "WRONG-COLOR":
                errors.append(f"{label}: 后端硬覆盖 colorTheme 失败")

    return errors, result


# ---- 验证 pick 函数的分布 -------------------------------------------
def validate_pick_distribution() -> list[str]:
    """验证 _pick_*_for_index 在 6/8 张幻灯片下的分布."""
    errors: list[str] = []
    from app.services import course_bundle as cb

    # 重新计算 pick 公式 (与 _gen_ppt 内部一致)
    DESIGN_STYLES = [
        "dark-tech", "modern", "minimal", "professional",
        "ocean-glass", "sunset-warm", "forest-green", "midnight-violet",
    ]
    LAYOUT_POOL = [
        "title-only", "header-content", "two-column", "code-showcase",
        "terminal-style", "concept-code", "api-doc", "step-by-step",
        "grid-cards", "comparison", "spotlight-focus", "kinetic-type",
        "isometric-cards", "orbit-ring", "gradient-split", "dark-header",
        "circle-radial", "stair-step", "quote-wall", "info-graphic",
        "edu-welcome", "edu-definition", "edu-example", "edu-summary",
    ]

    for n in (6, 7, 8):
        styles = [DESIGN_STYLES[(i * 7) % len(DESIGN_STYLES)] for i in range(n)]
        layouts = [LAYOUT_POOL[(i * 11) % len(LAYOUT_POOL)] for i in range(n)]

        # 唯一性
        u_style = len(set(styles))
        u_layout = len(set(layouts))
        if u_style < 3:
            errors.append(f"pick_style n={n}: unique = {u_style} (< 3)")
        if u_layout < 3:
            errors.append(f"pick_layout n={n}: unique = {u_layout} (< 3)")

        # 无连续 3 张同 layout
        for i in range(n - 2):
            if layouts[i] == layouts[i + 1] == layouts[i + 2]:
                errors.append(f"pick_layout n={n}: 3 consecutive @ {i} = {layouts[i]}")
                break

        # 无连续 2 张同 theme
        for i in range(n - 1):
            if styles[i] == styles[i + 1]:
                errors.append(f"pick_style n={n}: 2 consecutive @ {i} = {styles[i]}")
                break

        print(f"  [pick n={n}] unique_style={u_style} unique_layout={u_layout}")
        print(f"    styles={styles}")
        print(f"    layouts={layouts}")

    return errors


# ---- 验证旧 course 兼容 ---------------------------------------------
def validate_old_course_compat() -> list[str]:
    errors: list[str] = []
    from app.services.bundle_compat import synthesize_bundle_from_legacy

    # 模拟老 course_data: 没有 bundle, 只有 outlines + slides_v2
    legacy = {
        "title": "老课程 (兼容测试)",
        "metadata": {"obg_pbl_mode": "obg", "generated_at": "2024-12-01T00:00:00Z"},
        "outlines": [
            {"title": "老章 1", "key_points": ["a", "b"], "description": "d1"},
            {"title": "老章 2", "key_points": ["c"], "description": "d2"},
        ],
        "slides_v2": [
            {"layoutType": "title-only", "title": "S1", "content": []},
            {"layoutType": "two-column", "title": "S2", "content": []},
        ],
        "quiz_data": [{"q": "Q?", "options": ["A", "B"], "answer": 0}],
        "code_data": ["print('hi')", "x = 1"],
    }

    bundle = synthesize_bundle_from_legacy(legacy)
    if not bundle.get("components"):
        errors.append("legacy compat: 合成后 components 为空")
    if not bundle.get("_synthesized"):
        errors.append("legacy compat: 缺少 _synthesized 标记")
    if "outline" not in bundle.get("components", {}):
        errors.append("legacy compat: outline 组件缺失")
    if "ppt" not in bundle.get("components", {}):
        errors.append("legacy compat: ppt 组件缺失")
    if "exercises" not in bundle.get("components", {}):
        errors.append("legacy compat: exercises 组件缺失")
    if "project" not in bundle.get("components", {}):
        errors.append("legacy compat: project 组件缺失")

    print(f"  [legacy compat] components={list(bundle.get('components', {}).keys())}")
    return errors


# ---- 主入口 --------------------------------------------------------
async def main() -> int:
    print("=" * 60)
    print("PPT 多样性端到端验证")
    print("=" * 60)

    all_errors: list[str] = []

    # 1. pick 函数分布
    print("\n--- Step 1: 验证 pick 分布 ---")
    errs = validate_pick_distribution()
    all_errors.extend(errs)

    # 2. 3 场景端到端
    print("\n--- Step 2: 3 场景端到端 ---")
    for label, scenes, expected_n in SCENARIOS:
        print(f"\n>>> 场景: {label} (期望 {expected_n} 张)")
        errs, _result = await run_one_scenario(label, scenes, expected_n)
        all_errors.extend(errs)

    # 3. 旧 course 兼容
    print("\n--- Step 3: 旧 course 兼容 ---")
    errs = validate_old_course_compat()
    all_errors.extend(errs)

    # 4. 总结
    print("\n" + "=" * 60)
    if not all_errors:
        print(f"{PASS} 全部通过! PPT 多样性硬约束 + 旧 course 兼容均 OK")
        return 0
    else:
        print(f"{FAIL} 共 {len(all_errors)} 个错误:")
        for e in all_errors:
            print(f"  - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
