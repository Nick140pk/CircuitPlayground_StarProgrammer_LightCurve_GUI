@echo off
setlocal

echo ================================================
echo   Installing StarProgrammer Dependencies
echo ================================================

REM --- Find Python (prefer py launcher for 3.11) ---
set "PYCMD="
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set "PYCMD=py -3.11"
) else (
  where python >nul 2>&1
  if %ERRORLEVEL%==0 (
    set "PYCMD=python"
  )
)

if not defined PYCMD (
  echo [X] Python not found. Install Python 3.11 (64-bit) from https://www.python.org
  pause
  exit /b 1
)

echo [*] Using Python: %PYCMD%

REM --- Create venv if missing ---
if not exist .venv\Scripts\python.exe (
  echo [*] Creating virtual environment...
  %PYCMD% -m venv .venv
)

REM --- Upgrade pip ---
echo [*] Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip wheel setuptools

REM --- Install required packages ---
echo [*] Installing dependencies...
.venv\Scripts\python.exe -m pip install ^
  "numpy==1.24.4" ^
  "scipy==1.15.3" ^
  "matplotlib==3.8.4" ^
  "PyQt5>=5.15" ^
  pyserial

if %ERRORLEVEL%==0 (
  echo.
  echo [✓] Dependencies installed successfully!
  echo To activate the environment, run:
  echo    .venv\Scripts\activate
  echo Then start your program with:
  echo    python StarProgrammer_LightCurve_GUI.py
) else (
  echo [X] Something went wrong during installation.
)

echo.
pause
