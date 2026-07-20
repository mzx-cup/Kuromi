"""Install all dependencies into the embedded Python.

Run from project root:
    packaging\python\python.exe packaging\install_deps.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
PYTHON_DIR = HERE / "python"
PY_EXE = PYTHON_DIR / "python.exe"
PTH_FILE = next(PYTHON_DIR.glob("python*._pth"), None)
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
LOCK_FILE = HERE / "requirements.lock.txt"


def uncomment_import_site() -> None:
    """Embedded CPython ships with `#import site` in `python311._pth`; pip needs it on."""
    if PTH_FILE is None or not PTH_FILE.exists():
        print(f"[install_deps] WARN: no ._pth file found in {PYTHON_DIR}")
        return
    text = PTH_FILE.read_text(encoding="utf-8")
    new_text = re.sub(r"^#\s*import\s+site\s*$", "import site", text, flags=re.M)
    if new_text == text:
        print(f"[install_deps] {PTH_FILE.name} already has 'import site' uncommented.")
    else:
        PTH_FILE.write_text(new_text, encoding="utf-8")
        print(f"[install_deps] Uncommented 'import site' in {PTH_FILE.name}.")


def run_pip_install() -> None:
    if not REQUIREMENTS.exists():
        sys.exit(f"[install_deps] FATAL: {REQUIREMENTS} not found.")
    print(f"[install_deps] Installing requirements from {REQUIREMENTS.name}...")
    # Use a Tsinghua mirror first as a primary; fall back to default PyPI on failure.
    # `--no-warn-script-location` keeps the embedded Python clean (no Scripts\ entries
    # needed for an embeddable install).
    cmd = [
        str(PY_EXE), "-m", "pip", "install",
        "--no-warn-script-location",
        "--disable-pip-version-check",
        "-r", str(REQUIREMENTS),
    ]
    print(f"[install_deps] $ {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print("[install_deps] pip install failed; aborting.")
        sys.exit(result.returncode)


def write_lock() -> None:
    print(f"[install_deps] Writing lock file to {LOCK_FILE}...")
    cmd = [str(PY_EXE), "-m", "pip", "freeze"]
    out = subprocess.check_output(cmd, encoding="utf-8")
    LOCK_FILE.write_text(out, encoding="utf-8")
    print(f"[install_deps] Wrote {len(out.splitlines())} pinned packages.")


def main() -> None:
    if not PY_EXE.exists():
        sys.exit(
            f"[install_deps] FATAL: {PY_EXE} not found.\n"
            f"  Run packaging\\fetch_python.bat first."
        )
    uncomment_import_site()
    run_pip_install()
    write_lock()
    print("[install_deps] Done.")


if __name__ == "__main__":
    main()
