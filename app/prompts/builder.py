from __future__ import annotations

from app.prompts.loader import load_template


def build_prompt(prompt_id: str, **variables: str) -> tuple[str, str]:
    return load_template(prompt_id, dict(variables))
