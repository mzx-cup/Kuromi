"""Pack 5 sources into a <= 3KB markdown block."""
from __future__ import annotations

from datetime import datetime, timezone


_MAX_BYTES = 3000


def pack(commit_sha: str, results: dict[str, str]) -> str:
    parts = [
        f"# Project State @ {commit_sha}",
        "",
        f"_Refreshed: {datetime.now(timezone.utc).isoformat()}_",
        "",
        "## 当前切片", results.get("slices", ""),
        "",
        "## 最近 ADR", results.get("adrs", ""),
        "",
        "## 最近 commit", results.get("git", ""),
        "",
        "## 漂移警告", results.get("drift", ""),
        "",
        "## 最近巩固", results.get("consol", ""),
    ]
    text = "\n".join(parts)
    # Iteratively shrink until under the byte budget. Start by halving,
    # then micro-trim by 10% until we fit or hit a lower bound.
    if len(text.encode("utf-8")) > _MAX_BYTES:
        keep_fraction = 0.5
        while keep_fraction > 0.1 and len(text.encode("utf-8")) > _MAX_BYTES:
            lines = text.splitlines()
            cut = max(2, int(len(lines) * keep_fraction))
            text = "\n".join(lines[:cut]) + "\n_(truncated)_"
            keep_fraction -= 0.1
    return text
