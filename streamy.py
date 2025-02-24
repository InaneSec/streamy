#!/usr/bin/env python3
# Streamy v1.0
# A desktop application to stream RTSP video from your 3D printer camera.
# Created and maintained by data_heavy@proton.me
# Repo: https://github.com/InaneSec/streamy/

import sys
import os
import time
import cv2
import threading
import argparse
import subprocess
import importlib.util
import json
import glob
import re
from datetime import datetime

# Application version
APP_VERSION = "1.0"

# Function to check and install dependencies
def check_and_install_dependencies():
    """Check if required packages are installed and install them if necessary"""
    required_packages = {
        'opencv-python': 'cv2',
        'numpy': 'numpy',
        'PyQt5': 'PyQt5'
    }
    
    missing_packages = []
    
    print("Checking required dependencies...")
    for package, module_name in required_packages.items():
        if module_name == 'cv2':
            # Special check for OpenCV since module name differs from package name
            if importlib.util.find_spec("cv2") is None:
                missing_packages.append(package)
                print(f"- {package}: Not installed")
            else:
                print(f"- {package}: Installed ✓")
        else:
            # Standard check for other packages
            if importlib.util.find_spec(module_name) is None:
                missing_packages.append(package)
                print(f"- {package}: Not installed")
            else:
                print(f"- {package}: Installed ✓")
    
    # Install missing packages
    if missing_packages:
        print("\nInstalling missing dependencies...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("All dependencies installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            print("\nPlease install the following packages manually:")
            for package in missing_packages:
                print(f"- {package}")
            sys.exit(1)
    else:
        print("All required dependencies are already installed!")

# Check and install dependencies before importing
check_and_install_dependencies()

# Now import the required packages after ensuring they're installed
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QComboBox, QPushButton, 
                           QMessageBox, QFrame, QSizePolicy, QLineEdit, QCheckBox)
from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter
from PyQt5.QtCore import Qt, QTimer, pyqtSlot

# Status indicator class
class StatusIndicator(QWidget):
    """Custom widget that displays a colored status dot"""
    
    RED = QColor(255, 60, 60)       # Error/Disconnected
    YELLOW = QColor(255, 200, 60)   # Warning/Partial connection
    GREEN = QColor(60, 200, 60)     # Success/Connected
    GRAY = QColor(150, 150, 150)    # Neutral/Idle
    
    def __init__(self, parent=None, color=None, size=16):
        super().__init__(parent)
        self.color = color or self.GRAY
        self.size = size
        self.setMinimumSize(size, size)
        self.setMaximumSize(size, size)
    
    def setColor(self, color):
        """Set the indicator color"""
        self.color = color
        self.update()
    
    def paintEvent(self, event):
        """Paint the indicator dot"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw circle with current color
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.color)
        painter.drawEllipse(2, 2, self.size-4, self.size-4)
        
        # Draw border
        painter.setPen(QColor(80, 80, 80, 100))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(2, 2, self.size-4, self.size-4)

# Class for the saved printer configuration
class PrinterConfig:
    """Class to manage saved printer configurations"""
    CONFIG_FILE = "streamy_config.json"
    
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self):
        """Load printer configuration from file"""
        default_config = {
            "recent_printers": [],
            "last_used_printer": "",
            "include_timestamp": True
        }
        
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    # Ensure all required keys exist
                    for key in default_config:
                        if key not in config:
                            config[key] = default_config[key]
                    return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return default_config
        else:
            return default_config
    
    def save_config(self):
        """Save printer configuration to file"""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def add_printer(self, ip_address):
        """Add printer to recent list and set as last used"""
        if ip_address:
            # Remove if already exists (to avoid duplicates)
            if ip_address in self.config["recent_printers"]:
                self.config["recent_printers"].remove(ip_address)
            
            # Add to start of list
            self.config["recent_printers"].insert(0, ip_address)
            
            # Keep only last 5 printers
            self.config["recent_printers"] = self.config["recent_printers"][:5]
            
            # Set as last used
            self.config["last_used_printer"] = ip_address
            
            # Save changes
            self.save_config()
    
    def get_recent_printers(self):
        """Get list of recent printer IP addresses"""
        return self.config["recent_printers"]
    
    def get_last_used_printer(self):
        """Get last used printer IP address"""
        return self.config["last_used_printer"]
    
    def set_include_timestamp(self, value):
        """Set whether to include timestamp on snapshots"""
        self.config["include_timestamp"] = value
        self.save_config()
        
    def get_include_timestamp(self):
        """Get whether to include timestamp on snapshots"""
        return self.config.get("include_timestamp", True)

def get_next_snapshot_number():
    """Get the next snapshot number based on existing files on desktop"""
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    
    # Look for existing streamy-*.png files
    existing_files = glob.glob(os.path.join(desktop_path, "streamy-*.png"))
    
    if not existing_files:
        # No existing files, start from 1
        return 1
    
    # Extract numbers from filenames
    numbers = []
    pattern = r'streamy-(\d+)\.png'
    for file in existing_files:
        match = re.search(pattern, file)
        if match:
            try:
                number = int(match.group(1))
                numbers.append(number)
            except (ValueError, IndexError):
                continue
    
    if not numbers:
        return 1
        
    # Return the highest number + 1
    return max(numbers) + 1

# Main application class
class StreamyApp(QMainWindow):
    """Main RTSP viewer application class using PyQt5"""
    def __init__(self, ip_address=None):
        """Initialize the application"""
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("Streamy v1.0")
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)
        
        # Load printer configuration
        self.config = PrinterConfig()
        
        # Internal variables
        self.camera = None
        self.camera_url = None
        self.is_running = False
        self.current_frame = None
        self.frame_width = 640
        self.frame_height = 480
        self.previous_status = "Not connected"  # Store previous status for status timer
        
        # Setup UI
        self.setup_ui()
        
        # Set up timer for updating video (30fps)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.setInterval(33)  # ~30 FPS
        
        # Set up timer for status message reset
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.reset_status)
        self.status_timer.setSingleShot(True)
        
        # Populate recent printers
        self.populate_printer_combobox()
        
        # Connect to provided IP address or last used printer
        if ip_address:
            self.ip_combo.setCurrentText(ip_address)
            self.connect_to_camera()
        elif self.config.get_last_used_printer():
            self.ip_combo.setCurrentText(self.config.get_last_used_printer())
    
    def setup_ui(self):
        """Set up the user interface"""
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Controls frame
        controls_frame = QWidget()
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(5, 5, 5, 5)
        
        # IP Address label and combobox
        ip_label = QLabel("Printer IP Address:")
        
        # Use QLineEdit instead of just ComboBox to handle Enter key press
        self.ip_line_edit = QLineEdit()
        self.ip_line_edit.returnPressed.connect(self.connect_to_camera)
        
        self.ip_combo = QComboBox()
        self.ip_combo.setEditable(True)
        self.ip_combo.setMinimumWidth(200)
        self.ip_combo.setLineEdit(self.ip_line_edit)  # Use our custom line edit with Enter key support
        
        # Connect/Disconnect buttons
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_to_camera)
        
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self.disconnect_camera)
        
        # Status indicator and label in a horizontal layout
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create status indicator dot
        self.status_indicator = StatusIndicator(size=16)
        status_layout.addWidget(self.status_indicator)
        
        # Create status label
        self.status_label = QLabel("Not connected")
        status_layout.addWidget(self.status_label)
        
        # Add stretch to push everything to the left
        status_layout.addStretch(1)
        
        # Add controls to layout
        controls_layout.addWidget(ip_label)
        controls_layout.addWidget(self.ip_combo)
        controls_layout.addWidget(self.connect_btn)
        controls_layout.addWidget(self.disconnect_btn)
        controls_layout.addStretch(1)
        controls_layout.addWidget(status_widget)
        
        # Video display
        self.video_frame = QLabel()
        self.video_frame.setFrameStyle(QFrame.StyledPanel)
        self.video_frame.setAlignment(Qt.AlignCenter)
        self.video_frame.setMinimumSize(640, 480)
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Set initial "no connection" message
        self.show_no_connection_message()
        
        # Bottom controls frame with snapshot button and timestamp checkbox
        bottom_frame = QWidget()
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(5, 5, 5, 5)
        
        # Add left spacer 
        bottom_layout.addStretch(1)
        
        # Create snapshot button
        self.snapshot_btn = QPushButton("Snapshot")
        self.snapshot_btn.clicked.connect(self.take_snapshot)
        self.snapshot_btn.setEnabled(False)  # Disabled initially until connected
        bottom_layout.addWidget(self.snapshot_btn)
        
        # Add timestamp checkbox
        self.timestamp_checkbox = QCheckBox("Include Timestamp")
        self.timestamp_checkbox.setChecked(self.config.get_include_timestamp())
        self.timestamp_checkbox.stateChanged.connect(self.timestamp_checkbox_changed)
        bottom_layout.addWidget(self.timestamp_checkbox)
        
        # Add right spacer
        bottom_layout.addStretch(1)
        
        # Version label (right aligned)
        version_label = QLabel(f"Streamy v{APP_VERSION}")
        version_label.setAlignment(Qt.AlignRight)
        version_label.setStyleSheet("color: gray;")
        bottom_layout.addWidget(version_label)
        
        # Add all widgets to main layout
        main_layout.addWidget(controls_frame)
        main_layout.addWidget(self.video_frame, 1)
        main_layout.addWidget(bottom_frame)
    
    def timestamp_checkbox_changed(self, state):
        """Handle timestamp checkbox state change"""
        include_timestamp = (state == Qt.Checked)
        self.config.set_include_timestamp(include_timestamp)
        print(f"Timestamp setting changed to: {include_timestamp}")
    
    def show_no_connection_message(self):
        """Show a message when no camera is connected"""
        # Create a blank image with a message
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, "No camera connected", (180, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(img, "Enter printer IP address and click Connect", (100, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Convert to QImage and display
        self.display_image(img)
    
    def populate_printer_combobox(self):
        """Populate the printer IP address combobox with recent printers"""
        recent_printers = self.config.get_recent_printers()
        self.ip_combo.clear()
        self.ip_combo.addItems(recent_printers)
    
    def reset_status(self):
        """Reset status message to previous state after temporary message"""
        # Only reset if not already reset and previous status exists
        if self.previous_status:
            self.status_label.setText(self.previous_status)
            print(f"Status reset to: {self.previous_status}")
    
    def show_temporary_status(self, message, duration_ms=5000):
        """Show a temporary status message, then revert to previous status"""
        # Save current status before changing it
        self.previous_status = self.status_label.text()
        print(f"Setting temporary status: {message} (Previous: {self.previous_status})")
        
        # Update status label with new message
        self.status_label.setText(message)
        
        # Stop any existing timer
        if self.status_timer.isActive():
            self.status_timer.stop()
            
        # Start timer to reset status after duration
        self.status_timer.start(duration_ms)
    
    def connect_to_camera(self):
        """Connect to the camera with the specified IP address"""
        ip_address = self.ip_combo.currentText().strip()
        
        if not ip_address:
            QMessageBox.critical(self, "Error", "Please enter a printer IP address")
            return
        
        # Construct RTSP URL
        rtsp_url = f"rtsp://{ip_address}:554/video"
        
        # Update status to connecting (yellow)
        self.status_indicator.setColor(StatusIndicator.YELLOW)
        self.status_label.setText(f"Connecting...")
        QApplication.processEvents()
        
        # Disconnect if already connected
        if self.camera is not None:
            self.disconnect_camera()
        
        try:
            # Create VideoCapture object
            camera = cv2.VideoCapture(rtsp_url)
            
            # Set buffer size to reduce latency
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 3)
            
            # Check if connection was successful
            if not camera.isOpened():
                self.status_indicator.setColor(StatusIndicator.RED)
                self.status_label.setText("Not connected")
                QMessageBox.critical(self, "Connection Error", 
                                    f"Could not connect to the camera at {rtsp_url}.\n\n"
                                    f"Please check that the printer is powered on, connected to the network, "
                                    f"and has the camera enabled.")
                return
            
            # Test if we can read a frame
            ret, test_frame = camera.read()
            if not ret or test_frame is None:
                self.status_indicator.setColor(StatusIndicator.YELLOW)
                self.status_label.setText("Connected but not able to stream")
                QMessageBox.critical(self, "Video Error", 
                                   f"Connected to {rtsp_url} but could not read video frames.\n\n"
                                   f"Please check that the printer's camera is functioning properly.")
                camera.release()
                return
            
            # Success - everything is working
            self.status_indicator.setColor(StatusIndicator.GREEN)
            self.status_label.setText("Connected")
            
            # Get frame dimensions
            self.frame_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Save camera object and URL
            self.camera = camera
            self.camera_url = rtsp_url
            
            # Save to config
            self.config.add_printer(ip_address)
            self.populate_printer_combobox()
            
            # Enable snapshot button
            self.snapshot_btn.setEnabled(True)
            
            # Start video timer
            self.is_running = True
            self.timer.start()
            
        except Exception as e:
            self.status_indicator.setColor(StatusIndicator.RED)
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred while trying to connect:\n\n{str(e)}")
    
    def disconnect_camera(self):
        """Disconnect from the camera"""
        if self.camera is not None:
            # Stop timer
            self.timer.stop()
            self.is_running = False
            
            # Release camera
            self.camera.release()
            self.camera = None
            self.camera_url = None
            
            # Update status
            self.status_indicator.setColor(StatusIndicator.GRAY)
            self.status_label.setText("Not connected")
            
            # Disable snapshot button
            self.snapshot_btn.setEnabled(False)
            
            # Show no connection message
            self.show_no_connection_message()
    
    def take_snapshot(self):
        """Take a snapshot of the current video frame and save it to desktop"""
        if not self.is_running or self.current_frame is None:
            QMessageBox.warning(self, "Snapshot Error", "No video stream is active")
            return
            
        try:
            # Get the desktop path
            desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
            
            # Get next snapshot number based on existing files
            snapshot_num = get_next_snapshot_number()
            
            # Create filename with padded number (e.g., streamy-0001.png)
            filename = f"streamy-{snapshot_num:04d}.png"
            
            # Full path
            filepath = os.path.join(desktop_path, filename)
            
            # Create a copy of the frame for the snapshot
            snapshot_frame = self.current_frame.copy()
            
            # Add timestamp if enabled
            if self.timestamp_checkbox.isChecked():
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(snapshot_frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Save the image
            cv2.imwrite(filepath, snapshot_frame)
            
            # Show temporary success message
            self.show_temporary_status(f"Snapshot saved: {filename}", 5000)
            print(f"Snapshot saved to: {filepath}")
            
        except Exception as e:
            QMessageBox.critical(self, "Snapshot Error", f"Failed to save snapshot: {str(e)}")
            print(f"Error saving snapshot: {e}")
    
    @pyqtSlot()
    def update_frame(self):
        """Update video frame (called by timer)"""
        if not self.is_running or self.camera is None:
            return
            
        try:
            # Read frame
            ret, frame = self.camera.read()
            
            if not ret or frame is None:
                self.status_indicator.setColor(StatusIndicator.YELLOW)
                self.status_label.setText("Connected but not able to stream")
                self.disconnect_camera()
                return
            
            # Frame received successfully - ensure status is green
            if self.status_indicator.color != StatusIndicator.GREEN:
                self.status_indicator.setColor(StatusIndicator.GREEN)
                self.status_label.setText("Connected")
                
            # Save current frame for snapshots (without timestamp)
            self.current_frame = frame.copy()
                
            # Add timestamp to display frame (not the saved current_frame)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
            
            # Display the frame
            self.display_image(frame)
            
        except Exception as e:
            print(f"Error updating frame: {e}")
            self.status_indicator.setColor(StatusIndicator.YELLOW)
            self.status_label.setText("Connected but not able to stream")
    
    def display_image(self, img):
        """Convert OpenCV image to Qt format and display it"""
        if img is None:
            return
            
        # Convert the image to RGB format (OpenCV uses BGR)
        if len(img.shape) == 3:  # Color image
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            format = QImage.Format_RGB888
        else:  # Grayscale image
            format = QImage.Format_Grayscale8
        
        # Create QImage from the numpy array
        h, w = img.shape[:2]
        bytes_per_line = 3 * w if len(img.shape) == 3 else w
        q_img = QImage(img.data, w, h, bytes_per_line, format)
        
        # Get the size of the label
        label_size = self.video_frame.size()
        
        # Scale the image to fit the label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Display the image
        self.video_frame.setPixmap(scaled_pixmap)
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.camera is not None:
            self.disconnect_camera()
        super().closeEvent(event)

def main():
    """Main function"""
    print("==================================================")
    print("==================================================")
    print("                   Streamy v1.0                   ")
    print("  Created and maintained by data_heavy@proton.me  ")
    print("        https://github.com/InaneSec/streamy/      ")
    print("==================================================")
    print("==================================================")

    parser = argparse.ArgumentParser(description='RTSP Stream Viewer')
    parser.add_argument('--ip', type=str, help='IP address of the RTSP stream')
    args = parser.parse_args()
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')  # This style works well across platforms
    
    # Create main window
    window = StreamyApp(args.ip)
    window.show()
    
    # Start event loop
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()