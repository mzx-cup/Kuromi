# Frontend Style Conflict Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate "load order determines styles" fragility, fix incorrect CSS loading, and clean up dead code per the approved spec at `docs/superpowers/specs/2026-06-07-frontend-style-conflict-resolution-design.md`.

**Architecture:** Three-layer CSS responsibility (base / components / page) with single-source-of-truth load order. Each fix is an independent commit for low-risk rollback. Verification is gated by L1 static checks, L2 manual rendering, and L3 Playwright snapshots.

**Tech Stack:** Vanilla HTML/CSS/JS + Playwright + Python (verification scripts) + Bash

---

## File Structure

**New files:**
- `scripts/verify_css_load_order.py` — L1 static check: enforce 2.2-section load order in all HTML
- `scripts/audit_tailwind.py` — One-shot tool to count Tailwind utility class usage
- `tests/frontend/e2e/css-conflict-resolution.spec.js` — L3 Playwright snapshot tests for 5 high-risk pages

**Modified files:**
- `html/login.html` — Remove incorrect `teacher.css` link (Action 2)
- `html/register.html` — Remove incorrect `teacher.css` link (Action 2)
- 13 HTML files — Switch Tailwind CDN to local (Action 3)
- `css/hub.css` — Remove duplicate `body` / `*` / `html` selectors (Action 4 pilot)
- 13+ other CSS files — Remove duplicate global selectors (Action 4 rollout)

**Deleted files:**
- `css/hub-perfect.css`
- `css/hub-winmoes.css`
- `css/hub.css.backup`
- `css/hub-refined.css.backup`

---

### Task 0: Set Up Verification Script — CSS Load Order Check

**Files:**
- Create: `scripts/verify_css_load_order.py`

- [ ] **Step 1: Create scripts directory and write the verifier**

Create `scripts/verify_css_load_order.py` with the following content:

```python
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
```

- [ ] **Step 2: Run the verifier to confirm it works (expect 1 error for login/register)**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && python scripts/verify_css_load_order.py`
Expected: Shows at least one error like `login.html` has `tokens.css` (rank=0) appearing after `teacher.css` (unclassified). This is the existing broken state, which we'll fix in later tasks.

- [ ] **Step 3: Commit**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main
git add scripts/verify_css_load_order.py
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "chore(verify): 新增 CSS 加载顺序静态检查脚本"
```

---

### Task 1: Delete Orphan CSS Files

**Files:**
- Delete: `css/hub-perfect.css`
- Delete: `css/hub-winmoes.css`
- Delete: `css/hub.css.backup`
- Delete: `css/hub-refined.css.backup`

- [ ] **Step 1: Confirm no HTML/JS references the orphan files**

Run:
```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
grep -rn "hub-perfect\|hub-winmoes" --include="*.html" --include="*.js" | grep -v "css/hub-perfect\|css/hub-winmoes"
```

Expected: Either no output, or only matches in `js/hub.js` referencing the string `hub-perfect-animations` (which is a `<style>` ID, not a file reference — safe to ignore).

- [ ] **Step 2: Delete the four orphan files**

Run:
```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
git rm css/hub-perfect.css css/hub-winmoes.css css/hub.css.backup css/hub-refined.css.backup
```

Expected: Output shows the 4 files staged for deletion.

- [ ] **Step 3: Verify the local dev server can still find hub.css**

Run:
```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
ls css/hub.css && wc -l css/hub.css
```

Expected: `css/hub.css` exists, line count > 0 (this is the file we keep).

- [ ] **Step 4: Commit**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "chore(cleanup): 删除 hub 相关孤儿 CSS 文件 (hub-perfect/winmoes/2 个 backup)"
```

---

### Task 2: Fix login.html — Remove Incorrect teacher.css Load

**Files:**
- Modify: `html/login.html:6`

- [ ] **Step 1: Read login.html to see current state**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && sed -n '1,15p' html/login.html`
Expected: See `<link rel="stylesheet" href="/css/teacher.css">` on line 6, before `tokens.css` on line 7.

- [ ] **Step 2: Remove the teacher.css link and reorder**

Edit `html/login.html` to replace lines 6-11 with the following (using `Edit` tool, replace the entire `<link>` block from line 6 through line 11):

OLD:
```
  <link rel="stylesheet" href="/css/teacher.css">
  <link rel="stylesheet" href="/css/tokens.css">
  <link rel="stylesheet" href="/css/components.css">
  <link rel="stylesheet" href="/css/animations.css">
  <link rel="stylesheet" href="/css/app-base.css">
  <link rel="stylesheet" href="/css/app-bg.css">
```

NEW:
```
  <link rel="stylesheet" href="/css/tokens.css">
  <link rel="stylesheet" href="/css/components.css">
  <link rel="stylesheet" href="/css/animations.css">
  <link rel="stylesheet" href="/css/app-base.css">
  <link rel="stylesheet" href="/css/app-bg.css">
```

- [ ] **Step 3: Verify the change**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && grep -n "teacher.css" html/login.html`
Expected: No output (no more references).

- [ ] **Step 4: Run the load-order verifier**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && python scripts/verify_css_load_order.py 2>&1 | grep -E "login|register"`
Expected: No error lines mentioning `login.html`.

- [ ] **Step 5: Manually inspect login.html still loads core styles**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && sed -n '1,15p' html/login.html`
Expected: See tokens.css, components.css, animations.css, app-base.css, app-bg.css in that order. No teacher.css.

- [ ] **Step 6: Commit**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
git add html/login.html && \
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "fix(auth): 移除登录页误加载的 teacher.css"
```

---

### Task 3: Fix register.html — Remove Incorrect teacher.css Load

**Files:**
- Modify: `html/register.html:6`

- [ ] **Step 1: Confirm register.html has the same issue**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && sed -n '1,15p' html/register.html`
Expected: See the same `<link rel="stylesheet" href="/css/teacher.css">` on line 6.

- [ ] **Step 2: Remove the teacher.css link and reorder**

Edit `html/register.html` to replace lines 6-11 with the same corrected block as Task 2:

OLD:
```
  <link rel="stylesheet" href="/css/teacher.css">
  <link rel="stylesheet" href="/css/tokens.css">
  <link rel="stylesheet" href="/css/components.css">
  <link rel="stylesheet" href="/css/animations.css">
  <link rel="stylesheet" href="/css/app-base.css">
  <link rel="stylesheet" href="/css/app-bg.css">
```

NEW:
```
  <link rel="stylesheet" href="/css/tokens.css">
  <link rel="stylesheet" href="/css/components.css">
  <link rel="stylesheet" href="/css/animations.css">
  <link rel="stylesheet" href="/css/app-base.css">
  <link rel="stylesheet" href="/css/app-bg.css">
```

- [ ] **Step 3: Verify the change**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && grep -n "teacher.css" html/register.html`
Expected: No output.

- [ ] **Step 4: Run the load-order verifier**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && python scripts/verify_css_load_order.py 2>&1 | grep -E "login|register"`
Expected: No error lines.

- [ ] **Step 5: Commit**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
git add html/register.html && \
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "fix(auth): 移除注册页误加载的 teacher.css"
```

---

### Task 4: Audit Tailwind Utility Class Usage

**Files:**
- Create: `scripts/audit_tailwind.py`

- [ ] **Step 1: Write the audit script**

Create `scripts/audit_tailwind.py` with the following content:

```python
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
```

- [ ] **Step 2: Run the audit**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && python scripts/audit_tailwind.py`
Expected: Output listing top 30 utility classes. The output will inform the next step's decision (switch to local vs keep CDN).

- [ ] **Step 3: Record the decision in a comment file for the team**

Create `docs/superpowers/notes/tailwind-audit-2026-06-07.md` with content:

```markdown
# Tailwind 审计结果 (2026-06-07)

- 扫描文件数: <N>
- 独立 utility class 数: <N>
- 决策: <根据 audit_tailwind.py 输出填写 — 切本地 / 保留 CDN defer>

执行人: 实施此计划的工程师
日期: 2026-06-07
```

Fill in the actual numbers and decision based on Step 2 output.

- [ ] **Step 4: Commit audit script and note**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
git add scripts/audit_tailwind.py docs/superpowers/notes/tailwind-audit-2026-06-07.md && \
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "chore(audit): 新增 Tailwind utility class 使用范围审计脚本"
```

---

### Task 5: Unify Tailwind Loading (Based on Audit Decision)

**Files:**
- Modify: 14 HTML files using Tailwind (1 already uses local, 13 use CDN)

- [ ] **Step 1: List all HTML files using Tailwind CDN**

Run:
```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
grep -l "cdn.tailwindcss.com" html/*.html
```

Expected: 13 files listed (e.g. `ai-pair-programming.html`, `architecture-blueprint.html`, etc.).

- [ ] **Step 2: Decision branch**

Based on the audit from Task 4:
- **If audit shows < 30 independent utility classes**: replace each CDN `<script>` with `<link rel="stylesheet" href="/css/tailwind.css">` (note: CDN is a script, local is a link).
- **If audit shows ≥ 30 independent utility classes**: add `defer` attribute to existing CDN `<script>` tags.

- [ ] **Step 3 (Option A — switch to local): For each CDN file, replace the script tag**

For each file from Step 1, run:

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
# 用 sed 替换 CDN 脚本为本地 link（保留行内缩进）
for f in $(grep -l "cdn.tailwindcss.com" html/*.html); do
  sed -i 's|<script src="https://cdn.tailwindcss.com"></script>|<link rel="stylesheet" href="/css/tailwind.css">|' "$f"
done
```

- [ ] **Step 3 (Option B — keep CDN with defer): For each CDN file, add `defer`**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
for f in $(grep -l "cdn.tailwindcss.com" html/*.html); do
  sed -i 's|<script src="https://cdn.tailwindcss.com"></script>|<script defer src="https://cdn.tailwindcss.com"></script>|' "$f"
done
```

- [ ] **Step 4: Verify no HTML still uses the old CDN pattern**

Run:
```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
# 如果选了 Option A: 应无 CDN 引用
# 如果选了 Option B: 引用都带 defer
grep -n "cdn.tailwindcss.com" html/*.html
```

Expected for Option A: No output.
Expected for Option B: All matches include `defer`.

- [ ] **Step 5: Run the load-order verifier**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && python scripts/verify_css_load_order.py`
Expected: No new errors introduced by this task.

- [ ] **Step 6: Commit**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
git add html/*.html && \
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "refactor(perf): 统一 Tailwind 加载方式为本地编译版" || \
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "refactor(perf): Tailwind CDN 改为 defer 异步加载"
```

(Use the message matching the option chosen.)

---

### Task 6: Add CSS Variable Reference Check Script

**Files:**
- Create: `scripts/verify_css_vars.py`

- [ ] **Step 1: Write the script**

Create `scripts/verify_css_vars.py` with the following content:

```python
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
```

- [ ] **Step 2: Run the script to baseline current state**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && python scripts/verify_css_vars.py`
Expected: Some output showing referenced vs defined counts. May show a few undefined variables (existing tech debt, not introduced by this plan).

- [ ] **Step 3: Commit**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
git add scripts/verify_css_vars.py && \
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "chore(verify): 新增 CSS 变量引用完整性检查脚本"
```

---

### Task 7: Add Global Selector Audit Script

**Files:**
- Create: `scripts/audit_global_selectors.py`

- [ ] **Step 1: Write the audit script**

Create `scripts/audit_global_selectors.py` with the following content:

```python
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
        print(f"  {path.relative_to(ROOT)}: {len(matches)} 处")
        for m in matches:
            line_no = path.read_text(encoding="utf-8")[:m.start()].count("\n") + 1
            print(f"    line {line_no}: {m.group(0)}")
    print(f"\n共 {len(offenders)} 个文件需要清理")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the script to see baseline**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && python scripts/audit_global_selectors.py`
Expected: List of ~11+ files containing `body { }` and 6+ with `* { }`. This is the existing state to clean up.

- [ ] **Step 3: Commit**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
git add scripts/audit_global_selectors.py && \
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "chore(verify): 新增全局选择器审计脚本"
```

---

### Task 8: Pilot — Remove Global Selectors from hub.css

**Files:**
- Modify: `css/hub.css`

- [ ] **Step 1: Find global selectors in hub.css**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && grep -nE "^\s*(body|html|\*)\s*\{" css/hub.css`
Expected: A few lines (likely 1-3) showing the offending selectors.

- [ ] **Step 2: Read the surrounding context of each match**

For each line number from Step 1, read 5-10 lines around it to identify the full rule block (e.g. `body { ... }` or `* { ... }`).

- [ ] **Step 3: For each rule block, decide:**
- If it's redundant with `app-base.css` (e.g. body margin/padding/font-family): **delete the entire block**
- If it adds new properties: extract those properties to a `.page-*` class or move to `app-base.css`

- [ ] **Step 4: Remove the redundant blocks**

Edit `css/hub.css` and delete the identified redundant blocks. For example, if line 121 is `body { ... }` and the properties are all in `app-base.css`, delete the whole block including its closing `}`.

- [ ] **Step 5: Run the audit script to confirm only hub.css's violations are reduced**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && grep -nE "^\s*(body|html|\*)\s*\{" css/hub.css`
Expected: Fewer matches than Step 1 (ideally 0).

- [ ] **Step 6: Sanity check — make sure file still parses**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && python -c "import cssutils; sheet = cssutils.parseString(open('css/hub.css').read()); print('OK, %d rules' % len(sheet))"` 
Expected: Either "OK, N rules" or "ModuleNotFoundError: No module named 'cssutils'". If module not found, skip — file is plain text and a missing `}` would be obvious in browser DevTools.

- [ ] **Step 7: Visually inspect hub page (if dev server running) or skip**

If the dev server is running, open `http://localhost:8000/html/hub.html` and verify:
- Body still has the global background and font
- Cards still display correctly
- Theme switching still works

If no dev server, skip and rely on Task 11 L2 verification at the end.

- [ ] **Step 8: Commit the pilot**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
git add css/hub.css && \
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "refactor(css): 试点 - 移除 hub.css 中重复的全局选择器"
```

---

### Task 9: Roll Out — Remove Global Selectors from Remaining Page CSS

**Files:**
- Modify: 13+ other CSS files (one commit per file for granular rollback)

- [ ] **Step 1: List remaining files with global selectors**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && python scripts/audit_global_selectors.py | grep "css/" | awk '{print $1}' | sed 's/:$//'`
Expected: 13+ files (e.g. `css/personal.css`, `css/index.css`, `css/classroom.css`, `css/calendar.css`, `css/code.css`, `css/concept-analyzer.css`, `css/ai-pair-programming.css`, `css/architecture-blueprint.css`, `css/flow-meter.css`, `css/generation-preview.css`, `css/plant.css`, `css/components-glass.css`).

- [ ] **Step 2: For each file, repeat the pilot pattern**

For each file from Step 1, do the same procedure as Task 8:
1. `grep -nE "^\s*(body|html|\*)\s*\{" <file>` to find violations
2. Read 5-10 lines around each match
3. Decide: delete (if redundant with app-base.css) or extract to .page-* / move to app-base.css
4. Edit the file
5. Commit per file:
   ```bash
   git add <file> && \
   git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "refactor(css): 移除 <file> 中重复的全局选择器"
   ```

- [ ] **Step 3: Run the audit script to confirm clean state**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && python scripts/audit_global_selectors.py`
Expected: `✅ 仅 app-base.css 含全局选择器`

- [ ] **Step 4: Run the load-order verifier**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && python scripts/verify_css_load_order.py`
Expected: `✅ 所有 HTML 加载顺序符合约定`

---

### Task 10: Add Playwright Snapshot Test for High-Risk Pages

**Files:**
- Create: `tests/frontend/e2e/css-conflict-resolution.spec.js`

- [ ] **Step 1: Examine existing e2e test for patterns**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && head -50 tests/frontend/e2e/smoke.spec.js`
Expected: See how existing tests import Playwright, set up `test()`, and use `page.goto()`.

- [ ] **Step 2: Write the new test file**

Create `tests/frontend/e2e/css-conflict-resolution.spec.js` with the following content:

```javascript
/**
 * css-conflict-resolution.spec.js — L3 回归测试
 *
 * 验证 5 个高风险页面的核心 UI 状态：
 * 1. 加载正确（无 console error）
 * 2. 主题切换后 CSS 变量值变化
 * 3. 不加载被禁用的 CSS 文件
 */
const { test, expect } = require('@playwright/test');

const HIGH_RISK_PAGES = [
  { path: '/html/login.html', name: 'login', forbiddenCss: ['teacher.css'] },
  { path: '/html/register.html', name: 'register', forbiddenCss: ['teacher.css'] },
  { path: '/html/hub.html', name: 'hub', forbiddenCss: ['hub-perfect.css', 'hub-winmoes.css'] },
  { path: '/html/personal.html', name: 'personal', forbiddenCss: [] },
  { path: '/html/teacher-dashboard.html', name: 'teacher-dashboard', forbiddenCss: [] },
];

for (const page of HIGH_RISK_PAGES) {
  test(`${page.name} - 加载不包含禁用 CSS`, async ({ page: browserPage }) => {
    const loadedStylesheets = [];

    // 拦截所有样式表请求
    browserPage.on('response', (response) => {
      const url = response.url();
      if (url.endsWith('.css')) {
        loadedStylesheets.push(url);
      }
    });

    await browserPage.goto(page.path);
    await browserPage.waitForLoadState('networkidle');

    for (const forbidden of page.forbiddenCss) {
      const found = loadedStylesheets.find((url) => url.includes(forbidden));
      expect(found, `${page.name} 不应加载 ${forbidden}`).toBeUndefined();
    }
  });

  test(`${page.name} - 主题切换后 CSS 变量值变化`, async ({ page: browserPage }) => {
    await browserPage.goto(page.path);
    await browserPage.waitForLoadState('networkidle');

    // 读取当前主题的 brand-400 颜色
    const before = await browserPage.evaluate(() => {
      return getComputedStyle(document.documentElement)
        .getPropertyValue('--brand-400')
        .trim();
    });
    expect(before, '应能读取到 --brand-400 变量').not.toBe('');

    // 切换 data-theme 属性（模拟主题切换）
    await browserPage.evaluate(() => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current && current.includes('sakura') ? 'bamboo-dark' : 'sakura-dark';
      document.documentElement.setAttribute('data-theme', next);
    });

    // 等待样式应用
    await browserPage.waitForTimeout(200);

    const after = await browserPage.evaluate(() => {
      return getComputedStyle(document.documentElement)
        .getPropertyValue('--brand-400')
        .trim();
    });

    expect(after, '切换主题后 --brand-400 应变化').not.toBe(before);
  });
}
```

- [ ] **Step 3: Run the new test (dev server must be running)**

Run:
```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
npm run test:e2e -- tests/frontend/e2e/css-conflict-resolution.spec.js
```

Expected: All 10 tests pass (5 pages × 2 assertions each). If a test fails, the corresponding page has a regression — investigate before proceeding.

- [ ] **Step 4: Commit**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
git add tests/frontend/e2e/css-conflict-resolution.spec.js && \
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "test(e2e): 新增样式冲突解决方案的回归测试"
```

---

### Task 11: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run all L1 static checks**

Run:
```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
python scripts/verify_css_load_order.py && \
python scripts/verify_css_vars.py && \
python scripts/audit_global_selectors.py
```

Expected: All three scripts exit with code 0 and print `✅` lines.

- [ ] **Step 2: Confirm orphan files are gone**

Run:
```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
ls css/hub-perfect.css css/hub-winmoes.css css/hub.css.backup css/hub-refined.css.backup 2>&1
```

Expected: All four files show "No such file or directory".

- [ ] **Step 3: Confirm login/register don't load teacher.css**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && grep -n "teacher.css" html/login.html html/register.html`
Expected: No output.

- [ ] **Step 4: Run the e2e test suite**

Run: `cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && npm run test:e2e`
Expected: All existing tests + the new css-conflict-resolution tests pass.

- [ ] **Step 5: L2 manual rendering check (5 high-risk pages)**

If dev server is running, open each of these 5 pages in a browser:
- `http://localhost:8000/html/login.html`
- `http://localhost:8000/html/register.html`
- `http://localhost:8000/html/hub.html`
- `http://localhost:8000/html/personal.html`
- `http://localhost:8000/html/teacher-dashboard.html`

For each:
1. Toggle light/dark theme — colors should follow
2. Open theme modal and switch between 3 themes (sakura, bamboo, star) — colors should change
3. Open browser console — no style-related errors

If no dev server, document the limitation in the final report and rely on the e2e test in Step 4.

- [ ] **Step 6: Final commit (if any last-minute fixes were made)**

```bash
cd c:/Users/zwc/Downloads/Kuromi-main/Kuromi-main && \
git status
```

If there are uncommitted changes:
```bash
git add -A && \
git -c user.name="Claude" -c user.email="claude@anthropic.com" commit -m "chore(verify): 最终验证微调"
```

If clean, skip.

---

## Acceptance Criteria Checklist

Reference: [docs/superpowers/specs/2026-06-07-frontend-style-conflict-resolution-design.md#7-验收标准](../specs/2026-06-07-frontend-style-conflict-resolution-design.md)

- [ ] 4 个孤儿 CSS 文件已删除 (Task 1)
- [ ] 登录 / 注册页不再加载 `teacher.css` (Tasks 2, 3)
- [ ] Tailwind 加载方式统一 (Task 5)
- [ ] 所有页面级 CSS 文件不再含 `body { }` / `* { }` / `html { }` (Tasks 8, 9)
- [ ] L1 静态检查全部通过 (Task 11 Step 1)
- [ ] L2 5 个高风险页面渲染验证通过 (Task 11 Step 5)
- [ ] L3 至少 1 个 Playwright snapshot 测试通过 (Tasks 10, 11 Step 4)
