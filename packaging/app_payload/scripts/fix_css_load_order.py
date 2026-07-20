#!/usr/bin/env python3
"""
fix_css_load_order.py — 批量修正 HTML 中 <link rel="stylesheet"> 的加载顺序

按 spec 2.2 节约定，把所有 <link rel="stylesheet"> 重排为：
  tokens.css → tailwind.css → app-base.css → app-bg.css
  → components.css → components-*.css → animations.css
  → 页面专属 CSS → theme.css/scheme-*.css

不修改任何其他内容（script、meta、其他 link、HTML body）。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HTML_DIR = ROOT / "html"

# Windows 兼容：确保 stdout 能输出 emoji
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 顺序由小到大：数值小的排前面
LAYER_RANK = {
    "tokens.css": 1,
    "tailwind.css": 2,
    "app-base.css": 3,
    "app-bg.css": 4,
    "components.css": 5,
}


def layer_rank(filename: str) -> int:
    """返回 CSS 文件应处的层 rank；不在白名单的返回大值（排在后面）"""
    if filename in LAYER_RANK:
        return LAYER_RANK[filename]
    if filename.startswith("components-"):
        return 6
    if filename == "animations.css":
        return 7
    return 999  # 页面专属或 theme/scheme


LINK_PATTERN = re.compile(
    r'(<link\s+rel="stylesheet"\s+href="[^"]+"\s*/?>)',
    re.IGNORECASE,
)


def extract_filename(href: str) -> str:
    """从 href 提取 CSS 文件名（忽略 CDN URL）"""
    if href.startswith("http"):
        return ""
    return href.rsplit("/", 1)[-1]


def fix_file(html_path: Path) -> tuple[int, str]:
    """修正单个 HTML 文件的 link 顺序。返回 (变更行数, 新内容)"""
    text = html_path.read_text(encoding="utf-8")
    matches = list(LINK_PATTERN.finditer(text))
    if len(matches) < 2:
        return 0, text  # 没有或只有一个 link，无需排序

    # 提取所有 <link rel="stylesheet">
    link_tags = [m.group(1) for m in matches]

    # 按 layer_rank 排序；同 rank 内保持原相对顺序（stable sort）
    def sort_key(tag: str) -> int:
        m = re.search(r'href="([^"]+)"', tag)
        href = m.group(1) if m else ""
        fname = extract_filename(href)
        return layer_rank(fname)

    sorted_tags = sorted(link_tags, key=sort_key)

    if sorted_tags == link_tags:
        return 0, text  # 已是有序的

    # 替换：用第一个 match 位置作为锚点，按顺序写入所有 link
    # 策略：找到所有 link 占据的整段连续文本，重写该段
    first_match_start = matches[0].start()
    last_match_end = matches[-1].end()

    # 保留首尾的换行符：取 first match 前最后一个 \n 之后的内容
    prefix_start = text.rfind("\n", 0, first_match_start) + 1
    prefix = text[:prefix_start]
    # 保留 last match 后第一个 \n 之前的内容
    suffix_end_in_text = text.find("\n", last_match_end)
    if suffix_end_in_text == -1:
        suffix_end_in_text = len(text)
    suffix = text[suffix_end_in_text:]

    # 推断原始缩进（取第一个 link 的前导空白）
    first_tag_with_indent = text[first_match_start:matches[0].start()] + matches[0].group(1)
    indent_match = re.match(r"^(\s*)", text[prefix_start:first_match_start])
    indent = indent_match.group(1) if indent_match else "  "

    # 用同样的缩进拼出新的 link 块
    new_block = "\n".join(indent + tag for tag in sorted_tags)

    new_text = prefix + new_block + suffix
    return 1, new_text


def main() -> int:
    if not HTML_DIR.exists():
        print(f"ERROR: {HTML_DIR} 不存在", file=sys.stderr)
        return 1

    html_files = sorted(HTML_DIR.glob("*.html"))
    changed = 0
    for html_path in html_files:
        result, new_text = fix_file(html_path)
        if result:
            html_path.write_text(new_text, encoding="utf-8")
            changed += 1
            print(f"✅ {html_path.relative_to(ROOT)}")

    print(f"\n修改文件数: {changed} / {len(html_files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
