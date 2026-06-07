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
            with js_path.open(encoding="utf-8") as f:
                line_count = sum(1 for _ in f)
        except OSError:
            continue
        if line_count > threshold_lines:
            try:
                rel = str(js_path.relative_to(ROOT))
            except ValueError:
                rel = str(js_path)
            results.append({
                "file": js_path.name,
                "path": rel,
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
    # 收集待扫描的 (dir, ext) 组合, 用 resolved 路径去重 (避免 html_dir == js_dir 重复)
    pairs: list[tuple[Path, str]] = []
    seen_dirs: set[tuple[Path, str]] = set()
    for base in (html_dir, js_dir):
        for ext in (".html", ".js"):
            key = (base.resolve() if base.exists() else base, ext)
            if key in seen_dirs:
                continue
            seen_dirs.add(key)
            pairs.append((base, ext))
    for base, ext in pairs:
        for p in _iter_text_files(base, ext):
            try:
                lines = p.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for idx, line in enumerate(lines, 1):
                m = TODO.search(line)
                if m:
                    try:
                        rel = str(p.relative_to(ROOT))
                    except ValueError:
                        rel = str(p)
                    results.append({
                        "file": p.name,
                        "path": rel,
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
