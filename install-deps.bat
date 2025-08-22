@echo off
setlocal ENABLEDELAYEDEXPANSION

:: always work from this folder
cd /d "%~dp0"

echo.
echo === Star Programmer + Light-Curve GUI — Windows Setup ===
echo This will create a local .venv in: %CD%
echo.

:: Find Python 3 (prefer the py launcher)
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo Python 3 not found.
  echo Please install from https://www.python.org/downloads/windows/ (check "Add Python to PATH"), then run this again.
  pause
  exit /b 1
)

:: Create venv if missing
if not exist ".venv" (
  echo Creating virtual environment .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo Failed to create virtual environment.
    pause & exit /b 1
  )
)

echo Upgrading pip/setuptools/wheel ...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel

:: Install deps
if exist "requirements.txt" (
  echo Installing dependencies from requirements.txt ...
  call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
) else (
  echo requirements.txt not found. Installing common deps ...
  call ".venv\Scripts\python.exe" -m pip install pyqt5 pyserial matplotlib
)

:: Write the launcher that users will double-click
> "Run_StarProgrammer.cmd" (
  echo @echo off
  echo setlocal
  echo cd /d "%%~dp0"
  echo if not exist ".venv\Scripts\pythonw.exe" (
  echo ^  echo Setting up environment ...
  echo ^  call "%%~dp0install-deps.bat"
  echo )
  echo call ".venv\Scripts\pythonw.exe" "StarProgrammer_LightCurve_GUI.py" %%*
)

:: Optional: create a Desktop shortcut (ignore errors if PowerShell/COM is restricted)
for /f "usebackq tokens=2,*" %%A in (`
  reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Desktop 2^>nul ^| find "Desktop"
`) do set DESK=%%B
if not defined DESK set "DESK=%USERPROFILE%\Desktop"

powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut((Resolve-Path '%DESK%').Path + '\Star Programmer.lnk');" ^
  "$s.TargetPath='%(~dp0)Run_StarProgrammer.cmd'.Replace('%','%%');" ^
  "$s.WorkingDirectory='%(~dp0)'.Replace('%','%%');" ^
  "$s.IconLocation='%(~dp0)app.ico'.Replace('%','%%');" ^
  "$s.Save()" 2>nul

echo.
echo ✅ Setup complete.
echo 👉 Double-click Run_StarProgrammer.cmd (or the Desktop shortcut) to launch.
pause
