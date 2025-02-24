#!/usr/bin/env python3
"""
Streamy v1.0 - macOS App Builder
This script builds a standalone macOS app with custom icon support.
"""
import os
import sys
import subprocess
import shutil
import importlib.util
import platform

# Verify macOS
if platform.system() != "Darwin":
    print("Error: This script is for macOS only.")
    sys.exit(1)

print("===== Streamy v1.0 - macOS App Builder =====")

# Check for source files
script_path = "streamy.py"
icon_path = "view.icns"

if not os.path.exists(script_path):
    print(f"Error: Could not find {script_path} in the current directory.")
    print("Make sure this builder is in the same directory as streamy.py")
    sys.exit(1)

# Check for icon file
has_custom_icon = os.path.exists(icon_path)
if has_custom_icon:
    print(f"Found custom icon: {icon_path}")
    icon_option = "'iconfile': 'view.icns',"
else:
    print(f"Warning: Custom icon file {icon_path} not found. Will use default icon.")
    icon_option = ""

# Ensure pip is available
try:
    print("Checking pip installation...")
    subprocess.check_call([sys.executable, "-m", "pip", "--version"], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except:
    print("Error: pip is not available. Please install pip first.")
    sys.exit(1)

# Install/update dependencies
print("\nInstalling required dependencies...")
dependencies = ["PyQt5", "opencv-python", "numpy", "py2app==0.28.0"]
for dep in dependencies:
    print(f"Installing {dep}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", dep])
    except subprocess.CalledProcessError as e:
        print(f"Warning: Issue installing {dep}: {e}")
        print("Trying to continue anyway...")

print("\nCreating application with custom modifications...")

# Clean up previous build artifacts
if os.path.exists("build"):
    print("Cleaning up previous build directory...")
    shutil.rmtree("build")
if os.path.exists("dist"):
    print("Cleaning up previous dist directory...")
    shutil.rmtree("dist")

# Create a custom setup.py with enhanced options
setup_content = """
from setuptools import setup

APP = ['streamy.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,  # Changed to False for better compatibility
    'packages': ['PyQt5', 'cv2', 'numpy'],
    'includes': ['sip', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets'],
    'excludes': ['tkinter', 'matplotlib', 'scipy', 'wx', 'PyQt5.QtWebEngineWidgets'],
    'frameworks': ['/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework'],
    """ + icon_option + """
    'plist': {
        'CFBundleName': 'Streamy',
        'CFBundleDisplayName': 'Streamy',
        'CFBundleIdentifier': 'com.streamy.rtspviewer',
        'CFBundleVersion': '1.0',
        'CFBundleShortVersionString': '1.0',
        'NSHumanReadableCopyright': '© 2025',
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': True,
    }
}

setup(
    app=APP,
    name='Streamy',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app==0.28.0'],
)
"""

# Write the custom setup file
with open("_build_setup.py", "w") as f:
    f.write(setup_content)

# Build the application in development mode first (more reliable)
print("\nBuilding in development mode (alias)...")
try:
    subprocess.check_call([sys.executable, "_build_setup.py", "py2app", "-A"])
    print("Development build successful.")
except subprocess.CalledProcessError as e:
    print(f"Error in development build: {e}")
    print("Attempting to continue with full build...")

# Now build the standalone version
print("\nBuilding standalone application...")
try:
    # Remove alias build
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # Build standalone app with custom icon
    subprocess.check_call([sys.executable, "_build_setup.py", "py2app", "--no-strip"])
    
    app_path = os.path.abspath("dist/Streamy.app")
    print("\n✅ Application built successfully!")
    print(f"\nYour app has been created at:")
    print(f"  {app_path}")
    
    if has_custom_icon:
        print("\nThe app has been built with your custom icon (view.icns).")
        print("It may take a moment for macOS to refresh the icon cache.")
    
    # Additional instructions
    print("\nImportant: Before moving to Applications folder, test the app by:")
    print("  1. Right-click the app bundle in Finder")
    print("  2. Select 'Show Package Contents'")
    print("  3. Navigate to Contents/MacOS")
    print("  4. Double-click on 'Streamy' inside (the executable)")
    print("  5. If it runs correctly, you can move it to Applications")
    
except subprocess.CalledProcessError as e:
    print(f"\n❌ Error building application: {e}")
    print("\nTroubleshooting tips:")
    print("  - Make sure you have the latest macOS SDK installed")
    print("  - Try installing the dependencies manually:")
    print("    pip3 install PyQt5==5.15.2 opencv-python numpy py2app==0.28.0")
    print("  - Verify that your icon file is a valid .icns format")
    print("  - Run this script again")

# Clean up
try:
    os.remove("_build_setup.py")
except:
    pass

print("\n===========================================================")