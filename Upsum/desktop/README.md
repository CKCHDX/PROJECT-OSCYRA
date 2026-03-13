# Upsum Desktop Application

Privacy-focused Qt WebEngine browser for accessing Upsum.

## Features

- **Privacy-First**: No cookies, no cache, no tracking
- **Incognito Mode**: All sessions are private by default
- **Clean Interface**: Minimal, distraction-free browsing
- **Direct Access**: Connects to https://upsum.oscyra.solutions
- **Dark Theme**: Nordic-inspired design matching Upsum's aesthetic

## Installation

### Windows

1. Navigate to desktop directory:
   ```cmd
   cd desktop
   ```

2. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

3. Run the application:
   ```cmd
   python upsum_desktop.py
   ```

### Create Executable (Optional)

To create a standalone .exe:

1. Install PyInstaller:
   ```cmd
   pip install pyinstaller
   ```

2. Build executable:
   ```cmd
   pyinstaller --onefile --windowed --name Upsum --icon=upsum.ico upsum_desktop.py
   ```

3. Find executable in `dist/Upsum.exe`

## Usage

- **Home Button**: Returns to Upsum homepage
- **URL Bar**: Navigate to any URL (primarily for Upsum)
- **Privacy**: No data is saved between sessions
- **Clean Exit**: Close window to quit

## Privacy Features

- No HTTP cache
- No persistent cookies
- No local storage
- No geolocation
- No popup windows
- JavaScript limited to Upsum functionality

## Technical Details

- **Framework**: PyQt6 with WebEngine
- **Profile**: Off-the-record (incognito)
- **Default URL**: https://upsum.oscyra.solutions
- **Theme**: Dark Nordic aesthetic matching Upsum

## Development

The desktop app is a thin wrapper around Qt WebEngine configured for maximum privacy. It's designed to be lightweight and secure for accessing Upsum without browser tracking.

## License

Part of the Upsum project by Oscyra Solutions.
