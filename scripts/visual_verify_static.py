#!/usr/bin/env python3
"""
Static verification fallback for the 5 high-risk HTML pages.

Performs:
1. Fetches each HTML over the local HTTP server and confirms 200.
2. Parses each HTML and extracts <link rel="stylesheet"> tags in document order.
3. Fetches each referenced CSS over HTTP and verifies the response is 200.
4. Parses each CSS file and verifies opening/closing brace counts match
   (basic sanity check for syntactic well-formedness).
5. Verifies that the shared 5-link "core" sequence appears in the expected
   order: tokens, app-base, app-bg, components, animations.

This is the fallback path when a real headless browser is unavailable.
"""

import re
import sys
import urllib.request
from html.parser import HTMLParser

BASE = "http://localhost:8765"
PAGES = [
    ("login",            "/html/login.html",
     ["tokens", "app-base", "app-bg", "components", "animations"]),
    ("register",         "/html/register.html",
     ["tokens", "app-base", "app-bg", "components", "animations"]),
    ("hub",              "/html/hub.html",
     ["tokens", "app-base", "app-bg", "components", "animations"]),
    ("personal",         "/html/personal.html",
     ["tokens", "app-base", "app-bg", "components", "animations"]),
    ("teacher-dashboard", "/html/teacher-dashboard.html",
     ["tokens", "app-base", "app-bg", "components", "animations"]),
]


def fetch(url: str) -> tuple[int, str]:
    """Fetch URL; return (http_code, body)."""
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, f"<<error: {e}>>"


def extract_stylesheet_links(html: str) -> list[str]:
    """Return all <link rel="stylesheet" href="..."> hrefs in document order."""
    out: list[str] = []
    pattern = re.compile(
        r'<link[^>]*\brel=["\']stylesheet["\'][^>]*\bhref=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    for m in pattern.finditer(html):
        out.append(m.group(1))
    # also handle href before rel (rare, but be safe)
    pattern2 = re.compile(
        r'<link[^>]*\bhref=["\']([^"\']+)["\'][^>]*\brel=["\']stylesheet["\']',
        re.IGNORECASE,
    )
    for m in pattern2.finditer(html):
        out.append(m.group(1))
    return out


def has_token(hrefs: list[str], name: str) -> bool:
    return any(f"/css/{name}.css" in h for h in hrefs)


def check_brace_balance(css: str) -> tuple[bool, int, int]:
    """Return (balanced, opens, closes)."""
    opens = css.count("{")
    closes = css.count("}")
    return opens == closes, opens, closes


def main() -> int:
    overall_ok = True
    rows: list[dict] = []
    print("== Static visual-verify fallback ==\n")

    for label, path, expected_core in PAGES:
        url = f"{BASE}{path}"
        code, body = fetch(url)
        served_ok = code == 200
        hrefs = extract_stylesheet_links(body) if served_ok else []

        core_ok = all(has_token(hrefs, name) for name in expected_core)
        order_ok = True
        last_idx = -1
        for name in expected_core:
            idx = next(
                (i for i, h in enumerate(hrefs) if f"/css/{name}.css" in h),
                -1,
            )
            if idx == -1 or idx < last_idx:
                order_ok = False
                break
            last_idx = idx

        # Fetch each referenced CSS and confirm 200 + brace balance
        css_results: list[tuple[str, int, bool, int, int]] = []
        for h in hrefs:
            css_url = h if h.startswith("http") else f"{BASE}{h}"
            cc, css_body = fetch(css_url)
            bal, op, cl = check_brace_balance(css_body) if cc == 200 else (False, 0, 0)
            css_results.append((h, cc, bal, op, cl))

        css_all_ok = all(cc == 200 and bal for _, cc, bal, _, _ in css_results)
        all_ok = served_ok and core_ok and order_ok and css_all_ok
        overall_ok = overall_ok and all_ok

        rows.append({
            "label": label,
            "path": path,
            "http": code,
            "core_ok": core_ok,
            "order_ok": order_ok,
            "css_all_ok": css_all_ok,
            "css_results": css_results,
            "all_ok": all_ok,
            "hrefs": hrefs,
        })

    # Print per-page report
    for r in rows:
        print(f"--- {r['label']} ({r['path']}) ---")
        print(f"  HTTP: {r['http']}  expected_core_ok: {r['core_ok']}  order_ok: {r['order_ok']}  css_all_ok: {r['css_all_ok']}  overall: {r['all_ok']}")
        print(f"  stylesheet link order:")
        for h in r["hrefs"]:
            print(f"    - {h}")
        print(f"  CSS file checks:")
        for h, cc, bal, op, cl in r["css_results"]:
            print(f"    {h}  http={cc}  braces_opens={op}  braces_closes={cl}  balanced={bal}")
        print()

    print(f"== OVERALL: {'PASS' if overall_ok else 'FAIL'} ==")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
