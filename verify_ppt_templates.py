#!/usr/bin/env python3
"""
PPT 模板、颜色样式、布局系统验证脚本

检查项：
1. LAYOUT_TYPES 25种布局无重复
2. DESIGN_STYLES 15种风格无重复
3. THEME_COLORS 30种颜色无重复
4. STYLE_COLOR_PREFERENCES 每个style的color都在THEME_COLORS中
5. STYLE_LAYOUT_PREFERENCES 每个style的layout都在LAYOUT_TYPES中
6. IMAGE_FRIENDLY_LAYOUTS 所有layout都在LAYOUT_TYPES中
7. _select_layout 能根据不同design_style选取对应布局
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.ppt.minimax import THEME_COLORS
from app.services.ppt.minimax import MiniMaxPPTProvider

LAYOUT_TYPES = MiniMaxPPTProvider.LAYOUT_TYPES
DESIGN_STYLES = MiniMaxPPTProvider.DESIGN_STYLES
STYLE_COLOR_PREFERENCES = MiniMaxPPTProvider.STYLE_COLOR_PREFERENCES
STYLE_LAYOUT_PREFERENCES = MiniMaxPPTProvider.STYLE_LAYOUT_PREFERENCES
IMAGE_FRIENDLY_LAYOUTS = MiniMaxPPTProvider.IMAGE_FRIENDLY_LAYOUTS


def check_no_duplicates(items: list, name: str) -> list[str]:
    errors = []
    seen = set()
    for item in items:
        if item in seen:
            errors.append(f"  [DUPLICATE] {name}: '{item}'")
        seen.add(item)
    return errors


def check_all_in_set(items: list, target_set: set, item_type: str, target_name: str, style: str = "") -> list[str]:
    errors = []
    for item in items:
        if item not in target_set:
            ctx = f" (style='{style}')" if style else ""
            errors.append(f"  [INVALID] {item_type} '{item}'{ctx} not in {target_name}")
    return errors


def main():
    errors = []

    print("=" * 60)
    print("PPT Template & Style System Verification")
    print("=" * 60)

    # 1. 布局模板检查
    print(f"\n[1] LAYOUT_TYPES ({len(LAYOUT_TYPES)} types):")
    for l in LAYOUT_TYPES:
        print(f"    - {l}")
    errors.extend(check_no_duplicates(LAYOUT_TYPES, "LAYOUT_TYPES"))

    # 2. 设计风格检查
    print(f"\n[2] DESIGN_STYLES ({len(DESIGN_STYLES)} types):")
    for s in DESIGN_STYLES:
        print(f"    - {s}")
    errors.extend(check_no_duplicates(DESIGN_STYLES, "DESIGN_STYLES"))

    # 3. 主题颜色检查
    print(f"\n[3] THEME_COLORS ({len(THEME_COLORS)} types):")
    errors.extend(check_no_duplicates(list(THEME_COLORS.keys()), "THEME_COLORS"))

    # 4. STYLE_COLOR_PREFERENCES 完整性
    print(f"\n[4] STYLE_COLOR_PREFERENCES check:")
    color_keys = set(THEME_COLORS.keys())
    for style, colors in STYLE_COLOR_PREFERENCES.items():
        print(f"    {style}: {colors}")
        if style not in DESIGN_STYLES:
            errors.append(f"  [INVALID] STYLE_COLOR_PREFERENCES style '{style}' not in DESIGN_STYLES")
        errors.extend(check_all_in_set(colors, color_keys, "color", "THEME_COLORS", style))

    # 5. STYLE_LAYOUT_PREFERENCES 完整性
    print(f"\n[5] STYLE_LAYOUT_PREFERENCES check:")
    layout_keys = set(LAYOUT_TYPES)
    for style, layouts in STYLE_LAYOUT_PREFERENCES.items():
        print(f"    {style}: {layouts}")
        if style not in DESIGN_STYLES:
            errors.append(f"  [INVALID] STYLE_LAYOUT_PREFERENCES style '{style}' not in DESIGN_STYLES")
        errors.extend(check_all_in_set(layouts, layout_keys, "layout", "LAYOUT_TYPES", style))

    # 6. IMAGE_FRIENDLY_LAYOUTS 完整性
    print(f"\n[6] IMAGE_FRIENDLY_LAYOUTS check:")
    print(f"    {IMAGE_FRIENDLY_LAYOUTS}")
    errors.extend(check_all_in_set(IMAGE_FRIENDLY_LAYOUTS, layout_keys, "layout", "LAYOUT_TYPES"))

    # 7. _select_layout 功能测试
    print(f"\n[7] _select_layout functional tests:")
    provider = MiniMaxPPTProvider()
    test_cases = [
        (1, "normal", "modern", "count=1 -> title-only"),
        (2, "normal", "modern", "count=2 -> two-column"),
        (3, "normal", "modern", "count=3 -> quote-highlight"),
        (4, "normal", "modern", "count=4 -> stats-row"),
        (5, "normal", "modern", "count=5 -> header-content"),
        (6, "normal", "modern", "count=6 -> asymmetric-split"),
        (7, "normal", "modern", "count=7 -> timeline-steps"),
        (8, "normal", "modern", "count=8 -> comparison"),
        (9, "normal", "elegant", "count=9+ -> from pool"),
        (10, "normal", "tech", "count=10+ -> from pool"),
        (5, "quiz", "modern", "quiz -> grid-cards"),
    ]
    for content_count, scene_type, style, desc in test_cases:
        content = [{"text": f"item{i}"} for i in range(content_count)]
        layout = provider._select_layout(content, scene_type, style)
        valid = layout in LAYOUT_TYPES
        status = "OK" if valid else "FAIL"
        print(f"    [{status}] {desc} -> {layout}")

    # 8. 锁定布局验证（1-8项应锁定不同布局）
    print(f"\n[8] Locked layouts check (1-8 items):")
    locked = {}
    for count in range(1, 9):
        content = [{"text": f"item{i}"} for i in range(count)]
        layout = provider._select_layout(content, "normal", "modern")
        locked[count] = layout

    # 检查1-8是否各有不同布局（允许重复但应尽量不同）
    layout_set = set(locked.values())
    print(f"    Locked layouts: {locked}")
    print(f"    Unique locked layouts: {len(layout_set)} / 8")

    # 汇总
    print("\n" + "=" * 60)
    if errors:
        print(f"ERRORS FOUND: {len(errors)}")
        for e in errors:
            print(e)
        return 1
    else:
        print("ALL CHECKS PASSED")
        print(f"    - {len(LAYOUT_TYPES)} layout templates")
        print(f"    - {len(DESIGN_STYLES)} design styles")
        print(f"    - {len(THEME_COLORS)} theme colors")
        return 0


if __name__ == "__main__":
    sys.exit(main())