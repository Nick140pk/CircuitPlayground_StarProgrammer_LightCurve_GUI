@echo off
setlocal

set APP_NAME=StarProgrammer
set ENTRY=StarProgrammer_LightCurve_GUI.py
set ICON=app.ico

if not exist .venv (
  py -3.11 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate

python -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
pip install pyinstaller

pyinstaller ^
  --noconfirm ^
  --windowed ^
  --name %APP_NAME% ^
  --icon %ICON% ^
  --hidden-import matplotlib.backends.backend_qt5agg ^
  --hidden-import matplotlib.backends.backend_qtagg ^
  --collect-all matplotlib ^
  --collect-all PyQt5 ^
  --version-file version_info.txt ^
  %ENTRY%

set OUTDIR=dist\%APP_NAME%
set ZIPNAME=%APP_NAME%_Windows_x64.zip
IF EXIST "%ZIPNAME%" DEL /F /Q "%ZIPNAME%"
powershell -NoProfile -Command "Compress-Archive -Path '%OUTDIR%\*' -DestinationPath '%ZIPNAME%'"
echo Built: %ZIPNAME%
