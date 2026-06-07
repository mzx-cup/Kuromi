#!/usr/bin/env python3
"""
verify_css_vars.py — L1 静态检查

提取所有 CSS 中引用的 var(--xxx)，对比 tokens.css 中已定义的 --xxx，
输出未定义的引用。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CSS_DIR = ROOT / "css"
TOKENS_FILE = CSS_DIR / "tokens.css"


def extract_used_vars() -> set[str]:
    used = set()
    pattern = re.compile(r"var\(\s*--([a-zA-Z0-9_-]+)")
    for css_path in CSS_DIR.glob("*.css"):
        if css_path.name == "tokens.css":
            continue
        for match in pattern.finditer(css_path.read_text(encoding="utf-8")):
            used.add(match.group(1))
    return used


def extract_defined_vars() -> set[str]:
    defined = set()
    pattern = re.compile(r"^\s*--([a-zA-Z0-9_-]+)\s*:", re.MULTILINE)
    if not TOKENS_FILE.exists():
        return defined
    for match in pattern.finditer(TOKENS_FILE.read_text(encoding="utf-8")):
        defined.add(match.group(1))
    return defined


def main() -> int:
    # Windows 兼容
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    used = extract_used_vars()
    defined = extract_defined_vars()
    undefined = sorted(used - defined)
    print(f"引用变量总数: {len(used)}")
    print(f"已定义变量数: {len(defined)}")
    if not undefined:
        print("✅ 所有引用的 CSS 变量都在 tokens.css 中已定义")
        return 0
    print(f"\n❌ 以下 {len(undefined)} 个变量被引用但未在 tokens.css 中定义:")
    for v in undefined:
        print(f"  --{v}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
