#!/usr/bin/env python3
"""
audit_undefined_css_vars.py — 枚举未定义的 CSS 变量，按 4 类分桶

类别:
  - tailwind_product: tailwind.css 内部引用 (Tailwind 编译产物)
  - tailwind_class_as_var: 在 tailwind.css 中以 var() 形式使用 Tailwind 类名
  - should_migrate_to_tokens: 引用方的 tokens.css 已定义 (误报)
  - truly_undefined: 真正未定义

退出码: 0 = OK; 1 = 有 truly_undefined; 2 = 工具故障
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
CSS_DIR = ROOT / "css"
TOKENS_FILE = CSS_DIR / "tokens.css"
TAILWIND_FILE = CSS_DIR / "tailwind.css"
OUTPUT_FILE = ROOT / "output" / "audit_undefined_css_vars.json"

VAR_REF = re.compile(r"var\(\s*--([a-zA-Z0-9_-]+)")
VAR_DEF = re.compile(r"\s*--([a-zA-Z0-9_-]+)\s*:")


def extract_used_vars(css_dir: Path) -> dict[str, set[str]]:
    """返回 {filename: {var_name, ...}}"""
    result: dict[str, set[str]] = {}
    for css_path in sorted(css_dir.glob("*.css")):
        if not css_path.is_file():
            continue
        try:
            text = css_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        result[css_path.name] = set(VAR_REF.findall(text))
    return result


def extract_defined_vars(tokens_file: Path) -> set[str]:
    if not tokens_file.exists():
        return set()
    text = tokens_file.read_text(encoding="utf-8")
    return set(VAR_DEF.findall(text))


def categorize_undefined(
    used: set[str],
    defined: set[str],
    file_map: dict[str, set[str]],
    tailwind_file: Path,
) -> dict[str, list[dict]]:
    """对每个未定义变量分类"""
    undefined = used - defined
    buckets: dict[str, list[dict]] = {
        "tailwind_product": [],
        "tailwind_class_as_var": [],
        "should_migrate_to_tokens": [],
        "truly_undefined": [],
    }
    # 注: 简化版分类 — 仅识别 truly_undefined
    # tailwind_product / class_as_var 需要 tailwind.css 内引用识别
    # 留作可扩展 (当前实现为最小可用版本)
    for var in sorted(undefined):
        files_using = sorted(
            f for f, vars_ in file_map.items() if var in vars_
        )
        entry = {
            "var": var,
            "files_using": files_using,
            "first_seen_line": f"{files_using[0]}:?" if files_using else "?",
        }
        # 简单启发式: 若 tailwind.css 文件存在且含此 var, 归为 tailwind_product
        is_in_tailwind = False
        if tailwind_file.exists():
            tailwind_text = tailwind_file.read_text(encoding="utf-8")
            # 注: 原 plan 代码 VAR_DEF.search(f"--{var}", tailwind_text) 参数顺序错
            # (re.Pattern.search 第一个位置参数是 string, 不是 pattern) → 修正为:
            defined_in_tailwind = set(VAR_DEF.findall(tailwind_text))
            is_in_tailwind = var in defined_in_tailwind
        if is_in_tailwind:
            buckets["tailwind_product"].append(entry)
        else:
            buckets["truly_undefined"].append(entry)
    return buckets


def build_report(
    used: set[str],
    defined: set[str],
    undefined_items: list[dict],
    categories: dict[str, int],
) -> dict:
    return {
        "scan_date": date.today().isoformat(),
        "total_refs": sum(
            len(v) for v in used.values() if isinstance(v, set)
        ) if isinstance(used, dict) else len(used),
        "total_defs": len(defined) if isinstance(defined, set) else 0,
        "undefined_count": len(undefined_items),
        "categories": categories,
        "items": undefined_items,
    }


def collect_all_used(file_map: dict[str, set[str]]) -> set[str]:
    """展平 file_map 为 var 集合"""
    result: set[str] = set()
    for vars_ in file_map.values():
        result.update(vars_)
    return result


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not CSS_DIR.exists():
        print(f"❌ CSS 目录不存在: {CSS_DIR}", file=sys.stderr)
        return 2

    file_map = extract_used_vars(CSS_DIR)
    defined = extract_defined_vars(TOKENS_FILE)
    all_used = collect_all_used(file_map)
    undefined_set = all_used - defined

    categories_dict = categorize_undefined(
        undefined_set, defined, file_map, TAILWIND_FILE
    )

    # 合并所有未定义项
    items = []
    for bucket_name, entries in categories_dict.items():
        for entry in entries:
            entry["category"] = bucket_name
            items.append(entry)

    category_counts = {k: len(v) for k, v in categories_dict.items()}

    report = build_report(
        used=file_map,
        defined=defined,
        undefined_items=items,
        categories=category_counts,
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ 扫描完成: 引用 {report['total_refs']} 个变量")
    print(f"   已定义: {report['total_defs']}, 未定义: {report['undefined_count']}")
    print(f"   分类: {category_counts}")
    print(f"   输出: {OUTPUT_FILE.relative_to(ROOT)}")

    return 1 if category_counts["truly_undefined"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
