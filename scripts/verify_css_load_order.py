#!/usr/bin/env python3
"""
verify_css_load_order.py — L1 静态检查

遍历 html/ 下所有 HTML，验证 <link rel="stylesheet"> 的加载顺序
符合 spec 第 2.2 节的约定。

Expected load order:
  1. tokens.css
  2. tailwind.css
  3. app-base.css
  4. app-bg.css
  5. components.css
  6. components-*.css
  7. animations.css
  8. <页面专属 CSS>
  9. (按需) theme.css scheme-*.css

退出码: 0 = 全部通过; 1 = 至少一个文件违反顺序
"""
import re
import sys
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).parent.parent
HTML_DIR = ROOT / "html"

# 标准加载顺序：层名 -> 该层允许的 CSS 文件名（按出现顺序）
LOAD_ORDER = [
    ("tokens",     ["tokens.css"]),
    ("tailwind",   ["tailwind.css"]),
    ("app-base",   ["app-base.css"]),
    ("app-bg",     ["app-bg.css"]),
    ("components", ["components.css"]),  # 后续 components-* 不要求严格顺序
    ("animations", ["animations.css"]),
]

# 每一层之前不能出现的层（用于检测"倒着"的情况）
LAYER_RANK = {name: i for i, (name, _) in enumerate(LOAD_ORDER)}


class StyleSheetExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "link":
            attrs_dict = dict(attrs)
            if attrs_dict.get("rel") == "stylesheet":
                href = attrs_dict.get("href", "")
                self.links.append(href)


def classify(href: str) -> str | None:
    """根据 href 判断属于哪一层；返回 None 表示页面专属或非关键 CSS"""
    filename = Path(href).name
    if "cdn.tailwindcss" in href or "tailwind" in filename:
        return "tailwind"
    for name, files in LOAD_ORDER:
        if filename in files:
            return name
    if filename.startswith("components-"):
        return "components"  # components-* 视作同层
    return None  # 页面专属或 theme / scheme，不参与顺序检查


def check_file(html_path: Path) -> list[str]:
    errors = []
    parser = StyleSheetExtractor()
    parser.feed(html_path.read_text(encoding="utf-8"))

    seen_rank = -1
    for href in parser.links:
        if href.startswith("http"):
            continue  # CDN 不参与本地顺序
        layer = classify(href)
        if layer is None:
            continue
        rank = LAYER_RANK[layer]
        if rank < seen_rank:
            errors.append(
                f"  - {href} 出现顺序错误：当前层 '{layer}' (rank={rank}) "
                f"在已出现层 rank={seen_rank} 之后"
            )
        seen_rank = max(seen_rank, rank)
    return errors


def main() -> int:
    if not HTML_DIR.exists():
        print(f"ERROR: {HTML_DIR} 不存在", file=sys.stderr)
        return 1

    html_files = sorted(HTML_DIR.glob("*.html"))
    total_errors = 0
    for html_path in html_files:
        errors = check_file(html_path)
        if errors:
            print(f"\n❌ {html_path.relative_to(ROOT)}")
            for e in errors:
                print(e)
            total_errors += len(errors)

    print(f"\n{'='*60}")
    print(f"检查文件数: {len(html_files)}")
    print(f"错误总数:   {total_errors}")
    if total_errors == 0:
        print("✅ 所有 HTML 加载顺序符合约定")
        return 0
    print("❌ 存在加载顺序问题")
    return 1


if __name__ == "__main__":
    sys.exit(main())
