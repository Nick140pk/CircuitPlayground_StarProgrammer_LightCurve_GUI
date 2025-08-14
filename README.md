# Star Programmer + Light-Curve Plotter

A cross-platform PyQt5 GUI tool for programming star RGB brightness and simulating planetary transits in real-time.  
Plots live light-curve data from a connected CircuitPython device over serial.

## Features
- Control star color (RGB) and brightness
- Configure up to 5 planets (dip factor, orbit period, transit duration, phase offset)
- Live light-curve plotting with matplotlib
- Save/load/reset device configuration
- Works on Linux, Windows, and macOS

## Installation (Developer Mode)

Clone and install dependencies:
```bash
git clone https://github.com/YOUR-USERNAME/StarProgrammer-LightCurve-GUI.git
cd StarProgrammer-LightCurve-GUI
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
