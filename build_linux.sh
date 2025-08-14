#!/usr/bin/env bash
set -euo pipefail

APP_NAME="StarProgrammer"
ENTRY="StarProgrammer_LightCurve_GUI.py"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
pip install pyinstaller

pyinstaller \
  --noconfirm \
  --windowed \
  --name "$APP_NAME" \
  --hidden-import matplotlib.backends.backend_qt5agg \
  --hidden-import matplotlib.backends.backend_qtagg \
  --collect-all matplotlib \
  --collect-all PyQt5 \
  "$ENTRY"

OUTDIR="dist/$APP_NAME"
TAR="$APP_NAME"_Linux_x64.tar.gz
tar -czf "$TAR" -C "$OUTDIR" .
echo "Built: $TAR"
