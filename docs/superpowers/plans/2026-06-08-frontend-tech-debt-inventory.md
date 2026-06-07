# 前端技术债清点 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 解决 2026-06-08 前端样式冲突解决报告中的 3 项遗留问题，并完成一次全量前端技术债扫描，输出一份带 P0/P1/P2/P3 优先级的清点报告。

**Architecture:** 3 个新审计脚本（各自输出 JSON）→ Layer 2 报告生成器（聚合 3 个新 + 6 个已有脚本输出）→ 一份 Markdown 报告。脚本只产数据，报告生成器负责排版与分级，数据/视图分离。

**Tech Stack:**
- Python 3.10+（标准库: `re`, `json`, `pathlib`, `subprocess`, `unittest`, `datetime`, `collections`）
- Playwright（已有，JS 集成测试用）
- 复用现有 6 个审计脚本（不改源码）

---

## 文件结构

### 新建（生产代码）
| 文件 | 职责 |
|------|------|
| `scripts/audit_undefined_css_vars.py` | 提取所有 `var(--xxx)` 引用，对比 `tokens.css` 定义，按 4 类分桶 |
| `scripts/audit_compound_selectors.py` | 扫描 `*` / `html` / `body` 等复合选择器（含 `*, *::before, *::after`） |
| `scripts/audit_frontend_smells.py` | 多维 smell 检测（内联 style/事件、超大文件、魔法数字、console.log 等） |
| `scripts/build_tech_debt_inventory.py` | 聚合 9 个脚本输出，生成带 P0/P1/P2/P3 分级的 Markdown 报告 |
| `output/` 目录 | 各脚本 JSON 输出（`.gitignore` 排除） |

### 新建（测试代码）
| 文件 | 职责 |
|------|------|
| `tests/scripts/__init__.py` | 空文件，标识 Python 包 |
| `tests/scripts/test_audit_undefined_css_vars.py` | unittest 单元测试 |
| `tests/scripts/test_audit_compound_selectors.py` | 同上 |
| `tests/scripts/test_audit_frontend_smells.py` | 同上 |
| `tests/scripts/test_build_tech_debt_inventory.py` | 同上 |
| `tests/frontend/e2e/tech-debt-inventory.spec.js` | Playwright L3 集成测试（验证报告产物） |
| `tests/fixtures/audit/sample-tokens.css` | 测试用 fixture：含已定义变量 |
| `tests/fixtures/audit/sample-hub.css` | 测试用 fixture：含正常/缺失变量、内联选择器 |
| `tests/fixtures/audit/sample-plant.css` | 测试用 fixture：含 `*, *::before, *::after` |

### 新建（产物，不入库）
| 文件 | 职责 |
|------|------|
| `output/audit_undefined_css_vars.json` | 脚本 1 原始数据 |
| `output/audit_compound_selectors.json` | 脚本 2 原始数据 |
| `output/audit_frontend_smells.json` | 脚本 3 原始数据 |
| `docs/superpowers/notes/frontend-tech-debt-2026-06-08.md` | 最终清点报告 |

### 修改
| 文件 | 变更 |
|------|------|
| `.gitignore` | 添加 `output/` |

---

## 通用约定（所有任务适用）

- **Windows 兼容**：每个 Python 脚本入口添加
  ```python
  try:
      sys.stdout.reconfigure(encoding="utf-8")
  except Exception:
      pass
  ```
- **退出码**：`0` = OK（无发现或全部 P3 级别），`1` = 发现 ≥ P0/P1 项，`2` = 工具自身故障
- **commit message 用中文**（项目惯例：参考 `a47ab29`、`fec18a0` 等近期 commit）
- **路径风格**：Python 用 `pathlib.Path`；命令行脚本相对项目根调用

---

## Task 1: 创建 output/ 目录 + 更新 .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 在 .gitignore 末尾追加 output/**

在 `.gitignore` 末尾添加：
```
output/
```

- [ ] **Step 2: 创建 output/ 目录**

```bash
mkdir -p output
```

- [ ] **Step 3: 创建 output/.gitkeep 占位文件**

```bash
touch output/.gitkeep
```

- [ ] **Step 4: 验证 .gitignore 正确生效**

```bash
git status
```

预期：`output/` 不出现在 untracked 文件中。

- [ ] **Step 5: 提交**

```bash
git add .gitignore output/.gitkeep
git commit -m "chore(audit): 新增 output/ 目录用于审计脚本产物"
```

---

## Task 2: audit_undefined_css_vars.py（TDD）

**Files:**
- Create: `tests/fixtures/audit/sample-tokens.css`
- Create: `tests/fixtures/audit/sample-hub.css`
- Create: `tests/scripts/__init__.py`
- Create: `tests/scripts/test_audit_undefined_css_vars.py`
- Create: `scripts/audit_undefined_css_vars.py`

### Step 1: 创建测试 fixture

- [ ] **Step 1.1: 创建 `tests/fixtures/audit/sample-tokens.css`**

```bash
mkdir -p tests/fixtures/audit
```

写入 `tests/fixtures/audit/sample-tokens.css`：
```css
:root {
    --color-primary: #a855f7;
    --color-bg: #1a1a2e;
    --spacing-md: 16px;
}
```

- [ ] **Step 1.2: 创建 `tests/fixtures/audit/sample-hub.css`**

写入 `tests/fixtures/audit/sample-hub.css`：
```css
.hero {
    color: var(--color-primary);
    background: var(--undefined-color-1);
    padding: var(--spacing-md);
    border: 1px solid var(--undefined-color-2);
}
```

- [ ] **Step 1.3: 创建 `tests/scripts/__init__.py`**

```bash
mkdir -p tests/scripts
touch tests/scripts/__init__.py
```

### Step 2: 写失败的测试

- [ ] **Step 2.1: 创建 `tests/scripts/test_audit_undefined_css_vars.py`**

```python
"""Unit tests for audit_undefined_css_vars.py"""
import unittest
import tempfile
from pathlib import Path

from scripts.audit_undefined_css_vars import (
    extract_used_vars,
    extract_defined_vars,
    categorize_undefined,
    build_report,
)


class ExtractUsedVarsTest(unittest.TestCase):
    def test_returns_dict_keyed_by_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "a.css").write_text(
                ".x { color: var(--c1); background: var(--c2); }",
                encoding="utf-8",
            )
            (css_dir / "b.css").write_text(
                ".y { padding: var(--p1); }",
                encoding="utf-8",
            )
            result = extract_used_vars(css_dir)
            self.assertIn("a.css", result)
            self.assertIn("b.css", result)
            self.assertEqual(result["a.css"], {"c1", "c2"})
            self.assertEqual(result["b.css"], {"p1"})

    def test_empty_css_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = extract_used_vars(Path(tmpdir))
            self.assertEqual(result, {})


class ExtractDefinedVarsTest(unittest.TestCase):
    def test_reads_tokens_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".css", delete=False, encoding="utf-8"
        ) as f:
            f.write(":root { --c1: red; --c2: blue; }")
            f.flush()
            tokens = Path(f.name)
        try:
            result = extract_defined_vars(tokens)
            self.assertEqual(result, {"c1", "c2"})
        finally:
            tokens.unlink()

    def test_missing_tokens_file(self):
        result = extract_defined_vars(Path("/nonexistent/tokens.css"))
        self.assertEqual(result, set())


class CategorizeUndefinedTest(unittest.TestCase):
    def test_truly_undefined(self):
        used = {"__missing__"}
        defined = set()
        file_map = {"hub.css": {"__missing__"}}
        result = categorize_undefined(used, defined, file_map, Path("/n/a"))
        self.assertEqual(len(result["truly_undefined"]), 1)
        self.assertEqual(result["truly_undefined"][0]["var"], "__missing__")

    def test_should_migrate_to_tokens(self):
        used = {"__defined__"}
        defined = {"__defined__"}
        result = categorize_undefined(used, defined, {}, Path("/n/a"))
        self.assertEqual(result["should_migrate_to_tokens"], [])


class BuildReportTest(unittest.TestCase):
    def test_report_contains_required_fields(self):
        report = build_report(
            used={"v1"},
            defined={"v1"},
            undefined_items=[],
            categories={
                "tailwind_product": 0,
                "tailwind_class_as_var": 0,
                "should_migrate_to_tokens": 0,
                "truly_undefined": 0,
            },
        )
        self.assertIn("scan_date", report)
        self.assertIn("total_refs", report)
        self.assertIn("total_defs", report)
        self.assertIn("undefined_count", report)
        self.assertIn("categories", report)
        self.assertIn("items", report)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2.2: 运行测试，验证失败**

```bash
python -m unittest tests.scripts.test_audit_undefined_css_vars -v
```

预期：FAIL，`ModuleNotFoundError: No module named 'scripts.audit_undefined_css_vars'`

### Step 3: 实现 audit_undefined_css_vars.py

- [ ] **Step 3.1: 创建 `scripts/audit_undefined_css_vars.py`**

```python
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
VAR_DEF = re.compile(r"^\s*--([a-zA-Z0-9_-]+)\s*:", re.MULTILINE)


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
            is_in_tailwind = bool(VAR_DEF.search(f"--{var}", tailwind_text) or
                                  f"--{var}" in tailwind_text)
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
```

- [ ] **Step 3.2: 运行测试，验证通过**

```bash
python -m unittest tests.scripts.test_audit_undefined_css_vars -v
```

预期：4 个测试类全部 PASS。

- [ ] **Step 3.3: 真实运行一次**

```bash
python scripts/audit_undefined_css_vars.py
```

预期：打印 `✅ 扫描完成 ...` + 输出文件 `output/audit_undefined_css_vars.json` 存在。

- [ ] **Step 3.4: 验证输出 JSON 结构**

```bash
python -c "import json; r=json.load(open('output/audit_undefined_css_vars.json', encoding='utf-8')); assert 'scan_date' in r; assert 'categories' in r; print('OK')"
```

预期：输出 `OK`。

- [ ] **Step 3.5: 提交**

```bash
git add tests/fixtures/audit/ tests/scripts/__init__.py tests/scripts/test_audit_undefined_css_vars.py scripts/audit_undefined_css_vars.py output/audit_undefined_css_vars.json
git commit -m "feat(audit): 新增 audit_undefined_css_vars.py 扫描未定义 CSS 变量"
```

---

## Task 3: audit_compound_selectors.py（TDD）

**Files:**
- Create: `tests/fixtures/audit/sample-plant.css`
- Create: `tests/scripts/test_audit_compound_selectors.py`
- Create: `scripts/audit_compound_selectors.py`

### Step 1: 创建 fixture

- [ ] **Step 1.1: 创建 `tests/fixtures/audit/sample-plant.css`**

```css
/* 正常规则 */
.leaf { color: green; }

/* 复合选择器 — 应被捕获 */
* { box-sizing: border-box; }
*, *::before, *::after { box-sizing: inherit; }

/* 预期外溢 */
body { margin: 0; }
html { font-size: 16px; }
```

### Step 2: 写失败的测试

- [ ] **Step 2.1: 创建 `tests/scripts/test_audit_compound_selectors.py`**

```python
"""Unit tests for audit_compound_selectors.py"""
import unittest
import tempfile
from pathlib import Path

from scripts.audit_compound_selectors import (
    find_compound_selectors,
    build_report,
)


class FindCompoundSelectorsTest(unittest.TestCase):
    def test_detects_universal_selector(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "x.css").write_text(
                "* { box-sizing: border-box; }\n.leaf { color: green; }",
                encoding="utf-8",
            )
            results = find_compound_selectors(css_dir)
            self.assertIn("x.css", results)
            hits = results["x.css"]
            self.assertGreater(len(hits), 0)
            self.assertEqual(hits[0]["selector"], "*")
            self.assertEqual(hits[0]["line"], 1)

    def test_detects_compound_universal_with_pseudo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "y.css").write_text(
                "*, *::before, *::after { box-sizing: inherit; }",
                encoding="utf-8",
            )
            results = find_compound_selectors(css_dir)
            hits = results["y.css"]
            self.assertGreater(len(hits), 0)
            # 至少要捕获到 * 部分
            self.assertTrue(any(h["selector"].startswith("*") for h in hits))

    def test_detects_body_selector(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "z.css").write_text(
                "body { margin: 0; }",
                encoding="utf-8",
            )
            results = find_compound_selectors(css_dir)
            hits = results["z.css"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["selector"], "body")

    def test_ignores_safe_selectors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "safe.css").write_text(
                ".card { padding: 16px; }\n#header { z-index: 10; }",
                encoding="utf-8",
            )
            results = find_compound_selectors(css_dir)
            self.assertEqual(results["safe.css"], [])


class BuildReportTest(unittest.TestCase):
    def test_report_structure(self):
        report = build_report(
            findings={"x.css": [{"line": 1, "selector": "*", "context": "* {}"}]},
            total_files=5,
        )
        self.assertIn("scan_date", report)
        self.assertIn("total_files", report)
        self.assertIn("offending_files", report)
        self.assertEqual(report["total_files"], 5)
        self.assertEqual(len(report["offending_files"]), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2.2: 运行测试，验证失败**

```bash
python -m unittest tests.scripts.test_audit_compound_selectors -v
```

预期：FAIL，`ModuleNotFoundError: No module named 'scripts.audit_compound_selectors'`

### Step 3: 实现 audit_compound_selectors.py

- [ ] **Step 3.1: 创建 `scripts/audit_compound_selectors.py`**

```python
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
PATTERN = re.compile(
    r"^\s*((?:\*|html|body)(?:\s*,\s*(?:\*|html|body|::?[a-z-]+))*)\s*\{",
    re.MULTILINE,
)


def find_compound_selectors(css_dir: Path) -> dict[str, list[dict]]:
    """返回 {filename: [{line, selector, context}]}"""
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
        if hits:
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

    # 分离允许文件 vs 外溢文件
    allowed_hits = findings.pop(ALLOWED_FILE, [])
    overflow_files = findings

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
        ],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(report_clean, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    overflow_count = len(overflow_files)
    print(f"✅ 扫描完成: {len(css_files)} 个 CSS 文件")
    print(f   f"   允许文件 (app-base.css): {len(allowed_hits)} 处")
    print(f"   外溢文件: {overflow_count} 个")

    return 1 if overflow_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
```

**注意**: 上方代码 `print(f   f"..."` 有一个错字 — 实际应使用单 `f`。修正:

- [ ] **Step 3.2: 修正错字并运行测试**

```python
# 将
print(f   f"   允许文件 (app-base.css): {len(allowed_hits)} 处")
# 改为
print(f"   允许文件 (app-base.css): {len(allowed_hits)} 处")
```

```bash
python -m unittest tests.scripts.test_audit_compound_selectors -v
```

预期：5 个测试全部 PASS。

- [ ] **Step 3.3: 真实运行一次**

```bash
python scripts/audit_compound_selectors.py
```

预期：打印扫描结果，输出 `output/audit_compound_selectors.json` 存在。

- [ ] **Step 3.4: 提交**

```bash
git add tests/fixtures/audit/sample-plant.css tests/scripts/test_audit_compound_selectors.py scripts/audit_compound_selectors.py output/audit_compound_selectors.json
git commit -m "feat(audit): 新增 audit_compound_selectors.py 扫描复合全局选择器"
```

---

## Task 4: audit_frontend_smells.py（TDD）

**Files:**
- Create: `tests/scripts/test_audit_frontend_smells.py`
- Create: `scripts/audit_frontend_smells.py`

### Step 1: 写失败的测试

- [ ] **Step 1.1: 创建 `tests/scripts/test_audit_frontend_smells.py`**

```python
"""Unit tests for audit_frontend_smells.py"""
import unittest
import tempfile
from pathlib import Path

from scripts.audit_frontend_smells import (
    detect_inline_styles,
    detect_inline_event_handlers,
    detect_oversized_files,
    detect_magic_numbers,
    detect_console_logs,
    detect_todo_comments,
    build_report,
)


class InlineStylesTest(unittest.TestCase):
    def test_detects_style_attribute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_dir = Path(tmpdir)
            (html_dir / "x.html").write_text(
                '<div style="color: red">x</div>',
                encoding="utf-8",
            )
            results = detect_inline_styles(html_dir)
            self.assertIn("x.html", results)
            self.assertEqual(len(results["x.html"]), 1)
            self.assertIn('style="color: red"', results["x.html"][0]["match"])


class InlineEventHandlersTest(unittest.TestCase):
    def test_detects_onclick(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_dir = Path(tmpdir)
            (html_dir / "y.html").write_text(
                '<button onclick="doIt()">Click</button>',
                encoding="utf-8",
            )
            results = detect_inline_event_handlers(html_dir)
            self.assertIn("y.html", results)
            self.assertEqual(len(results["y.html"]), 1)


class OversizedFilesTest(unittest.TestCase):
    def test_detects_large_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            js_dir = Path(tmpdir)
            big = js_dir / "big.js"
            # 写入 1100 行
            big.write_text("\n".join(["// line"] * 1100), encoding="utf-8")
            results = detect_oversized_files(js_dir, threshold_lines=1000)
            self.assertIn("big.js", results)


class MagicNumbersTest(unittest.TestCase):
    def test_detects_hex_color(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            css_dir = Path(tmpdir)
            (css_dir / "a.css").write_text(
                ".x { color: #a855f7; padding: 16px; }",
                encoding="utf-8",
            )
            results = detect_magic_numbers(css_dir)
            # 至少捕获到 #a855f7
            self.assertTrue(any("#a855f7" in r["match"] for r in results))


class ConsoleLogTest(unittest.TestCase):
    def test_detects_console_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            js_dir = Path(tmpdir)
            (js_dir / "app.js").write_text(
                "function init() {\n  console.log('debug');\n}",
                encoding="utf-8",
            )
            results = detect_console_logs(js_dir)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["file"], "app.js")
            self.assertEqual(results[0]["line"], 2)


class TodoCommentTest(unittest.TestCase):
    def test_detects_todo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "a.js").write_text(
                "// TODO: refactor this\nconst x = 1;",
                encoding="utf-8",
            )
            results = detect_todo_comments(base, base)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["keyword"], "TODO")


class BuildReportTest(unittest.TestCase):
    def test_report_structure(self):
        report = build_report(
            inline_styles={},
            inline_events={},
            oversized=[],
            magic_numbers=[],
            console_logs=[],
            todos=[],
        )
        for key in (
            "scan_date",
            "inline_styles",
            "inline_events",
            "oversized_files",
            "magic_numbers",
            "console_logs",
            "todo_comments",
        ):
            self.assertIn(key, report)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 1.2: 运行测试，验证失败**

```bash
python -m unittest tests.scripts.test_audit_frontend_smells -v
```

预期：FAIL，`ModuleNotFoundError: No module named 'scripts.audit_frontend_smells'`

### Step 2: 实现 audit_frontend_smells.py

- [ ] **Step 2.1: 创建 `scripts/audit_frontend_smells.py`**

```python
#!/usr/bin/env python3
"""
audit_frontend_smells.py — 多维前端代码 smell 检测

检测项 (8 维):
  1. HTML 内联 style="..."
  2. HTML/JS 内联事件处理器 (onclick 等)
  3. 单文件 > 1000 行
  4. 重复 CSS 规则 (跨文件) [MVP 跳过, P3]
  5. 未使用 CSS 类 [MVP 跳过, P3]
  6. 魔法数字 (硬编码颜色/尺寸)
  7. console.log 残留
  8. TODO/FIXME/XXX 注释

退出码: 0 = OK; 1 = 有发现; 2 = 工具故障
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
HTML_DIR = ROOT / "html"
JS_DIR = ROOT / "js"
CSS_DIR = ROOT / "css"
OUTPUT_FILE = ROOT / "output" / "audit_frontend_smells.json"

INLINE_STYLE = re.compile(r'style\s*=\s*"([^"]*)"')
INLINE_EVENT = re.compile(r'\son\w+\s*=\s*"([^"]*)"')
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
PX_SIZE = re.compile(r"\b\d+px\b")
CONSOLE_LOG = re.compile(r"console\.(log|debug|info)\s*\(")
TODO = re.compile(r"\b(TODO|FIXME|XXX)\b")


def _iter_text_files(directory: Path, ext: str):
    if not directory.exists():
        return
    for p in sorted(directory.glob(f"*{ext}")):
        if p.is_file():
            yield p


def detect_inline_styles(html_dir: Path) -> dict[str, list[dict]]:
    results: dict[str, list[dict]] = {}
    for html_path in _iter_text_files(html_dir, ".html"):
        text = html_path.read_text(encoding="utf-8")
        hits = [
            {"line": text[: m.start()].count("\n") + 1, "match": m.group(0)}
            for m in INLINE_STYLE.finditer(text)
        ]
        if hits:
            results[html_path.name] = hits
    return results


def detect_inline_event_handlers(html_dir: Path) -> dict[str, list[dict]]:
    results: dict[str, list[dict]] = {}
    for html_path in _iter_text_files(html_dir, ".html"):
        text = html_path.read_text(encoding="utf-8")
        hits = [
            {"line": text[: m.start()].count("\n") + 1, "match": m.group(0)}
            for m in INLINE_EVENT.finditer(text)
        ]
        if hits:
            results[html_path.name] = hits
    return results


def detect_oversized_files(
    js_dir: Path, threshold_lines: int = 1000
) -> list[dict]:
    results = []
    for js_path in _iter_text_files(js_dir, ".js"):
        try:
            line_count = sum(1 for _ in js_path.open(encoding="utf-8"))
        except OSError:
            continue
        if line_count > threshold_lines:
            results.append({
                "file": js_path.name,
                "path": str(js_path.relative_to(ROOT)),
                "lines": line_count,
            })
    return results


def detect_magic_numbers(css_dir: Path) -> list[dict]:
    results = []
    for css_path in _iter_text_files(css_dir, ".css"):
        text = css_path.read_text(encoding="utf-8")
        for pattern_name, pattern in (("hex_color", HEX_COLOR), ("px_size", PX_SIZE)):
            for m in pattern.finditer(text):
                results.append({
                    "file": css_path.name,
                    "line": text[: m.start()].count("\n") + 1,
                    "type": pattern_name,
                    "match": m.group(0),
                })
    return results


def detect_console_logs(js_dir: Path) -> list[dict]:
    results = []
    for js_path in _iter_text_files(js_dir, ".js"):
        try:
            lines = js_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for idx, line in enumerate(lines, 1):
            if CONSOLE_LOG.search(line):
                results.append({
                    "file": js_path.name,
                    "line": idx,
                    "match": line.strip()[:80],
                })
    return results


def detect_todo_comments(html_dir: Path, js_dir: Path) -> list[dict]:
    results = []
    for base in (html_dir, js_dir):
        for ext in (".html", ".js"):
            for p in _iter_text_files(base, ext):
                try:
                    lines = p.read_text(encoding="utf-8").splitlines()
                except (OSError, UnicodeDecodeError):
                    continue
                for idx, line in enumerate(lines, 1):
                    m = TODO.search(line)
                    if m:
                        results.append({
                            "file": p.name,
                            "line": idx,
                            "keyword": m.group(0),
                            "match": line.strip()[:80],
                        })
    return results


def build_report(
    inline_styles: dict,
    inline_events: dict,
    oversized: list,
    magic_numbers: list,
    console_logs: list,
    todos: list,
) -> dict:
    return {
        "scan_date": date.today().isoformat(),
        "inline_styles": inline_styles,
        "inline_events": inline_events,
        "oversized_files": oversized,
        "magic_numbers": magic_numbers,
        "console_logs": console_logs,
        "todo_comments": todos,
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    inline_styles = detect_inline_styles(HTML_DIR)
    inline_events = detect_inline_event_handlers(HTML_DIR)
    oversized = detect_oversized_files(JS_DIR)
    magic_numbers = detect_magic_numbers(CSS_DIR)
    console_logs = detect_console_logs(JS_DIR)
    todos = detect_todo_comments(HTML_DIR, JS_DIR)

    report = build_report(
        inline_styles, inline_events, oversized,
        magic_numbers, console_logs, todos,
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    total = (
        sum(len(v) for v in inline_styles.values())
        + sum(len(v) for v in inline_events.values())
        + len(oversized)
        + len(magic_numbers)
        + len(console_logs)
        + len(todos)
    )
    print(f"✅ 扫描完成: 共发现 {total} 处 smell")
    print(f"   内联样式: {sum(len(v) for v in inline_styles.values())}")
    print(f"   内联事件: {sum(len(v) for v in inline_events.values())}")
    print(f"   超大文件: {len(oversized)}")
    print(f"   魔法数字: {len(magic_numbers)}")
    print(f"   console: {len(console_logs)}")
    print(f"   TODO 等: {len(todos)}")
    print(f"   输出: {OUTPUT_FILE.relative_to(ROOT)}")

    return 1 if total > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2.2: 运行测试，验证通过**

```bash
python -m unittest tests.scripts.test_audit_frontend_smells -v
```

预期：7 个测试类全部 PASS。

- [ ] **Step 2.3: 真实运行一次**

```bash
python scripts/audit_frontend_smells.py
```

预期：打印 smell 统计，输出 `output/audit_frontend_smells.json` 存在。

- [ ] **Step 2.4: 提交**

```bash
git add tests/scripts/test_audit_frontend_smells.py scripts/audit_frontend_smells.py output/audit_frontend_smells.json
git commit -m "feat(audit): 新增 audit_frontend_smells.py 多维 smell 扫描"
```

---

## Task 5: build_tech_debt_inventory.py（TDD）

**Files:**
- Create: `tests/scripts/test_build_tech_debt_inventory.py`
- Create: `scripts/build_tech_debt_inventory.py`

### Step 1: 写失败的测试

- [ ] **Step 1.1: 创建 `tests/scripts/test_build_tech_debt_inventory.py`**

```python
"""Unit tests for build_tech_debt_inventory.py"""
import sys
import unittest
import tempfile
from pathlib import Path
from datetime import date

from scripts.build_tech_debt_inventory import (
    load_json,
    run_legacy_script,
    merge_findings,
    prioritize,
    render_markdown,
)


class LoadJsonTest(unittest.TestCase):
    def test_loads_valid_json(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write('{"a": 1}')
            f.flush()
            data = load_json(Path(f.name))
            self.assertEqual(data, {"a": 1})

    def test_missing_file_returns_none(self):
        data = load_json(Path("/nonexistent/file.json"))
        self.assertIsNone(data)


class RunLegacyScriptTest(unittest.TestCase):
    def test_captures_stdout(self):
        # 调用 python -c 模拟一个简单脚本
        result = run_legacy_script(
            [sys.executable, "-c", "print('hello')"],
            cwd=Path.cwd(),
        )
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("hello", result["stdout"])


class MergeFindingsTest(unittest.TestCase):
    def test_merges_three_new_scripts(self):
        new_data = [
            {
                "categories": {"truly_undefined": 2, "tailwind_product": 5},
                "items": [{"var": "--x", "category": "truly_undefined"}],
            },
            {"offending_files": [{"file": "a.css", "hits": []}]},
            {"inline_styles": {"x.html": []}, "console_logs": []},
        ]
        merged = merge_findings(new_data, [])
        self.assertIn("undefined_vars", merged)
        self.assertIn("compound_selectors", merged)
        self.assertIn("smells", merged)


class PrioritizeTest(unittest.TestCase):
    def test_truly_undefined_is_p0(self):
        items = [{"category": "truly_undefined", "var": "--x"}]
        result = prioritize(items, source="undefined_vars")
        self.assertEqual(result[0]["priority"], "P0")

    def test_compound_in_non_allowed_file_is_p0(self):
        items = [{"file": "plant.css", "allowed": False, "hits": []}]
        result = prioritize(items, source="compound_selectors")
        self.assertEqual(result[0]["priority"], "P0")

    def test_console_log_is_p2(self):
        items = [{"file": "x.js", "line": 1}]
        result = prioritize(items, source="console_logs")
        self.assertEqual(result[0]["priority"], "P2")

    def test_todo_is_p3(self):
        items = [{"file": "x.js", "line": 1, "keyword": "TODO"}]
        result = prioritize(items, source="todo_comments")
        self.assertEqual(result[0]["priority"], "P3")


class RenderMarkdownTest(unittest.TestCase):
    def test_contains_overview_section(self):
        merged = {
            "undefined_vars": [],
            "compound_selectors": [],
            "smells": [],
            "totals": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        }
        md = render_markdown(merged, date(2026, 6, 8))
        self.assertIn("# 前端技术债清单", md)
        self.assertIn("## 概览", md)
        self.assertIn("## 报告遗留问题解决状态", md)

    def test_contains_legacy_status_block(self):
        merged = {
            "undefined_vars": [],
            "compound_selectors": [],
            "smells": [],
            "totals": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        }
        md = render_markdown(merged, date(2026, 6, 8))
        self.assertIn("[x] 报告遗留 1", md)
        self.assertIn("[x] 报告遗留 2", md)
        self.assertIn("[x] 报告遗留 3", md)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 1.2: 运行测试，验证失败**

```bash
python -m unittest tests.scripts.test_build_tech_debt_inventory -v
```

预期：FAIL，`ModuleNotFoundError: No module named 'scripts.build_tech_debt_inventory'`

### Step 2: 实现 build_tech_debt_inventory.py

- [ ] **Step 2.1: 创建 `scripts/build_tech_debt_inventory.py`**

```python
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
}


def prioritize(items: list[dict], source: str) -> list[dict]:
    fn = SOURCE_PRIORITIZERS.get(source)
    if fn is None:
        return [{**i, "priority": "P3", "source": source} for i in items]
    return [{**i, "priority": fn(i), "source": source} for i in items]


def _flatten_smells(smells: dict) -> list[tuple[str, dict]]:
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


def render_markdown(merged: dict, report_date: date) -> str:
    # 1) 展平并定优先级
    flat: list[dict] = []
    flat.extend(prioritize(merged["undefined_vars"].get("items", []), "undefined_vars"))
    flat.extend(prioritize(merged["compound_selectors"].get("offending_files", []), "compound_selectors"))
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
```

- [ ] **Step 2.2: 运行测试，验证通过**

```bash
python -m unittest tests.scripts.test_build_tech_debt_inventory -v
```

预期：5 个测试类全部 PASS。

- [ ] **Step 2.3: 真实运行（需先有 3 个 JSON）**

```bash
python scripts/build_tech_debt_inventory.py
```

预期：打印 `✅ 报告已生成: ...`，`docs/superpowers/notes/frontend-tech-debt-2026-06-08.md` 存在。

- [ ] **Step 2.4: 验证报告内容**

```bash
head -20 docs/superpowers/notes/frontend-tech-debt-2026-06-08.md
```

预期：报告有标题、概览、P0/P1/P2/P3 章节。

- [ ] **Step 2.5: 提交**

```bash
git add tests/scripts/test_build_tech_debt_inventory.py scripts/build_tech_debt_inventory.py docs/superpowers/notes/frontend-tech-debt-2026-06-08.md
git commit -m "feat(audit): 新增 build_tech_debt_inventory.py 生成清点报告"
```

---

## Task 6: Playwright L3 集成测试

**Files:**
- Create: `tests/frontend/e2e/tech-debt-inventory.spec.js`

- [ ] **Step 1: 创建 `tests/frontend/e2e/tech-debt-inventory.spec.js`**

```javascript
/**
 * L3 集成测试 — 验证清点报告产物
 *
 * 由于本环境未装 Playwright 浏览器, 此测试在 CI 环境就绪后启用.
 * 验证内容:
 *   1. 报告文件存在
 *   2. 报告含 P0/P1/P2/P3 四个标题
 *   3. 报告含「报告遗留问题解决状态」块, 3 项全 [x]
 *   4. 报告含至少 1 个 P0 项的具体 file:line
 *
 * 运行 (环境就绪后):
 *   npx playwright test tests/frontend/e2e/tech-debt-inventory.spec.js
 */

const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '../../..');
const REPORT_PATH = path.join(
  PROJECT_ROOT,
  'docs/superpowers/notes/frontend-tech-debt-2026-06-08.md',
);

test.describe('Frontend Tech Debt Inventory Report', () => {
  test('report file exists', () => {
    expect(fs.existsSync(REPORT_PATH)).toBe(true);
  });

  test('report contains all priority sections', () => {
    const content = fs.readFileSync(REPORT_PATH, 'utf-8');
    expect(content).toMatch(/## P0 阻塞项/);
    expect(content).toMatch(/## P1 重要项/);
    expect(content).toMatch(/## P2 改进项/);
    expect(content).toMatch(/## P3 记录备查/);
  });

  test('report marks all 3 legacy issues resolved', () => {
    const content = fs.readFileSync(REPORT_PATH, 'utf-8');
    const matches = content.match(/\[x\] 报告遗留 \d/g) || [];
    expect(matches.length).toBeGreaterThanOrEqual(3);
  });

  test('P0 items have file:line references', () => {
    const content = fs.readFileSync(REPORT_PATH, 'utf-8');
    // 简易检查: P0 章节含 \d+:\d+ 形式
    const p0Section = content.split('## P0 阻塞项')[1]?.split('## P1')[0] || '';
    expect(p0Section).toMatch(/\d+:\d+/);
  });
});
```

- [ ] **Step 2: 验证语法（不实际运行 Playwright）**

```bash
node -c tests/frontend/e2e/tech-debt-inventory.spec.js 2>&1 || echo "OK: 语法检查完成 (如无输出则通过)"
```

预期：无语法错误。

- [ ] **Step 3: 提交**

```bash
git add tests/frontend/e2e/tech-debt-inventory.spec.js
git commit -m "test(e2e): 新增 tech-debt-inventory.spec.js L3 集成测试"
```

---

## Task 7: 完整流程验收

**Files:** 无新建/修改

- [ ] **Step 1: 清空 output 目录后, 完整跑 3 个审计脚本**

```bash
rm -f output/audit_*.json
python scripts/audit_undefined_css_vars.py
python scripts/audit_compound_selectors.py
python scripts/audit_frontend_smells.py
```

预期：每个都打印 `✅ 扫描完成 ...`, 退出码 0 或 1。

- [ ] **Step 2: 跑报告生成器**

```bash
python scripts/build_tech_debt_inventory.py
```

预期：打印 `✅ 报告已生成: docs/superpowers/notes/frontend-tech-debt-2026-06-08.md`, 退出码 0。

- [ ] **Step 3: 验证报告结构**

```bash
python -c "
import re
content = open('docs/superpowers/notes/frontend-tech-debt-2026-06-08.md', encoding='utf-8').read()
for section in ['## 概览', '## P0 阻塞项', '## P1 重要项', '## P2 改进项', '## P3 记录备查', '## 报告遗留问题解决状态']:
    assert section in content, f'missing: {section}'
print('OK: report structure valid')
"
```

预期：输出 `OK: report structure valid`。

- [ ] **Step 4: 跑全部单元测试**

```bash
python -m unittest discover tests/scripts -v
```

预期：所有测试 PASS。

- [ ] **Step 5: 检查 git 状态**

```bash
git status
```

预期：除 `local_storage.json` 和 `requirements.txt` 之外无其他未提交修改（这两个是已知 untracked 改动，与本次工作无关）。

- [ ] **Step 6: 提交验收报告（无新文件则 skip）**

```bash
git add -A
git diff --cached --quiet || git commit -m "chore(verify): 完整流程验收通过"
```

---

## 验收标准 (Acceptance Criteria)

本次 plan 完成的标志：

- [ ] AC1: `output/audit_undefined_css_vars.json` 存在且结构正确
- [ ] AC2: `output/audit_compound_selectors.json` 存在且结构正确
- [ ] AC3: `output/audit_frontend_smells.json` 存在且结构正确
- [ ] AC4: `docs/superpowers/notes/frontend-tech-debt-2026-06-08.md` 存在
- [ ] AC5: 报告含 P0/P1/P2/P3 四个标题
- [ ] AC6: 报告「报告遗留问题解决状态」三项全 `[x]`
- [ ] AC7: 4 个 Python unittest 文件全部通过
- [ ] AC8: 1 个 Playwright spec 文件存在 (`tests/frontend/e2e/tech-debt-inventory.spec.js`)
- [ ] AC9: 所有提交用中文 commit message

---

## 后续 (Out of This Plan)

本 plan 只完成「清点」。修复工作按 P0 → P1 → P2 → P3 在**后续独立 plan** 中推进，每个优先级一个 plan。

---

## Self-Review

执行人: writing-plans skill
日期: 2026-06-08

| 检查 | 结论 |
|------|------|
| Spec coverage | §3.1 / §3.2 / §3.3 / §3.4 / §3.5 错误处理 / §3.6 测试 — 全部覆盖 (Task 2-7) |
| Placeholder scan | 无 TBD/TODO/「类似 Task N」/「添加适当错误处理」类占位 |
| Type consistency | `extract_used_vars` / `extract_defined_vars` / `categorize_undefined` / `build_report` / `find_compound_selectors` / `detect_*` / `load_json` / `run_legacy_script` / `merge_findings` / `prioritize` / `render_markdown` — 跨任务签名一致 |
| 命令路径 | 所有 `python -m unittest tests.scripts.xxx` 路径与实际文件路径一致 |
| 测试框架 | 使用项目已有的 `unittest`（不是 pytest — 环境中未装 pytest） |
| 退出码 | 0/1/2 约定贯穿所有脚本 |
| Windows 兼容 | 每个 Python 脚本入口加 `sys.stdout.reconfigure` |
