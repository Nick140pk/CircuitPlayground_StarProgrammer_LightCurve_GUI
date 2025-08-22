@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

:: ─────────────────────────────────────────────────────────────
:: App settings (edit these if your file name ever changes)
set "MAIN=StarProgrammer_LightCurve_GUI.py"
set "LAUNCHER=Run_StarProgrammer.cmd"
set "SHORTCUT_NAME=Star Programmer.lnk"

:: Hard-coded dependency list (no requirements.txt needed)
:: You can pin versions if you want, e.g. numpy==1.24.4 matplotlib==3.8.4
set "PACKAGES=pyqt5 pyserial matplotlib numpy"
:: ─────────────────────────────────────────────────────────────

echo:
echo === One-time setup: creating local Python environment ===
echo Location: %CD%
echo:

:: Find Python 3
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [!] Python 3 not found.
  echo     Install from https://www.python.org/downloads/windows/  (check "Add Python to PATH")
  echo     Then run this file again.
  pause
  exit /b 1
)

:: Create virtual environment
if not exist ".venv" (
  echo [+] Creating virtual environment .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [x] Failed to create virtual environment.
    pause & exit /b 1
  )
) else (
  echo [+] Using existing .venv
)

:: Upgrade pip/setuptools/wheel
echo [+] Upgrading pip / setuptools / wheel ...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
  echo [x] Failed to upgrade pip / build tools.
  pause & exit /b 1
)

:: Install hard-coded packages
echo [+] Installing packages: %PACKAGES%
call ".venv\Scripts\python.exe" -m pip install %PACKAGES%
if errorlevel 1 (
  echo [x] Dependency install failed.
  echo     If you're on a restricted network, try again on a different connection.
  pause & exit /b 1
)

:: Create the double-click launcher
echo [+] Writing launcher: %LAUNCHER%
> "%LAUNCHER%" (
  echo @echo off
  echo setlocal
  echo cd /d "%%~dp0"
  echo if not exist ".venv\Scripts\pythonw.exe" call "%%~dp0install-deps.bat"
  echo call ".venv\Scripts\pythonw.exe" "%%~dp0%MAIN%" %%*
)

:: Optional: create a Desktop shortcut (best effort)
echo [+] Creating desktop shortcut (optional) ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$P = (Resolve-Path '%CD%').Path;" ^
  "$W = New-Object -ComObject WScript.Shell;" ^
  "$D = [Environment]::GetFolderPath('Desktop');" ^
  "$S = $W.CreateShortcut(Join-Path $D '%SHORTCUT_NAME%');" ^
  "$S.TargetPath = Join-Path $P '%LAUNCHER%';" ^
  "$S.WorkingDirectory = $P;" ^
  "if (Test-Path (Join-Path $P 'app.ico')) { $S.IconLocation = (Join-Path $P 'app.ico'); }" ^
  "$S.Save()" 2>nul

echo:
echo ✅ Setup complete.
echo 👉 Double-click %LAUNCHER% (or use the desktop shortcut) to launch the app.
echo:
pause
