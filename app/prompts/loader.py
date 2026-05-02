from __future__ import annotations

import re
from pathlib import Path

_PROMPTS_ROOT = Path(__file__).resolve().parent.parent.parent / "prompts"
_TEMPLATES_DIR = _PROMPTS_ROOT / "templates"
_SNIPPETS_DIR = _PROMPTS_ROOT / "snippets"

_SNIPPET_CACHE: dict[str, str] = {}
_TEMPLATE_CACHE: dict[str, tuple[str, str]] = {}

_SNIPPET_RE = re.compile(r"\{\{\s*snippet:([\w\-]+)\s*\}\}")
_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _load_snippet(name: str) -> str:
    if name not in _SNIPPET_CACHE:
        path = _SNIPPETS_DIR / f"{name}.md"
        if path.exists():
            _SNIPPET_CACHE[name] = path.read_text(encoding="utf-8").strip()
        else:
            _SNIPPET_CACHE[name] = f"[snippet:{name} not found]"
    return _SNIPPET_CACHE[name]


def _resolve_snippets(text: str) -> str:
    def _replace(m: re.Match[str]) -> str:
        return _load_snippet(m.group(1))
    return _SNIPPET_RE.sub(_replace, text)


def _interpolate(text: str, variables: dict[str, str]) -> str:
    def _replace(m: re.Match[str]) -> str:
        key = m.group(1)
        return variables.get(key, m.group(0))
    return _VAR_RE.sub(_replace, text)


def load_template(prompt_id: str, variables: dict[str, str] | None = None) -> tuple[str, str]:
    variables = variables or {}

    cache_key = f"{prompt_id}:{sorted(variables.items())}"
    if cache_key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[cache_key]

    template_dir = _TEMPLATES_DIR / prompt_id
    system_path = template_dir / "system.md"
    user_path = template_dir / "user.md"

    system_text = system_path.read_text(encoding="utf-8").strip() if system_path.exists() else ""
    user_text = user_path.read_text(encoding="utf-8").strip() if user_path.exists() else ""

    system_text = _resolve_snippets(system_text)
    user_text = _resolve_snippets(user_text)

    system_text = _interpolate(system_text, variables)
    user_text = _interpolate(user_text, variables)

    result = (system_text, user_text)
    _TEMPLATE_CACHE[cache_key] = result
    return result
