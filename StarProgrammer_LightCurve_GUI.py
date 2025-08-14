#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Star Programmer + Light-Curve Plotter (Single App) - Fixed & Optimized
- Connect to your CircuitPython device over serial
- Program star RGB + brightness
- Program up to 5 planets (name, dip, orbit s, transit s, phase ms)
- Read live light-curve values from the device and plot them in real time

Dependencies:
    First fix NumPy/scipy compatibility if needed:
    pip install "numpy>=1.19,<1.25" scipy --force-reinstall
    pip install pyqt5 pyserial matplotlib

Run:
    python StarProgrammer_LightCurve_GUI.py
"""
import sys
import time
import re
import logging
from collections import deque
from typing import List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check Python version
if sys.version_info < (3, 7):
    raise SystemExit("Python 3.7+ required")

# Import PyQt5 components
try:
    from PyQt5 import QtCore, QtGui, QtWidgets
    from PyQt5.QtCore import QTimer, QObject, pyqtSignal
    from PyQt5.QtWidgets import *
    from PyQt5.QtGui import QColor, QPalette
    from PyQt5.QtCore import Qt
except ImportError as e:
    raise SystemExit(f"PyQt5 is required. Install with: pip install pyqt5\nError: {e}")

# Import serial communication
try:
    import serial
    import serial.tools.list_ports as list_ports
except ImportError as e:
    raise SystemExit(f"pyserial is required. Install with: pip install pyserial\nError: {e}")

# Import matplotlib with error handling
try:
    import matplotlib
    matplotlib.use('Qt5Agg')  # Set backend before importing pyplot
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
except ImportError as e:
    raise SystemExit(f"matplotlib is required. Install with: pip install matplotlib\nError: {e}")
except Exception as e:
    error_msg = str(e)
    if "ARRAY_API not found" in error_msg or "numpy" in error_msg.lower():
        raise SystemExit(
            "NumPy/matplotlib compatibility issue detected.\n"
            "Try fixing with:\n"
            "pip install 'numpy>=1.19,<1.25' scipy matplotlib --force-reinstall\n"
            "Then restart the application."
        )
    else:
        raise SystemExit(f"matplotlib import failed: {e}")

# Constants
MAX_PLANETS = 5
DEFAULT_BAUD = 115200
POLL_INTERVAL_MS = 50
UI_UPDATE_INTERVAL_MS = 100


class SerialManager(QObject):
    """Enhanced serial communication manager"""
    line_received = pyqtSignal(str)
    status_changed = pyqtSignal(bool, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, baud=DEFAULT_BAUD, parent=None):
        super().__init__(parent)
        self._ser = None
        self.baud = baud
        self._buf = bytearray()
        self._last_port = None

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(POLL_INTERVAL_MS)
        self.poll_timer.timeout.connect(self._poll_serial)

    @staticmethod
    def list_serial_ports():
        """Get list of available serial ports"""
        try:
            ports = list(list_ports.comports())
            names = [p.device for p in ports]
            # Prioritize common Arduino/CircuitPython port names
            def port_priority(port_name):
                port_lower = port_name.lower()
                if any(x in port_lower for x in ['acm', 'usb']):
                    return 0
                elif 'com' in port_lower:
                    return 1
                else:
                    return 2
            names.sort(key=lambda n: (port_priority(n), n))
            return names
        except Exception as e:
            logger.error(f"Error listing serial ports: {e}")
            return []

    def connect(self, port_name):
        """Connect to serial port"""
        self.disconnect()
        try:
            logger.info(f"Connecting to {port_name} at {self.baud} baud")
            self._ser = serial.Serial(
                port=port_name, 
                baudrate=self.baud, 
                timeout=0,
                write_timeout=2.0
            )
            self._last_port = port_name
            self.poll_timer.start()
            self.status_changed.emit(True, f"Connected: {port_name} @ {self.baud}")
            logger.info(f"Successfully connected to {port_name}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._ser = None
            self.status_changed.emit(False, f"Connection failed: {str(e)}")
            return False

    def disconnect(self):
        """Safely disconnect from serial port"""
        self.poll_timer.stop()
        if self._ser:
            try:
                logger.info("Disconnecting from serial port")
                self._ser.close()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
        self._ser = None
        self.status_changed.emit(False, "DISCONNECTED")

    def is_connected(self):
        """Check if serial connection is active"""
        return self._ser is not None and self._ser.is_open

    def send_line(self, text):
        """Send line with error handling"""
        if not self.is_connected():
            raise RuntimeError("Serial not connected")
        
        if not text.endswith("\n"):
            text = text + "\n"
        
        try:
            self._ser.write(text.encode("utf-8"))
            self._ser.flush()
            logger.debug(f"Sent: {text.strip()}")
        except Exception as e:
            logger.error(f"Error sending data: {e}")
            raise RuntimeError(f"Serial write failed: {e}")

    def _poll_serial(self):
        """Poll for incoming serial data"""
        if not self.is_connected():
            return

        try:
            data = self._ser.read(8192)
            if not data:
                return

            self._buf.extend(data)
            
            while b"\n" in self._buf:
                line, _, rest = self._buf.partition(b"\n")
                self._buf = bytearray(rest)
                
                try:
                    decoded_line = line.decode("utf-8", errors="replace").strip()
                    if decoded_line:
                        self.line_received.emit(decoded_line)
                except Exception as e:
                    logger.warning(f"Error decoding line: {e}")

        except Exception as e:
            logger.error(f"Serial polling error: {e}")
            self.error_occurred.emit(f"Serial error: {e}")
            self.disconnect()


class MplCanvas(FigureCanvas):
    """Matplotlib canvas for real-time plotting"""
    def __init__(self, width=8, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.fig.tight_layout()


class PlanetTable(QTableWidget):
    """Planet configuration table"""
    HEADERS = ["Name", "Dip (0-1)", "Orbit (s)", "Transit (s)", "Phase (ms)"]

    def __init__(self, parent=None):
        super().__init__(MAX_PLANETS, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        
        # Initialize with default values
        for r in range(MAX_PLANETS):
            for c in range(len(self.HEADERS)):
                self.setItem(r, c, QTableWidgetItem(""))
            
            # Set defaults
            self.item(r, 1).setText("0.1")   # 10% dip
            self.item(r, 2).setText("10.0")  # 10 second orbit
            self.item(r, 3).setText("2.0")   # 2 second transit
            self.item(r, 4).setText("0")     # no phase offset

    def get_planet_rows(self):
        """Extract and validate planet data"""
        rows = []
        for r in range(MAX_PLANETS):
            name_item = self.item(r, 0)
            name = name_item.text().strip() if name_item else ""
            if not name:
                continue
                
            try:
                dip = float(self.item(r, 1).text())
                orbit_s = float(self.item(r, 2).text())
                transit_s = float(self.item(r, 3).text())
                phase_ms = int(float(self.item(r, 4).text()))
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Row {r+1}: Invalid numeric value - {e}")
            
            # Validation
            if not (0.0 <= dip <= 1.0):
                raise ValueError(f"Row {r+1}: Dip must be between 0.0 and 1.0")
            if orbit_s <= 0 or transit_s <= 0:
                raise ValueError(f"Row {r+1}: Orbit and transit must be > 0")
            if transit_s >= orbit_s:
                raise ValueError(f"Row {r+1}: Transit duration must be < orbit period")
            
            rows.append((name[:11], dip, orbit_s, transit_s, phase_ms))
        
        return rows


class ColorSwatch(QFrame):
    """Color picker widget"""
    colorChanged = pyqtSignal(QColor)

    def __init__(self, initial=None, parent=None):
        super().__init__(parent)
        if initial is None:
            initial = QColor(255, 200, 100)
        self._color = initial
        self.setFixedSize(40, 28)
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.setAutoFillBackground(True)
        self.setToolTip("Click to change star color")
        self._update_appearance()

    def _update_appearance(self):
        """Update visual appearance"""
        palette = self.palette()
        palette.setColor(QPalette.Window, self._color)
        self.setPalette(palette)

    def mousePressEvent(self, event):
        """Handle color picker"""
        if event.button() == Qt.LeftButton:
            color = QColorDialog.getColor(self._color, self, "Choose Star Color")
            if color.isValid():
                self._color = color
                self._update_appearance()
                self.colorChanged.emit(color)

    def color(self):
        return self._color


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Star Programmer + Light-Curve Plotter v2.0")
        self.resize(1100, 800)

        # Initialize serial manager
        self.serial = SerialManager(baud=DEFAULT_BAUD, parent=self)
        self.serial.line_received.connect(self.on_serial_line)
        self.serial.status_changed.connect(self.on_status_changed)
        self.serial.error_occurred.connect(self.on_serial_error)

        # Plot data
        self.seconds_window = 30.0
        self.x_times = deque(maxlen=1000)
        self.y_vals = deque(maxlen=1000)
        self.t0 = time.monotonic()

        self._setup_ui()
        self._setup_plot()
        self._setup_timers()
        self.refresh_ports(auto_select=True)

    def _setup_ui(self):
        """Set up user interface"""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)

        # Connection controls
        layout.addWidget(QLabel("Port:"), 0, 0)
        self.port_combo = QComboBox(self)
        layout.addWidget(self.port_combo, 0, 1)
        
        self.refresh_btn = QPushButton("Refresh", self)
        self.refresh_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(self.refresh_btn, 0, 2)
        
        self.connect_btn = QPushButton("Connect", self)
        self.connect_btn.clicked.connect(self.toggle_connect)
        layout.addWidget(self.connect_btn, 0, 3)
        
        layout.addWidget(QLabel("Window (s):"), 0, 4)
        self.window_spin = QDoubleSpinBox(self)
        self.window_spin.setRange(5.0, 300.0)
        self.window_spin.setValue(30.0)
        self.window_spin.valueChanged.connect(self.set_window_seconds)
        layout.addWidget(self.window_spin, 0, 5)
        
        self.status_label = QLabel("DISCONNECTED", self)
        layout.addWidget(self.status_label, 0, 6)

        # Star controls
        star_group = QGroupBox("Star Configuration", self)
        star_layout = QHBoxLayout(star_group)
        
        star_layout.addWidget(QLabel("Color:"))
        self.color_swatch = ColorSwatch(parent=self)
        self.color_swatch.colorChanged.connect(self.on_color_changed)
        star_layout.addWidget(self.color_swatch)
        
        star_layout.addWidget(QLabel("Brightness:"))
        self.brightness_slider = QSlider(Qt.Horizontal, self)
        self.brightness_slider.setRange(0, 255)
        self.brightness_slider.setValue(200)
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)
        star_layout.addWidget(self.brightness_slider, 1)
        
        self.brightness_spin = QSpinBox(self)
        self.brightness_spin.setRange(0, 255)
        self.brightness_spin.setValue(200)
        self.brightness_spin.valueChanged.connect(self.brightness_slider.setValue)
        star_layout.addWidget(self.brightness_spin)
        
        self.send_star_btn = QPushButton("Send Star Config", self)
        self.send_star_btn.clicked.connect(self.send_star_config)
        star_layout.addWidget(self.send_star_btn)
        
        layout.addWidget(star_group, 1, 0, 1, 7)

        # Planet table
        self.table = PlanetTable(self)
        layout.addWidget(self.table, 2, 0, 1, 7)

        # Action buttons
        buttons = [
            ("Send Planets", self.send_planets),
            ("Set Count", self.send_planet_count),
            ("Save", lambda: self._send_command("SAVE")),
            ("Load", lambda: self._send_command("LOAD")),
            ("Reset", self.reset_device),
            ("List", lambda: self._send_command("LIST"))
        ]
        
        for col, (text, handler) in enumerate(buttons):
            btn = QPushButton(text, self)
            btn.clicked.connect(handler)
            layout.addWidget(btn, 3, col)

        # Plot canvas
        self.canvas = MplCanvas(width=10, height=4)
        layout.addWidget(self.canvas, 4, 0, 1, 7)

        # Log
        self.log = QPlainTextEdit(self)
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setMaximumHeight(150)
        layout.addWidget(self.log, 5, 0, 1, 7)

    def _setup_plot(self):
        """Configure the plot"""
        self.line, = self.canvas.ax.plot([], [], 'b-', linewidth=1.5)
        self.canvas.ax.set_xlabel("Time (seconds)")
        self.canvas.ax.set_ylabel("Brightness")
        self.canvas.ax.set_ylim(0, 260)
        self.canvas.ax.grid(True, alpha=0.3)
        self.canvas.ax.set_title("Live Light Curve")
        self.canvas.fig.tight_layout()

    def _setup_timers(self):
        """Set up update timers"""
        self.ui_timer = QTimer(self)
        self.ui_timer.setInterval(UI_UPDATE_INTERVAL_MS)
        self.ui_timer.timeout.connect(self.update_plot)
        self.ui_timer.start()

    # Event handlers
    def on_brightness_changed(self, value):
        self.brightness_spin.setValue(value)

    def on_color_changed(self, color):
        logger.info(f"Color changed to RGB({color.red()}, {color.green()}, {color.blue()})")

    def on_status_changed(self, connected, message):
        self.status_label.setText(message)
        self.connect_btn.setText("Disconnect" if connected else "Connect")

    def on_serial_error(self, error_message):
        QMessageBox.warning(self, "Serial Error", error_message)

    def on_serial_line(self, line):
        """Process incoming serial data"""
        # Try "Total: <value>" format
        total_match = re.match(r"^Total\s*:\s*([0-9]+(?:\.[0-9]+)?)", line, re.IGNORECASE)
        if total_match:
            try:
                value = float(total_match.group(1))
                self.append_data_point(value)
                return
            except ValueError:
                pass
        
        # Try plain number
        try:
            value = float(line.strip())
            self.append_data_point(value)
            return
        except ValueError:
            pass
        
        # Log other messages
        self.log.appendPlainText(line)

    def append_data_point(self, value):
        """Add data point to plot"""
        current_time = time.monotonic() - self.t0
        self.x_times.append(current_time)
        self.y_vals.append(value)
        
        # Trim old data
        cutoff_time = current_time - self.seconds_window
        while self.x_times and self.x_times[0] < cutoff_time:
            self.x_times.popleft()
            self.y_vals.popleft()

    def update_plot(self):
        """Update real-time plot"""
        if not self.x_times:
            return
            
        xs = list(self.x_times)
        ys = list(self.y_vals)
        
        self.line.set_data(xs, ys)
        
        if xs:
            latest_time = xs[-1]
            x_min = max(0.0, latest_time - self.seconds_window)
            x_max = max(x_min + 1.0, latest_time)
            self.canvas.ax.set_xlim(x_min, x_max)
            
            if ys:
                y_min = min(0, min(ys) - 10)
                y_max = max(260, max(ys) + 10)
                self.canvas.ax.set_ylim(y_min, y_max)
        
        self.canvas.draw_idle()

    # UI Actions
    def set_window_seconds(self, seconds):
        self.seconds_window = float(seconds)

    def refresh_ports(self, auto_select=False):
        self.port_combo.clear()
        ports = self.serial.list_serial_ports()
        
        if not ports:
            self.port_combo.addItem("(no ports found)")
            return
            
        self.port_combo.addItems(ports)
        if auto_select and ports:
            self.port_combo.setCurrentIndex(0)

    def toggle_connect(self):
        if self.serial.is_connected():
            self.serial.disconnect()
        else:
            port = self.port_combo.currentText().strip()
            if not port or port == "(no ports found)":
                QMessageBox.warning(self, "No Port", "Please select a valid serial port.")
                return
                
            if self.serial.connect(port):
                self.t0 = time.monotonic()
                self.x_times.clear()
                self.y_vals.clear()
                self.log.clear()
                
                try:
                    self.serial.send_line("HELP")
                except Exception:
                    pass

    def send_star_config(self):
        if not self._check_connection():
            return
            
        color = self.color_swatch.color()
        brightness = self.brightness_spin.value()
        command = f"SETSTAR:{color.red()},{color.green()},{color.blue()},{brightness}"
        
        try:
            self.serial.send_line(command)
            time.sleep(0.1)
        except Exception as e:
            QMessageBox.critical(self, "Send Error", f"Failed to send star config:\n{e}")

    def send_planet_count(self):
        if not self._check_connection():
            return
            
        try:
            planets = self.table.get_planet_rows()
            count = min(len(planets), MAX_PLANETS)
            self.serial.send_line(f"SETNUM:{count}")
            time.sleep(0.15)
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Send Error", f"Failed to send count:\n{e}")

    def send_planets(self):
        if not self._check_connection():
            return
            
        try:
            planets = self.table.get_planet_rows()
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", str(e))
            return
            
        if not planets:
            QMessageBox.information(self, "No Planets", "No planets configured.")
            return

        try:
            # Send count first
            count = min(len(planets), MAX_PLANETS)
            self.serial.send_line(f"SETNUM:{count}")
            time.sleep(0.15)
            
            # Send each planet
            for name, dip, orbit_s, transit_s, phase_ms in planets[:MAX_PLANETS]:
                orbit_ms = int(orbit_s * 1000.0)
                transit_ms = int(transit_s * 1000.0)
                command = f"{name},{dip:.6f},{orbit_ms},{transit_ms},{phase_ms}"
                self.serial.send_line(command)
                time.sleep(0.08)
            
            QMessageBox.information(self, "Success", f"Sent {len(planets)} planet(s) to device.")
            
        except Exception as e:
            QMessageBox.critical(self, "Send Error", f"Failed to send planets:\n{e}")

    def reset_device(self):
        if not self._check_connection():
            return
            
        reply = QMessageBox.question(
            self, "Reset Device", 
            "Reset device to defaults?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._send_command("RESETCFG")

    def _send_command(self, command):
        if not self._check_connection():
            return
            
        try:
            self.serial.send_line(command)
            time.sleep(0.2)
            
            if command == "SAVE":
                QMessageBox.information(self, "Saved", "Configuration saved.")
            elif command == "LOAD":
                QMessageBox.information(self, "Loaded", "Configuration loaded.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send {command}:\n{e}")

    def _check_connection(self):
        if not self.serial.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to a device first.")
            return False
        return True

    def closeEvent(self, event):
        self.serial.disconnect()
        event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Star Programmer")
    app.setApplicationVersion("2.0")
    
    try:
        window = MainWindow()
        window.show()
        logger.info("Application started successfully")
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        QMessageBox.critical(None, "Startup Error", f"Failed to start application:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
