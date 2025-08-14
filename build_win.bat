@echo off
setlocal ENABLEDELAYEDEXPANSION

REM =========================================================
REM Star Programmer + Light-Curve Plotter — Windows Runner
REM - Creates a venv, installs deps, runs the app
REM - Works on Windows 10 and 11
REM =========================================================

title Star Programmer Setup & Run

REM --- Paths ---
set "BASEDIR=%~dp0"
cd /d "%BASEDIR%"
set "VENV_DIR=%BASEDIR%.venv"
set "ENTRY=StarProgrammer_LightCurve_GUI.py"
set "REQ=requirements.txt"

echo.
echo =========================================================
echo   Star Programmer + Light-Curve Plotter — Setup/Run
echo =========================================================
echo Location: %BASEDIR%
echo.

REM --- Sanity: script next to program? ---
if not exist "%ENTRY%" (
  echo [X] Could not find "%ENTRY%" in: %BASEDIR%
  echo     Please place this .bat in the same folder as %ENTRY%.
  echo.
  pause
  exit /b 1
)

REM --- Find Python (prefer py launcher for 3.11) ---
set "PYCMD="

where py >nul 2>&1
if "%ERRORLEVEL%"=="0" (
  for /f "usebackq delims=" %%v in (`py -3.11 -c "print('OK')" 2^>NUL`) do set "PYCMD=py -3.11"
)

if not defined PYCMD (
  where python >nul 2>&1
  if "%ERRORLEVEL%"=="0" (
    set "PYCMD=python"
  )
)

if not defined PYCMD (
  echo [X] Python not found.
  echo     Please install Python 3.11 (64-bit) from https://www.python.org
  echo     and check "Add Python to PATH" during install.
  echo.
  pause
  exit /b 1
)

REM --- Show Python version ---
echo [*] Using Python command: %PYCMD%
%PYCMD% -c "import sys; print('Python', sys.version)" || (
  echo [!] Warning: Could not query Python version. Continuing.
)

REM --- Create venv if missing ---
if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [*] Creating virtual environment at: %VENV_DIR%
  %PYCMD% -m venv "%VENV_DIR%" || (
    echo [X] Failed to create virtual environment.
    echo.
    pause
    exit /b 1
  )
) else (
  echo [*] Reusing existing virtual environment.
)

REM --- Upgrade pip / wheel / setuptools ---
echo [*] Upgrading pip, wheel, setuptools...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip wheel setuptools || (
  echo [X] Failed to upgrade pip/wheel/setuptools.
  echo.
  pause
  exit /b 1
)

REM --- Install dependencies (requirements.txt if present, else pins) ---
if exist "%REQ%" (
  echo [*] Installing dependencies from %REQ% ...
  "%VENV_DIR%\Scripts\python.exe" -m pip install -r "%REQ%" || (
    echo [X] Dependency install failed (requirements.txt).
    echo.
    pause
    exit /b 1
  )
) else (
  echo [!] No requirements.txt found — installing safe pinned defaults...
  "%VENV_DIR%\Scripts\python.exe" -m pip install ^
    "numpy==1.24.4" "scipy==1.15.3" "matplotlib==3.8.4" "PyQt5>=5.15" pyserial || (
    echo [X] Dependency install failed (pinned set).
    echo.
    pause
    exit /b 1
  )
)

echo.
echo [*] Dependencies ready. Launching the app...

REM --- Try normal launch first ---
set "QT_OPENGL="
start "" /wait "%VENV_DIR%\Scripts\python.exe" "%BASEDIR%%ENTRY%"
set "EXITCODE=%ERRORLEVEL%"

if "%EXITCODE%"=="0" (
  echo.
  echo [✓] App closed without error. You can run this .bat any time to start it again.
  echo.
  pause
  exit /b 0
)

echo.
echo [!] The app returned exit code %EXITCODE%.
echo     Trying a compatibility mode (software rendering)...

REM --- Retry with software rendering (helps older/quirky GPUs) ---
set "QT_OPENGL=software"
start "" /wait "%VENV_DIR%\Scripts\python.exe" -c "import os; os.environ['QT_OPENGL']='software'; import runpy; runpy.run_path(r'%BASEDIR%%ENTRY%')"
set "EXITCODE=%ERRORLEVEL%"

if "%EXITCODE%"=="0" (
  echo.
  echo [✓] App ran successfully with software rendering.
  echo     If you want to always use this mode, set QT_OPENGL=software before running.
  echo.
  pause
  exit /b 0
)

echo.
echo [X] The app still failed to run. Exit code: %EXITCODE%
echo.
echo Quick tips:
echo  - If Windows shows a SmartScreen warning: click "More info" -> "Run anyway".
echo  - Ensure GPU drivers are up to date.
echo  - If connecting hardware: install the correct USB driver (CH340/CP210x/FTDI).
echo  - If serial access fails: close other serial programs and re-try.
echo.
pause
exit /b %EXITCODE%
