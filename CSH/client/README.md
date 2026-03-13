# SLP Windows Client

Windows GUI client for connecting to SLP (Secure Line Protocol) servers.

## Files

- `slp_client_gui.py` - Main GUI application
- `build_exe.bat` - Windows batch script to build .exe
- `dist/SLP_Client.exe` - Compiled executable (after build)

## Building the Executable

### Prerequisites

- Python 3.8 or higher
- PyInstaller (`pip install pyinstaller`)

### Build Steps

#### Windows:

```batch
cd client
build_exe.bat
```

#### Linux/Mac:

```bash
cd client
pip install pyinstaller
pyinstaller --onefile --windowed --name=SLP_Client slp_client_gui.py
```

### Build Output

The executable will be created in:
```
client/dist/SLP_Client.exe
```

## Running the Client

### From Python:

```bash
python slp_client_gui.py
```

### From Executable:

```bash
dist\SLP_Client.exe
```

## Usage

1. **Enter SLP Address**
   - Format: `slp://host:port/path`
   - Example: `slp://localhost:4270/`
   - Example: `slp://192.168.1.100:4270/index`

2. **Click Connect**
   - Client will send SLP request to server
   - Response will be displayed in text area

3. **Open in Browser**
   - After successful connection
   - Opens HTML response in default web browser

## Features

- ✅ Clean modern GUI
- ✅ SLP protocol support
- ✅ Custom address parsing
- ✅ Response display
- ✅ Browser integration
- ✅ Error handling
- ✅ Status indicators
- ✅ Connection logging

## Troubleshooting

### Build Errors

**ModuleNotFoundError**: Install required packages:
```bash
pip install -r ../requirements.txt
pip install pyinstaller
```

**Permission Denied**: Run as administrator on Windows

### Connection Errors

**Connection Timeout**:
- Ensure server is running
- Check firewall allows UDP port 4270
- Verify host/port are correct

**Invalid Packet**:
- Ensure server is using SLP protocol
- Check server version matches client

## Technical Details

- **Protocol**: SLP (Secure Line Protocol)
- **Transport**: UDP
- **Port**: 4270 (default)
- **Packet Format**: 8-byte header + payload
- **Timeout**: 5 seconds
- **Max Receive Size**: 64KB

## Development

### Testing

1. Start SLP server:
```bash
python examples/server_v2.py
```

2. Run client:
```bash
python slp_client_gui.py
```

3. Enter: `slp://localhost:4270/`

4. Click Connect

### Debugging

Enable console output in PyInstaller:
```bash
pyinstaller --onefile --console --name=SLP_Client_Debug slp_client_gui.py
```

## Future Enhancements

- [ ] Encryption support
- [ ] Connection history
- [ ] Bookmarks
- [ ] Advanced settings
- [ ] Multi-tab support
- [ ] Download manager

## License

Part of the SLP (Secure Line Protocol) project.
Copyright © 2026 Oscyra Solutions
