# Streamy v1.0

- A desktop application to stream RTSP video from your 3D printer camera.
- Created and maintained by data_heavy@proton.me
- Repo: https://github.com/InaneSec/streamy/


## Features

- **Simple RTSP Streaming** - Connect to your 3D printer's camera stream with ease
- **Visual Status Indicators** - Color-coded status dots show connection state at a glance
- **Snapshot Capability** - Capture and save images from the live stream to your desktop
- **Flexible Configuration** - Save commonly used IP addresses for quick access
- **Automatic Dependency Management** - Required packages are installed on first run

## Quick Start

### Running the Python Script Directly

1. Download `streamy.py` file
2. Run it with:
   ```
   python3 streamy.py
   ```
3. Enter your printer's IP address (or select from history)
4. Press Enter or click "Connect"

### Command Line Options

You can specify a printer IP address at startup:
```
python3 streamy.py --ip 192.168.1.100
```

## Creating a macOS Application

### Building the App (One-Time Process)

1. Download both `streamy.py` and `build_app.py` files to the same folder
2. If you want to use a custom icon, include a file named `view.icns` in the same folder
3. Open Terminal and run:
   ```
   python3 build_app.py
   ```
4. The builder script will:
   - Install necessary dependencies if needed
   - Create the application bundle
   - Place it in a `dist` folder

5. Move the resulting `.app` file to your Applications folder

> **Note:** When building the app, you may see a warning about "No module named sip" - this is normal and won't affect functionality.

## Snapshot Features

Streamy includes advanced snapshot capabilities:

### Taking Snapshots

1. Click the "Snapshot" button at the bottom of the window
2. Images are saved to your desktop with sequential numbering (streamy-0001.png, etc.)
3. The status message confirms when a snapshot is saved (disappears after 5 seconds)

### Snapshot Options

- **Include Timestamp** - Toggle timestamping on saved images with the checkbox
- **Automatic Numbering** - Even if you delete some snapshots, the numbering always picks up correctly
- **Original Quality** - Snapshots are saved at the camera's native resolution

## Status Indicators

The application uses color-coded status indicators:

- **Red** - Not connected / Connection error
- **Yellow** - Connected but unable to stream
- **Green** - Fully connected and streaming
- **Gray** - Disconnected / Idle state

## Connection Troubleshooting

If you have trouble connecting to your printer's camera:

1. **Verify the printer is powered on** and connected to your network
2. **Check that your printer's camera is enabled** in its settings
3. **Confirm the IP address** is correct (try pinging it from Terminal)
4. **Check your firewall settings** to ensure it's not blocking RTSP traffic on port 554
5. **Try a different port or path** if your printer uses a non-standard configuration

## Requirements

- Python 3.7 or higher
- PyQt5
- OpenCV-Python
- NumPy

These dependencies are automatically installed when you first run the application.

## Configuration

Streamy stores your preferences in a file called `streamy_config.json` including:

- Recently used printer IP addresses
- Last used printer IP
- Timestamp preference for snapshots

## License

This project is available under the MIT License.
