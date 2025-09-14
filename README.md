# MyLocalAPI

**MyLocalAPI** is a lightweight local HTTP server for Windows PC control. It provides REST endpoints for switching audio outputs, controlling volume, launching streaming services, and managing fan control profiles. The application features a system tray icon and a Tkinter GUI for configuration.

## Features

- **Audio Control**: Switch default audio devices, set volume, query current device status
- **Streaming Services**: Launch YouTube, Netflix, Disney+, Prime Video, Apple TV, and Crunchyroll
- **Fan Control**: Integrate with FanControl.exe to manage fan profiles and speeds  
- **System Tray**: Runs quietly in system tray with right-click menu
- **GUI Configuration**: Easy-to-use settings interface with device mapping
- **Token Security**: API endpoints protected with configurable token
- **Autostart**: Optional Windows startup integration

## Quick Start

### Prerequisites

- Windows 10/11 (64-bit recommended)
- Python 3.9+ (for development) or use pre-built executable

### Installation

#### Option 1: Pre-built Executable (Recommended)
1. Download the latest `MyLocalAPI.exe` from releases
2. Run the executable - it will create a system tray icon
3. Right-click the tray icon and select "Settings..." to configure

#### Option 2: Development Setup
```bash
# Clone repository
git clone <repository-url>
cd MyLocalAPI

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

### Basic Configuration

1. **Set Port and Token**: Configure in the GUI (default: port 1482, token "changeme")
2. **Audio Mappings**: Add your audio devices with labels (e.g., "headphones", "speakers")
3. **Start Server**: Click "Start" button in GUI or tray menu

### API Usage

Once started, the server provides REST endpoints:

```bash
# Switch to headphones
curl "http://127.0.0.1:1482/switch?key=headphones&token=changeme"

# Set volume to 50%
curl "http://127.0.0.1:1482/volume?percent=50&token=changeme"

# Get current device and volume
curl "http://127.0.0.1:1482/device/current?token=changeme"

# Launch YouTube (switches to streaming device if configured)
curl "http://127.0.0.1:1482/openStreaming?service=youtube&token=changeme"
```

## Configuration

### Audio Control Settings

- **Enable Audio Control**: Toggle audio-related endpoints
- **SvvPath**: Optional path to custom svcl.exe (bundled by default)  
- **Device Mappings**: Map friendly labels to Windows audio device IDs

**Finding Device IDs**: Use the bundled `svcl.exe` or SoundVolumeView:
```bash
svcl.exe /scomma "" /Columns "Name,Command-Line Friendly ID"
```

Device IDs follow the format: `Provider\Device\DeviceName\Render`

### Fan Control Settings

- **Enable Fan Control**: Toggle fan-related endpoints
- **FanControl.exe Path**: Path to FanControl executable
- **Fan Config Directory**: Directory containing .json configuration files
- **Apply on Stream Launch**: Automatically apply fan profile when launching streaming services

**Fan Config Requirements**: JSON files in config directory, preferably named with percentages (e.g., `50.json`, `75.json`)

### Streaming Services

- **Enable Streaming Endpoint**: Toggle `/openStreaming` endpoint
- **Apple TV Moniker**: Windows app identifier for Apple TV app (auto-detected)

Supported services:
- `youtube` (opens in Chrome)
- `crunchyroll` (opens in Chrome)  
- `netflix` (opens in Edge)
- `disney` (opens in Edge)
- `prime` (opens in Edge)
- `appletv` (launches Apple TV app)

### System Settings

- **Autostart**: Launch MyLocalAPI on Windows startup (registry-based)
- **Settings Management**: Export/import/reset configuration

## API Reference

### Authentication
All endpoints require a `token` parameter matching the configured token.

### Audio Endpoints

#### `GET /switch`
Switch default audio device.
- `key`: Device label from mappings, OR
- `id`: Direct device ID (Command-Line Friendly ID)
- `token`: API token

#### `GET /volume`
Set system volume percentage.
- `percent`: Volume level (0-100)
- `token`: API token

#### `GET /volume/current`
Get current volume and device information.
- `token`: API token

#### `GET /device/current` 
Get current default audio device details.
- `token`: API token

#### `GET /list`
List all available playback devices.
- `token`: API token

### Streaming Endpoints

#### `GET /openStreaming`
Launch streaming service and switch to streaming audio device (if configured).
- `service`: One of `youtube|crunchyroll|netflix|disney|prime|appletv`
- `token`: API token

### Fan Control Endpoints

#### `GET /fan/apply`
Apply fan configuration or percentage.
- `name`: Configuration basename, OR
- `percent`: Target percentage (0-100)
- `token`: API token

#### `GET /fan/refresh`
Refresh FanControl sensors.
- `token`: API token

#### `GET /fan/configs`
Get available fan configurations.
- `nearestTo`: Optional percentage to find closest config
- `token`: API token

#### `GET /fan/status`
Get fan control status and running processes.
- `token`: API token

### System Endpoints

#### `GET /status`
Get overall system status (audio, devices, fan).
- `token`: API token

#### `GET /diag`
Get diagnostic information for troubleshooting.
- `token`: API token

## Packaging for Distribution

### PyInstaller Build

Create a standalone executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Create executable (single file)
pyinstaller --onefile --noconsole --add-data "scripts;scripts" main.py

# Or use the provided spec file
pyinstaller mylocalapi.spec
```

### Bundling Dependencies

The application requires these external executables:

1. **svcl.exe** (NirSoft SoundVolumeCommandLine):
   - Download from https://www.nirsoft.net/utils/sound_volume_command_line.html
   - Place in `scripts/svcl-x64/` directory
   - Will be bundled automatically with PyInstaller

2. **FanControl.exe** (optional):
   - Download from https://github.com/Rem0o/FanControl.releases  
   - User must install separately and configure path in GUI

### Advanced Packaging with Inno Setup

For a professional installer:

```iss
; Example Inno Setup script
[Setup]
AppName=MyLocalAPI
AppVersion=1.0
DefaultDirName={pf}\MyLocalAPI
DefaultGroupName=MyLocalAPI
OutputBaseFilename=MyLocalAPI-Setup

[Files]
Source: "dist\main.exe"; DestDir: "{app}"; DestName: "MyLocalAPI.exe"
Source: "scripts\*"; DestDir: "{app}\scripts"; Flags: recursesubdirs

[Icons]  
Name: "{group}\MyLocalAPI"; Filename: "{app}\MyLocalAPI.exe"
Name: "{group}\Uninstall MyLocalAPI"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\MyLocalAPI.exe"; Description: "Launch MyLocalAPI"; Flags: postinstall
```

## Known Limitations and TODOs

### Current Limitations

1. **Windows Only**: Uses Windows-specific audio APIs and system integrations
2. **Fan Control Dependency**: Requires separate FanControl.exe installation
3. **Browser Dependencies**: Streaming services require Chrome/Edge installation
4. **Single Instance**: Only one server can run per port (by design)

### Fan Control Integration Notes

The fan control functionality depends on the third-party FanControl application:
- **Configuration Parsing**: Currently reads .json files from config directory
- **Profile Names**: Works best with percentage-based filenames (e.g., `50.json`)
- **Process Management**: Starts/stops FanControl.exe as needed
- **TODO**: Investigate if FanControl.exe supports command-line config listing

If FanControl.exe provides a `--list-configs` or similar option, it should be used instead of directory parsing.

### Future Enhancements

- [ ] Linux/macOS support using platform-specific audio APIs
- [ ] Native Windows Audio API integration (bypass svcl.exe dependency)  
- [ ] Plugin system for additional hardware control
- [ ] Web dashboard interface
- [ ] Mobile app integration
- [ ] Voice control integration (Alexa/Google Assistant)

## Troubleshooting

### Common Issues

**Server won't start:**
- Check port is not in use: `netstat -an | findstr :1482`
- Verify token is not empty
- Check Windows Firewall settings

**Audio switching not working:**
- Verify svcl.exe is bundled or path is correct
- Check device mappings are complete (both label and device ID)
- Run `svcl.exe /list` to verify device visibility

**Fan control not responding:**
- Ensure FanControl.exe path is correct and executable exists
- Verify fan config directory contains .json files  
- Check FanControl.exe can run normally outside MyLocalAPI

**Streaming services not launching:**
- Verify Chrome/Edge installation for browser-based services
- Check Apple TV app installation and moniker for Apple TV
- Test launching services manually first

### Debug Mode

For detailed logging, run from command line:
```bash
MyLocalAPI.exe --debug
```

Or check the log file: `%APPDATA%\MyLocalAPI\mylocalapi.log`

### System Requirements

- **Minimum**: Windows 10 1803, 2GB RAM, 50MB disk space
- **Recommended**: Windows 11, 4GB+ RAM, Chrome and Edge installed
- **Optional**: FanControl.exe for fan management features

## Development

### Project Structure

```
MyLocalAPI/
├── main.py              # Application entry point
├── settings.py          # Settings management and persistence  
├── server.py           # Flask HTTP server
├── gui.py              # Tkinter GUI interface
├── audio_control.py    # Audio device management via svcl.exe
├── streaming.py        # Streaming service integration
├── fan_control.py      # Fan control via FanControl.exe
├── utils.py            # Utilities and Windows integration
├── requirements.txt    # Python dependencies
├── scripts/
│   └── svcl-x64/       # Bundled NirSoft tools
├── tests/              # Test scripts
└── README.md          # This file
```

### Running Tests

```bash
# Run basic functionality tests
python -m pytest tests/

# Manual QA checklist (see below)
python tests/manual_qa.py
```

## Manual QA Checklist

Execute these tests before release:

### Basic Functionality
- [ ] 1. Start app, set Port (1482) and Token, start server
- [ ] 2. Verify `http://127.0.0.1:1482/` responds with JSON status  
- [ ] 3. Call `/device/current` and `/volume/current` - verify JSON response
- [ ] 4. Add device mapping with label "headphones" and valid device ID
- [ ] 5. Call `/switch?key=headphones&token=<token>` - verify success response
- [ ] 6. Toggle audio control OFF - verify endpoints return disabled responses

### GUI and Tray
- [ ] 7. Verify tray menu shows Port: 1482 and Start/Stop states correctly
- [ ] 8. Test "Open MyLocalAPI" opens default browser to server root
- [ ] 9. Left-click tray icon opens/focuses GUI window
- [ ] 10. Test server Start/Stop/Restart buttons in both GUI and tray

### System Integration  
- [ ] 11. Toggle "Launch on startup" - verify registry entry created/removed
- [ ] 12. Test settings Export/Import functionality
- [ ] 13. Test settings Reset to Defaults

### Streaming Services
- [ ] 14. Enable streaming endpoint, test `/openStreaming?service=youtube&token=<token>`
- [ ] 15. Disable streaming endpoint, verify returns disabled response
- [ ] 16. Configure "Use for streaming" on a device mapping, verify audio switches

### Fan Control (if available)
- [ ] 17. Configure fan paths, enable fan control
- [ ] 18. Test `/fan/configs` returns available configurations  
- [ ] 19. Test `/fan/apply?percent=50&token=<token>` applies closest config
- [ ] 20. Enable "Apply on stream launch", verify fan config applies with streaming

### Packaging Test
- [ ] 21. Build with PyInstaller: `pyinstaller --onefile main.py`
- [ ] 22. Run generated exe on clean Windows 10/11 VM
- [ ] 23. Verify bundled svcl.exe is present and endpoints function
- [ ] 24. Test tray icon, GUI, and server functionality in packaged version

### Error Handling
- [ ] 25. Try starting server on port already in use - verify clear error
- [ ] 26. Test with invalid token - verify 401 responses  
- [ ] 27. Test with missing/invalid device IDs - verify graceful error handling
- [ ] 28. Test GUI responsiveness during server operations

All tests should pass before considering the application ready for release.

## AS IS Disclaimer

MyLocalAPI is provided "AS IS", without warranty of any kind. Use of this software, included scripts, bundled utilities, or pre-built executables is at your own risk. The authors and contributors disclaim all warranties, express or implied, including but not limited to warranties of merchantability, fitness for a particular purpose, security, and non-infringement.

The authors are not liable for any direct, indirect, incidental, special, consequential, or exemplary damages (including but not limited to loss of data, lost profits, downtime, or system damage) arising from the use or inability to use this software, even if advised of the possibility of such damage. You are responsible for securing the API token, configuring your firewall, and using strong local network practices.

Third-party tools (e.g., svcl.exe, FanControl.exe, browsers) are provided and maintained by their respective authors; you assume any risks related to installing or executing those tools. This disclaimer does not constitute legal advice. If you need warranties or liability coverage, contact the project maintainer or consult a legal professional.

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.

## Support

For issues, feature requests, or questions:
- GitHub Issues: <repository-url>/issues
- Documentation: This README and inline code comments
- Logs: Check `%APPDATA%\MyLocalAPI\mylocalapi.log` for debugging

## Acknowledgments
- **NirSoft** for SoundVolumeCommandLine tool
- **Rem0o** for FanControl application  
