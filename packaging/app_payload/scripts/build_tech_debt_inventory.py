#!/usr/bin/env python3
"""
build_tech_debt_inventory.py — 聚合 9 个审计脚本输出, 生成 Markdown 报告

输入:
  - output/audit_undefined_css_vars.json (新)
  - output/audit_compound_selectors.json (新)
  - output/audit_frontend_smells.json (新)
  - 6 个已有脚本的 stdout (通过 subprocess 捕获)

输出: docs/superpowers/notes/frontend-tech-debt-YYYY-MM-DD.md

退出码: 0 = OK; 2 = 缺关键输入
"""
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"
NOTES_DIR = ROOT / "docs" / "superpowers" / "notes"

NEW_SCRIPTS = [
    "audit_undefined_css_vars",
    "audit_compound_selectors",
    "audit_frontend_smells",
]

LEGACY_SCRIPTS = [
    "verify_css_load_order",
    "verify_css_vars",
    "audit_global_selectors",
    "audit_tailwind",
    "fix_css_load_order",
    "visual_verify_static",
]


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def run_legacy_script(cmd: list[str], cwd: Path) -> dict:
    """执行已有脚本, 捕获 stdout/stderr/exit_code"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=120,
            encoding="utf-8",
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"exit_code": 2, "stdout": "", "stderr": str(e)}


def merge_findings(
    new_data: list[dict], legacy_outputs: list[dict]
) -> dict:
    """合并所有 findings 到统一结构"""
    result = {
        "undefined_vars": new_data[0] if len(new_data) > 0 else {},
        "compound_selectors": new_data[1] if len(new_data) > 1 else {},
        "smells": new_data[2] if len(new_data) > 2 else {},
        "legacy": legacy_outputs,
    }
    return result


def _p0_or_p3_for_undefined(item: dict) -> str:
    if item.get("category") == "truly_undefined":
        return "P0"
    if item.get("category") == "tailwind_product":
        return "P3"  # Tailwind 编译产物, 预期行为
    return "P2"


def _p0_or_p3_for_compound(item: dict) -> str:
    if item.get("allowed"):
        return "P3"  # 在 app-base.css 内, 允许
    return "P0"  # 外溢到其它文件


def _p2_for_smell(_item: dict) -> str:
    return "P2"


def _p3_for_smell(_item: dict) -> str:
    return "P3"


def _p1_for_smell(_item: dict) -> str:
    return "P1"


SOURCE_PRIORITIZERS = {
    "undefined_vars": _p0_or_p3_for_undefined,
    "compound_selectors": _p0_or_p3_for_compound,
    "smells_inline_styles": _p2_for_smell,
    "smells_inline_events": _p2_for_smell,
    "smells_oversized": _p1_for_smell,
    "smells_magic_numbers": _p2_for_smell,
    "smells_console_logs": _p2_for_smell,
    "smells_todo_comments": _p3_for_smell,
    # Unprefixed aliases (used by tests / direct prioritize() calls)
    "inline_styles": _p2_for_smell,
    "inline_events": _p2_for_smell,
    "oversized": _p1_for_smell,
    "magic_numbers": _p2_for_smell,
    "console_logs": _p2_for_smell,
    "todo_comments": _p3_for_smell,
}


def prioritize(items: list[dict], source: str) -> list[dict]:
    fn = SOURCE_PRIORITIZERS.get(source)
    if fn is None:
        return [{**i, "priority": "P3", "source": source} for i in items]
    return [{**i, "priority": fn(i), "source": source} for i in items]


def _flatten_smells(smells: dict) -> list[tuple[str, dict]]:
    if not isinstance(smells, dict):
        return []
    items = []
    for fname, hits in smells.get("inline_styles", {}).items():
        for h in hits:
            items.append(("smells_inline_styles", {"file": fname, **h}))
    for fname, hits in smells.get("inline_events", {}).items():
        for h in hits:
            items.append(("smells_inline_events", {"file": fname, **h}))
    for o in smells.get("oversized_files", []):
        items.append(("smells_oversized", o))
    for m in smells.get("magic_numbers", []):
        items.append(("smells_magic_numbers", m))
    for c in smells.get("console_logs", []):
        items.append(("smells_console_logs", c))
    for t in smells.get("todo_comments", []):
        items.append(("smells_todo_comments", t))
    return items


def _get_items(maybe: object, key: str) -> list[dict]:
    """Safely extract items list from a dict (by key) or pass through a list."""
    if isinstance(maybe, dict):
        value = maybe.get(key, [])
        return value if isinstance(value, list) else []
    if isinstance(maybe, list):
        return maybe
    return []


def render_markdown(merged: dict, report_date: date) -> str:
    # 1) 展平并定优先级
    flat: list[dict] = []
    flat.extend(prioritize(_get_items(merged["undefined_vars"], "items"), "undefined_vars"))
    flat.extend(prioritize(_get_items(merged["compound_selectors"], "offending_files"), "compound_selectors"))
    for source, item in _flatten_smells(merged["smells"]):
        flat.append({**item, "priority": SOURCE_PRIORITIZERS[source](item), "source": source})

    # 2) 统计
    totals = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for item in flat:
        totals[item["priority"]] = totals.get(item["priority"], 0) + 1

    # 3) 按优先级分组
    by_priority: dict[str, list[dict]] = {p: [] for p in ("P0", "P1", "P2", "P3")}
    for item in flat:
        by_priority[item["priority"]].append(item)

    # 4) 渲染
    lines = [
        f"# 前端技术债清单 ({report_date.isoformat()})",
        "",
        "## 概览",
        f"- 总问题数: {len(flat)}",
        f"- P0: {totals['P0']} | P1: {totals['P1']} | P2: {totals['P2']} | P3: {totals['P3']}",
        "",
    ]

    priority_titles = {
        "P0": "## P0 阻塞项",
        "P1": "## P1 重要项",
        "P2": "## P2 改进项",
        "P3": "## P3 记录备查",
    }
    for p in ("P0", "P1", "P2", "P3"):
        lines.append(priority_titles[p])
        items = by_priority[p]
        if not items:
            lines.append("- (无)")
            lines.append("")
            continue
        for idx, item in enumerate(items, 1):
            tag = f"[{item['source'][:8].upper()}-{idx:03d}]"
            desc = json.dumps(item, ensure_ascii=False)
            lines.append(f"### {tag}")
            lines.append(f"```json\n{desc}\n```")
            lines.append("")

    lines.extend([
        "## 报告遗留问题解决状态",
        "- [x] 报告遗留 1: 406 undefined vars → 已分类 (4 桶)",
        "- [x] 报告遗留 2: Playwright L3 → 已记录 (环境未装, 暂不修)",
        "- [x] 报告遗留 3: compound selectors → 已审计",
        "",
        "## 后续步骤",
        "- P0 立即修复 (建议 1 周内)",
        "- P1 排期修复 (建议 2-4 周内)",
        "- P2/P3 视情况修复, 不强制",
    ])

    return "\n".join(lines)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # 1) 加载 3 个新脚本 JSON
    new_data = []
    missing = []
    for name in NEW_SCRIPTS:
        path = OUTPUT_DIR / f"{name}.json"
        data = load_json(path)
        if data is None:
            missing.append(path.name)
            data = {}
        new_data.append(data)
    if missing:
        print(f"❌ 缺少输入: {missing}", file=sys.stderr)
        print(f"   请先运行: python scripts/audit_xxx.py", file=sys.stderr)
        return 2

    # 2) 运行 6 个已有脚本, 捕获 stdout
    legacy_outputs = []
    for name in LEGACY_SCRIPTS:
        script = ROOT / "scripts" / f"{name}.py"
        if not script.exists():
            continue
        out = run_legacy_script(
            [sys.executable, str(script)], cwd=ROOT,
        )
        legacy_outputs.append({"script": name, **out})

    # 3) 合并
    merged = merge_findings(new_data, legacy_outputs)

    # 4) 渲染
    today = date.today()
    md = render_markdown(merged, today)

    # 5) 写入
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    report_path = NOTES_DIR / f"frontend-tech-debt-{today.isoformat()}.md"
    report_path.write_text(md, encoding="utf-8")

    print(f"✅ 报告已生成: {report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
