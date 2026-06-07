#!/usr/bin/env python3
"""
audit_global_selectors.py — L1 静态检查

检测页面级 CSS 文件中出现的全局选择器 (body / html / *),
这些应只在 app-base.css 中定义。

退出码: 0 = 仅 app-base.css 含全局选择器; 1 = 其它文件也含
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CSS_DIR = ROOT / "css"
ALLOWED_FILE = "app-base.css"
PATTERN = re.compile(r"^\s*(body|html|\*)\s*\{", re.MULTILINE)


def main() -> int:
    # Windows 兼容
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    offenders = []
    for css_path in sorted(CSS_DIR.glob("*.css")):
        if css_path.name == ALLOWED_FILE:
            continue
        matches = list(PATTERN.finditer(css_path.read_text(encoding="utf-8")))
        if matches:
            offenders.append((css_path, matches))

    if not offenders:
        print(f"✅ 仅 {ALLOWED_FILE} 含全局选择器")
        return 0

    print(f"❌ 以下文件含不应出现的全局选择器 (body/html/*):\n")
    for path, matches in offenders:
        text = path.read_text(encoding="utf-8")
        print(f"  {path.relative_to(ROOT)}: {len(matches)} 处")
        for m in matches:
            line_no = text[:m.start()].count("\n") + 1
            print(f"    line {line_no}: {m.group(0)}")
    print(f"\n共 {len(offenders)} 个文件需要清理")
    return 1


if __name__ == "__main__":
    sys.exit(main())
