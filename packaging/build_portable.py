"""Build a portable (extract-and-run) distribution zip for Windows.

This is the no-Inno-Setup alternative.  It bundles:
  - Embedded CPython 3.11
  - All pip dependencies
  - The app source tree (staged)
  - launcher.py
  - One-click run.bat

Output: dist/Star-Learn-Portable-{version}.zip

Usage:
    python packaging/build_portable.py          # full build
    python packaging/build_portable.py --skip-deps   # skip pip install (if already done)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIST = ROOT / "dist"
PAYLOAD = HERE / "app_payload"
PYTHON_DIR = HERE / "python"
PY_EXE = PYTHON_DIR / "python.exe"


# ── helpers ──────────────────────────────────────────────────────────
def run(cmd: list[str], desc: str = "") -> None:
    print(f"[portable] {desc or ' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        sys.exit(f"[portable] FAILED: {' '.join(cmd)}")


def python(cmd: list[str], desc: str = "") -> None:
    run([sys.executable] + cmd, desc)


# ── steps ────────────────────────────────────────────────────────────
def fetch_embedded_python() -> None:
    if PY_EXE.exists():
        print(f"[portable] Embedded Python already present: {PY_EXE}")
        return
    print("[portable] Downloading embedded Python 3.11.9 ...")
    fetch_bat = HERE / "fetch_python.bat"
    if not fetch_bat.exists():
        sys.exit("[portable] fetch_python.bat not found.")
    run([str(fetch_bat)], "fetch_python.bat")


def ensure_pip_works() -> None:
    """Uncomment `import site` in python*._pth so pip can see site-packages."""
    import re
    for pth in PYTHON_DIR.glob("python*._pth"):
        text = pth.read_text(encoding="utf-8")
        if "import site" in text and not text.startswith("#import site"):
            continue
        new_text = re.sub(r"^#\s*import\s+site", "import site", text, flags=re.M)
        pth.write_text(new_text, encoding="utf-8")
        print(f"[portable] Patched {pth.name}")


def install_deps() -> None:
    ensure_pip_works()
    req = ROOT / "requirements.txt"
    if not req.exists():
        sys.exit(f"[portable] {req} not found.")
    run([
        str(PY_EXE), "-m", "pip", "install",
        "--no-warn-script-location", "--disable-pip-version-check",
        "-r", str(req),
    ], "pip install -r requirements.txt")


def stage_payload() -> None:
    python([str(HERE / "stage_payload.py")], "stage_payload.py")


def write_run_bat(build_dir: Path) -> None:
    """Create a one-click run.bat in the portable build root."""
    bat = build_dir / "Star-Learn.bat"
    bat.write_text(
        '@echo off\r\n'
        'title Star-Learn (Xingshi)\r\n'
        'cd /d "%~dp0"\r\n'
        'start "" "%~dp0python\\python.exe" "%~dp0launcher.py"\r\n',
        encoding="ascii",
    )
    print(f"[portable] Created {bat.name}")


def build_zip(skip_deps: bool = False) -> None:
    DIST.mkdir(parents=True, exist_ok=True)

    # 1. assets
    python([str(HERE / "assets" / "generate_assets.py")], "generate_assets.py")

    # 2. stage
    stage_payload()

    # 3. embedded Python
    fetch_embedded_python()

    # 4. deps
    if not skip_deps:
        install_deps()

    # 5. Create build directory
    version = "1.0.0"
    build_name = f"Star-Learn-Portable-{version}"
    build_dir = DIST / build_name
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    # 6. Copy everything into build_dir
    print("[portable] Assembling distribution...")

    # app payload
    _copytree(PAYLOAD, build_dir)
    print(f"  ✓ app payload")

    # embedded python
    _copytree(PYTHON_DIR, build_dir / "python")
    print(f"  ✓ embedded Python")

    # launcher
    shutil.copy2(HERE / "launcher.py", build_dir / "launcher.py")
    print(f"  ✓ launcher.py")

    # starter env template
    templates_dir = build_dir / "packaging" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / "templates" / "starter.env", templates_dir / "starter.env")
    print(f"  ✓ starter.env template")

    # assets
    assets_dir = build_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for f in (HERE / "assets").iterdir():
        if f.is_file():
            shutil.copy2(f, assets_dir / f.name)
    print(f"  ✓ assets")

    # run.bat
    write_run_bat(build_dir)

    # 7. Zip
    zip_path = DIST / f"{build_name}.zip"
    print(f"[portable] Creating {zip_path} ...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(build_dir.rglob("*")):
            if f.is_file():
                arcname = str(f.relative_to(DIST))
                zf.write(f, arcname)

    # 8. Cleanup build dir
    shutil.rmtree(build_dir)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[portable] Done!  {zip_path}  ({size_mb:.1f} MB)")
    print(f"[portable] Users extract the zip and double-click Star-Learn.bat to run.")


def _copytree(src: Path, dst: Path) -> None:
    """shutil.copytree but dst may already exist (merge)."""
    if not dst.exists():
        shutil.copytree(src, dst)
        return
    for item in src.iterdir():
        s = src / item.name
        d = dst / item.name
        if s.is_dir():
            _copytree(s, d)
        else:
            shutil.copy2(s, d)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build portable Star-Learn distribution")
    parser.add_argument("--skip-deps", action="store_true", help="Skip pip install")
    args = parser.parse_args()

    os.chdir(ROOT)
    build_zip(skip_deps=args.skip_deps)


if __name__ == "__main__":
    import os
    os.chdir(str(ROOT))
    main()
