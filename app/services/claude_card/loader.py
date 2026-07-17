"""Slice-B5: 5-source parallel load of project state for Claude cold-start."""
from __future__ import annotations

import concurrent.futures
import logging
import subprocess
from pathlib import Path

from app.services.claude_card.cache import ClaudeCardCache
from app.services.claude_card.packer import pack


_log = logging.getLogger(__name__)


def _read(path: str) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else f"(no {path})"


def _slice_status() -> str:
    return _read("SLICE_STATUS.md")


def _adr_recent(days: int = 30) -> str:
    specs = Path("docs/superpowers/specs")
    if not specs.exists():
        return "(no specs dir)"
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    out = []
    for p in specs.rglob("*.md"):
        try:
            t = datetime.fromtimestamp(p.stat().st_mtime)
        except OSError:
            continue
        if t >= cutoff:
            out.append(str(p.relative_to(".")))
    return "\n".join(out) or f"(no ADRs updated in last {days}d)"


def _git_log(n: int = 50) -> str:
    try:
        return subprocess.check_output(
            ["git", "log", "--oneline", f"-{n}"],
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            errors="replace",
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return f"(git unreachable: {exc})"


def _drift_reports() -> str:
    try:
        from app.repositories.orm.drift_report import OrmDriftReportRepository
        rows = OrmDriftReportRepository().list_unresolved(limit=20)
        if not rows:
            return "(no unresolved drift reports)"
        return "\n".join(
            f"- [{r.drift_kind}] {r.kb_node_id}: {r.source_ref}"
            for r in rows
        )
    except Exception as exc:  # noqa: BLE001
        return f"(drift reports unreachable: {exc})"


def _consolidation_log(n: int = 5) -> str:
    """Recent memory_consolidation action_types from AgentBehaviorLog."""
    try:
        from app.repositories.orm.agent_behavior_log import (
            OrmAgentBehaviorLogRepository,
        )
        repo = OrmAgentBehaviorLogRepository()
        # try common method names
        for method in ("recent_by_action", "list_recent", "recent"):
            if hasattr(repo, method):
                rows = getattr(repo, method)(
                    action_type="memory_consolidation", limit=n,
                )
                if rows:
                    break
        else:
            return "(no recent consolidation runs)"
        return "\n".join(
            f"- {r.timestamp.isoformat()}: {(getattr(r, 'output_text', '') or '')[:100]}"
            for r in rows
        ) or "(no recent consolidation runs)"
    except Exception as exc:  # noqa: BLE001
        return f"(consolidation log unreachable: {exc})"


_LOADERS = (
    ("slices", _slice_status),
    ("adrs", _adr_recent),
    ("git", _git_log),
    ("drift", _drift_reports),
    ("consol", _consolidation_log),
)


def load_card(commit_sha: str) -> str:
    cache = ClaudeCardCache()
    cached = cache.get(commit_sha)
    if cached is not None:
        return cached

    results: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futs = {key: ex.submit(fn) for key, fn in _LOADERS}
        for key, fut in futs.items():
            try:
                results[key] = fut.result(timeout=0.5)
            except Exception as exc:  # noqa: BLE001
                _log.warning("loader[%s] failed: %s", key, exc)
                results[key] = f"(loader failed: {exc})"

    markdown = pack(commit_sha, results)
    cache.set(commit_sha, markdown)
    return markdown


def main() -> int:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True, encoding="utf-8", errors="replace",
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"failed to read commit sha: {exc}", flush=True)
        return 1
    md = load_card(sha)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
