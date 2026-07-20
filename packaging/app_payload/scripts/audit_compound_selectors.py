#!/usr/bin/env python3
"""
audit_compound_selectors.py — 检测复合全局选择器

检测目标:
  - *  (含 *, *::before, *::after)
  - html
  - body

退出码: 0 = 仅 app-base.css 含 (若扫描到即算违规); 1 = 多个文件含
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
CSS_DIR = ROOT / "css"
ALLOWED_FILE = "app-base.css"
OUTPUT_FILE = ROOT / "output" / "audit_compound_selectors.json"

# 匹配复合选择器起始 (捕获完整选择器直到 {)
# 例: "*", "*, *::before, *::after", "body", "html"
# 注: 每个逗号分隔的单元允许附带 ::before/:hover 等伪元素。
# 原计划的 (?:\*|html|body|::?[a-z-]+) 不能处理 "*::before" 这种复合单元
# (因 :? 只能吞一个冒头, 剩余的 [a-z-]+ 吞不下第二冒头)。
# 现拆为 ::[a-z-]+ 与 :[a-z-]+ 两个分支, 更直观且测试通过。
PATTERN = re.compile(
    r"^\s*((?:\*|html|body)(?:::[a-z-]+|:[a-z-]+)*(?:\s*,\s*(?:\*|html|body)(?:::[a-z-]+|:[a-z-]+)*)*)\s*\{",
    re.MULTILINE,
)


def find_compound_selectors(css_dir: Path) -> dict[str, list[dict]]:
    """返回 {filename: [{line, selector, context}]} (含无命中文件, 列表为空)"""
    results: dict[str, list[dict]] = {}
    for css_path in sorted(css_dir.glob("*.css")):
        if not css_path.is_file():
            continue
        text = css_path.read_text(encoding="utf-8")
        hits = []
        for match in PATTERN.finditer(text):
            # 计算行号
            line_num = text[: match.start()].count("\n") + 1
            selector = match.group(1).strip()
            hits.append({
                "line": line_num,
                "selector": selector,
                "context": match.group(0).strip(),
            })
        # 始终收录文件 (无命中为空列表), 便于调用方使用直接下标
        results[css_path.name] = hits
    return results


def build_report(
    findings: dict[str, list[dict]],
    total_files: int,
) -> dict:
    return {
        "scan_date": date.today().isoformat(),
        "total_files": total_files,
        "offending_files": [
            {
                "file": fname,
                "allowed": fname == ALLOWED_FILE,
                "hits": hits,
            }
            for fname, hits in findings.items()
        ],
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not CSS_DIR.exists():
        print(f"❌ CSS 目录不存在: {CSS_DIR}", file=sys.stderr)
        return 2

    css_files = list(CSS_DIR.glob("*.css"))
    findings = find_compound_selectors(CSS_DIR)

    # 分离允许文件 vs 外溢文件 (只保留有命中的文件, 避免空噪声)
    allowed_hits = findings.pop(ALLOWED_FILE, [])
    overflow_files = {f: h for f, h in findings.items() if h}

    report = build_report(
        findings={"_app_base": allowed_hits, **overflow_files}
        if allowed_hits
        else overflow_files,
        total_files=len(css_files),
    )
    # 修正: build_report 需要纯 findings
    report_clean = {
        "scan_date": report["scan_date"],
        "total_files": report["total_files"],
        "offending_files": [
            {
                "file": fname,
                "allowed": fname == ALLOWED_FILE,
                "hits": hits,
            }
            for fname, hits in [
                (ALLOWED_FILE, allowed_hits),
                *[(f, h) for f, h in overflow_files.items()],
            ]
            if hits  # 仅收录实际有命中的文件
        ],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(report_clean, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    overflow_count = len(overflow_files)
    print(f"✅ 扫描完成: {len(css_files)} 个 CSS 文件")
    print(f"   允许文件 (app-base.css): {len(allowed_hits)} 处")
    print(f"   外溢文件: {overflow_count} 个")

    return 1 if overflow_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
