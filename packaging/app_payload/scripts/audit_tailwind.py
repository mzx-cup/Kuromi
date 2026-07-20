#!/usr/bin/env python3
"""
audit_tailwind.py — 统计 HTML 中 Tailwind 工具类的使用范围

输出使用频次最高的 N 个 utility class，用于决定切换到本地 tailwind.css
是否会丢失 utility class。
"""
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
HTML_DIR = ROOT / "html"

# 常见 Tailwind utility 模式（截取主要类别，避免正则爆炸）
PATTERNS = [
    r"\bflex\b", r"\bgrid\b", r"\bblock\b", r"\binline\b", r"\bhidden\b",
    r"\bp-[0-9]\b", r"\bpx-[0-9]\b", r"\bpy-[0-9]\b",
    r"\bm-[0-9]\b", r"\bmx-[0-9]\b", r"\bmy-[0-9]\b",
    r"\bmt-[0-9]\b", r"\bmb-[0-9]\b", r"\bml-[0-9]\b", r"\bmr-[0-9]\b",
    r"\bw-[0-9]+\b", r"\bh-[0-9]+\b", r"\bmin-h-screen\b", r"\bmax-w-",
    r"\btext-(xs|sm|base|lg|xl|2xl|3xl)\b",
    r"\bfont-(normal|medium|semibold|bold)\b",
    r"\bbg-(white|black|gray-|red-|blue-|green-|purple-|pink-|brand-)\b",
    r"\btext-(white|black|gray-|red-|blue-|green-|purple-|pink-|brand-)\b",
    r"\bborder\b", r"\brounded(-[a-z0-9]+)?\b",
    r"\bitems-(start|end|center|stretch)\b",
    r"\bjustify-(start|end|center|between|around)\b",
    r"\bgap-[0-9]+\b",
]


def main() -> int:
    if not HTML_DIR.exists():
        print(f"ERROR: {HTML_DIR} 不存在", file=sys.stderr)
        return 1

    # Windows 兼容：确保 stdout 能输出 emoji
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    counter = Counter()
    file_count = 0
    html_files = sorted(HTML_DIR.glob("*.html"))
    for html_path in html_files:
        text = html_path.read_text(encoding="utf-8")
        for pat in PATTERNS:
            for m in re.finditer(pat, text):
                counter[m.group(0)] += 1
        file_count += 1

    print(f"扫描文件数: {file_count}")
    print(f"匹配 utility class 总数: {sum(counter.values())}")
    print(f"独立 utility class 数: {len(counter)}")
    print()
    print("Top 30 使用频次:")
    for cls, count in counter.most_common(30):
        print(f"  {count:5d}  {cls}")
    print()
    if len(counter) < 30:
        print("✅ 使用范围较小，可考虑切本地编译")
    else:
        print("⚠️  使用范围较大，保留 CDN 或确认本地 tailwind.css 已覆盖这些类")
    return 0


if __name__ == "__main__":
    sys.exit(main())
