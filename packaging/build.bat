@echo off
REM ============================================================================
REM  Star-Learn (Xingshi) Windows Installer Build Script
REM
REM  Prerequisites:
REM    1. Inno Setup 6+ installed (https://jrsoftware.org/isinfo.php)
REM       Default path: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
REM    2. Python 3.9+ on PATH (for staging + asset generation)
REM    3. Internet access (to download embedded Python + pip packages)
REM
REM  Usage:
REM    build.bat              Full build (assets → stage → python → deps → installer)
REM    build.bat stage        Only stage payload
REM    build.bat python       Only fetch embedded Python
REM    build.bat deps         Only install pip dependencies
REM    build.bat installer    Only run Inno Setup (assumes prior steps done)
REM    build.bat clean        Clean all build artifacts
REM
REM  Output: dist\Star-Learn-Setup-{version}.exe
REM ============================================================================

setlocal enabledelayedexpansion

pushd "%~dp0\.."
set "ROOT=%CD%"
set "DIST=%ROOT%\dist"
set "PACKAGING=%ROOT%\packaging"
set "PYTHON_DIR=%PACKAGING%\python"
set "PY_EXE=%PYTHON_DIR%\python.exe"

set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

set "STEP=%~1"
if "%STEP%"=="" set "STEP=full"

echo.
echo ========================================
echo   Star-Learn Installer Builder
echo   Root : %ROOT%
echo   Step : %STEP%
echo ========================================
echo.

REM ── clean ──────────────────────────────────────────────────────────
if /i "%STEP%"=="clean" goto :clean

REM ── full / stage ───────────────────────────────────────────────────
if /i "%STEP%"=="stage" goto :stage
if /i "%STEP%"=="full" goto :assets

REM ── python ─────────────────────────────────────────────────────────
if /i "%STEP%"=="python" goto :fetch_python

REM ── deps ───────────────────────────────────────────────────────────
if /i "%STEP%"=="deps" goto :install_deps

REM ── installer ──────────────────────────────────────────────────────
if /i "%STEP%"=="installer" goto :compile_installer

echo [ERROR] Unknown step: %STEP%
echo Valid: full, stage, python, deps, installer, clean
exit /b 1

REM ====================================================================
REM  Assets generation
REM ====================================================================
:assets
echo [1/5] Generating installer assets (icon, BMPs, LICENSE)...
python "%PACKAGING%\assets\generate_assets.py"
if errorlevel 1 (
    echo [ERROR] Asset generation failed.
    exit /b 1
)

REM ====================================================================
REM  Stage payload
REM ====================================================================
:stage
echo [2/5] Staging app payload...
python "%PACKAGING%\stage_payload.py"
if errorlevel 1 (
    echo [ERROR] Payload staging failed.
    exit /b 1
)

if /i "%STEP%"=="stage" goto :done

REM ====================================================================
REM  Fetch embedded Python
REM ====================================================================
:fetch_python
echo [3/5] Fetching embedded Python 3.11.9...
call "%PACKAGING%\fetch_python.bat"
if errorlevel 1 (
    echo [ERROR] Python fetch failed.
    exit /b 1
)

echo [3/5] Patching _pth for pip (uncomment "import site")...
"%PY_EXE%" -c "import re, pathlib; p = next(pathlib.Path(r'%PYTHON_DIR%').glob('python*._pth'), None); t = p.read_text() if p else ''; p.write_text(re.sub(r'^#\s*import\s+site', 'import site', t, flags=re.M)) if p and '#import site' in t else None"
if errorlevel 1 (
    echo [WARN] Could not patch _pth file. Pip may not work.
)

if /i "%STEP%"=="python" goto :done

REM ====================================================================
REM  Install pip dependencies into embedded Python
REM ====================================================================
:install_deps
if not exist "%PY_EXE%" (
    echo [ERROR] %PY_EXE% not found. Run "build.bat python" first.
    exit /b 1
)
echo [4/5] Installing pip packages...
"%PY_EXE%" -m pip install --no-warn-script-location --disable-pip-version-check -r "%ROOT%\requirements.txt"
if errorlevel 1 (
    echo [ERROR] pip install failed.
    exit /b 1
)

REM Write lock file for reference
echo [4/5] Writing requirements lock file...
"%PY_EXE%" -m pip freeze > "%PACKAGING%\requirements.lock.txt"
echo        → packaging\requirements.lock.txt

if /i "%STEP%"=="deps" goto :done

REM ====================================================================
REM  Compile installer with Inno Setup
REM ====================================================================
:compile_installer
if not exist "%ISCC%" (
    echo [ERROR] Inno Setup compiler not found at: "%ISCC%"
    echo.
    echo Please install Inno Setup 6 from:
    echo   https://jrsoftware.org/isinfo.php
    echo.
    echo If installed elsewhere, set ISCC environment variable:
    echo   set ISCC=C:\path\to\ISCC.exe
    exit /b 1
)

echo [5/5] Compiling installer with Inno Setup...
if not exist "%DIST%" mkdir "%DIST%"

"%ISCC%" /Qp "%PACKAGING%\installer.iss"
if errorlevel 1 (
    echo [ERROR] Inno Setup compilation failed.
    exit /b 1
)

echo.
echo ========================================
echo   BUILD SUCCESSFUL
echo ========================================
echo.
dir "%DIST%\Star-Learn-Setup-*.exe" 2>nul
echo.
goto :done

REM ====================================================================
REM  Clean
REM ====================================================================
:clean
echo Cleaning build artifacts...

if exist "%DIST%" (
    echo   Removing dist\
    rmdir /s /q "%DIST%"
)
if exist "%PACKAGING%\app_payload" (
    echo   Removing packaging\app_payload\
    rmdir /s /q "%PACKAGING%\app_payload"
)
if exist "%PACKAGING%\python" (
    echo   Removing packaging\python\
    rmdir /s /q "%PACKAGING%\python"
)
if exist "%PACKAGING%\requirements.lock.txt" (
    echo   Removing packaging\requirements.lock.txt
    del /f /q "%PACKAGING%\requirements.lock.txt"
)
if exist "%PACKAGING%\assets\icon.ico" (
    echo   Removing generated assets
    del /f /q "%PACKAGING%\assets\icon.ico" 2>nul
    del /f /q "%PACKAGING%\assets\installer-*.bmp" 2>nul
    del /f /q "%PACKAGING%\assets\LICENSE.txt" 2>nul
)
echo Clean done.

REM ====================================================================
REM  Done
REM ====================================================================
:done
popd
endlocal
exit /b 0
