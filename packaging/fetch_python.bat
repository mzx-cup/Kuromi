@echo off
REM Download CPython 3.11.9 embeddable zip + get-pip.py into packaging\python\
REM Idempotent: skips if already present.
setlocal enabledelayedexpansion

pushd "%~dp0\.."
set "ROOT=%CD%"
set "PY_DIR=%ROOT%\packaging\python"
set "GET_PIP=%PY_DIR%\get-pip.py"
set "EMBED_ZIP=%PY_DIR%\python-3.11.9-embed-amd64.zip"
set "EXTRACTED=%PY_DIR%\python.exe"

set "PY_VERSION=3.11.9"
set "PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-embed-amd64.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"

if not exist "%PY_DIR%" mkdir "%PY_DIR%"

if exist "%EXTRACTED%" (
    echo [fetch_python] Embedded Python already extracted at "%EXTRACTED%". Skipping download.
    goto :verify_pip
)

echo [fetch_python] Downloading Python %PY_VERSION% embeddable...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%EMBED_ZIP%' -UseBasicParsing -ErrorAction Stop; 'OK' } catch { exit 1 }"
if errorlevel 1 (
    echo [fetch_python] ERROR: Python download failed. Check network.
    exit /b 1
)

echo [fetch_python] Extracting...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Expand-Archive -Path '%EMBED_ZIP%' -DestinationPath '%PY_DIR%' -Force"
if errorlevel 1 (
    echo [fetch_python] ERROR: extraction failed.
    exit /b 1
)
del /f /q "%EMBED_ZIP%"

:verify_pip
if exist "%PY_DIR%\Scripts\pip.exe" (
    echo [fetch_python] pip already bootstrapped. Skipping get-pip.
    goto :done
)

echo [fetch_python] Downloading get-pip.py...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "try { Invoke-WebRequest -Uri '%GET_PIP_URL%' -OutFile '%GET_PIP%' -UseBasicParsing -ErrorAction Stop; 'OK' } catch { exit 1 }"
if errorlevel 1 (
    echo [fetch_python] ERROR: get-pip.py download failed.
    exit /b 1
)

echo [fetch_python] Bootstrapping pip...
"%EXTRACTED%" "%GET_PIP%"

:done
echo [fetch_python] Done. Python at: %EXTRACTED%
popd
endlocal
