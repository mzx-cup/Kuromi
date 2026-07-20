"""Copy the project tree (minus dev junk) into packaging/app_payload/ for Inno Setup.

Run from project root:
    python packaging/stage_payload.py
"""
from __future__ import annotations

import fnmatch
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
PAYLOAD = HERE / "app_payload"

# Top-level directories to skip entirely.
EXCLUDE_DIRS = {
    "node_modules", "__pycache__", "audio",
    "demo-results", "shots", "perf-results", "verify-dd-out",
    "docs", "Seedance", "Navicat", ".claude",
    ".git", ".github", ".pytest_cache", ".superpowers", ".vscode",
    ".agents", "dist", "packaging",  # packaging itself is staged separately
}
# Top-level files to skip.
EXCLUDE_FILES = {
    "package.json", "package-lock.json",
    "playwright.config.js", "vitest.config.js",
    "agents.py",  # oddly large; re-evaluate — actually keep, this is a core module
}
# Glob patterns (matched against basename anywhere in the tree).
EXCLUDE_GLOBS = {
    "*.db", "*.bak", "*.pre-migration.bak",
    "local_storage.json*", "uvicorn.log",
}
# Remove agents.py from the exclude list (was a typo above).
EXCLUDE_FILES.discard("agents.py")


def should_skip_dir(name: str) -> bool:
    return name in EXCLUDE_DIRS or name.startswith(".") and name not in {".env", ".env.ascii"}


def should_skip_file(path: Path) -> bool:
    base = path.name
    if base in EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(base, g) for g in EXCLUDE_GLOBS)


def copy_tree() -> None:
    if PAYLOAD.exists():
        print(f"[stage] Cleaning {PAYLOAD}...")
        shutil.rmtree(PAYLOAD)
    PAYLOAD.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    for src in sorted(PROJECT_ROOT.iterdir()):
        if src.name in EXCLUDE_DIRS:
            print(f"[stage]   skip dir:  {src.name}/")
            skipped += 1
            continue
        if src.is_file():
            if should_skip_file(src):
                print(f"[stage]   skip file: {src.name}")
                skipped += 1
                continue
            shutil.copy2(src, PAYLOAD / src.name)
            copied += 1
            continue
        # Directory: walk and selectively copy.
        for root, dirs, files in src.walk() if hasattr(src, "walk") else _walk(src):
            # Filter subdirs in-place to prune.
            dirs[:] = [d for d in dirs if not should_skip_dir(d)]
            rel = Path(root).relative_to(src)
            dest_dir = PAYLOAD / src.name / rel
            dest_dir.mkdir(parents=True, exist_ok=True)
            for f in files:
                fp = Path(root) / f
                if should_skip_file(fp):
                    continue
                shutil.copy2(fp, dest_dir / f)
                copied += 1
        print(f"[stage]   copied dir: {src.name}/")
    print(f"[stage] Done. {copied} files copied, {skipped} entries skipped.")
    print(f"[stage] Payload: {PAYLOAD}")


def _walk(p: Path):
    """Compatibility shim for pathlib.walk (3.12+)."""
    import os
    for root, dirs, files in os.walk(p):
        yield Path(root), dirs, files


def main() -> None:
    if not PROJECT_ROOT.is_dir():
        sys.exit(f"[stage] FATAL: project root {PROJECT_ROOT} not found.")
    copy_tree()


if __name__ == "__main__":
    main()
