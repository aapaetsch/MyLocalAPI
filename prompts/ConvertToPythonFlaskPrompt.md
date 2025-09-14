You are converting an existing PowerShell HTTP server (audio-switch-server.ps1) into a Python application. The app must run a Flask HTTP server and provide a Tkinter GUI used mainly for settings and server control. When the Flask server is running the app must show a system tray icon. Produce a complete, production-ready implementation and packaging instructions for Windows (PyInstaller preferred). Deliver working source code, a README, and basic automated tests or manual QA steps.

High-level goals
- Retain all API functionality from the PowerShell server (see Endpoints & behavior below).
- Provide a Tkinter GUI that allows users to change settings, start/stop/restart server, and edit the device mapping lists and file paths.
- Show a system tray icon while the app is running. Left-click opens/raises the GUI. Right-click shows a menu with the required items and actions.
- Persist settings to a JSON file in the user app data folder and load them on startup.
-  Provide production packaging guidance (PyInstaller) and instructions for bundling svcl.exe/soundvolumeview and fancontrol.exe executables.

Required libraries (recommended)

Use these or equivalents:
- Flask (+ Flask-Cors if needed)
- pystray (tray icon/menu handling)
- Pillow (for tray icon image)
- tkinter (standard lib) + ttk for widgets
- threading / multiprocessing (to run Flask alongside Tkinter)
- pywin32 or ctypes for Win32 interactions (optional, for rounded corners, autostart, and bringing windows to front)
- watchdog (optional — to watch fan config files)
- requests for internal HTTP calls (if needed)
- packaging: pyinstaller
**Note: If any platform-specific APIs are used, implement fallbacks or degrade gracefully.

UI / System Tray — Functional spec

System Tray icon behavior:
- App shows a system tray icon while the program process lives.
- Left-click on tray icon: open and focus the main GUI window (if minimized or hidden).
- Right-click menu (exact ordering; the bottom item Quit must be separated by a visually thicker separator):
  1. Open MyLocalAPI — opens default browser to http://127.0.0.1:<Port>/
  2. Settings... — opens GUI (same as left-click)
  3. Port: #### — disabled menu item (shows current configured port, updates live)
  4. Start — start Flask server (if not running)
  5. Stop — stop Flask server (if running)
  6. Restart — restart Flask server
  7. ---- (thicker separator)
  8. Quit — gracefully stop server + app
- The menu items should reflect state (e.g., gray out Start if running).

Tkinter GUI layout & behavior:
- Title bar shows App name and icon.
- Window should attempt rounded corners on Windows; if not possible, fall back to normal window. (Implement via Win32 SetWindowRgn / layered window or using a modern ttk theme; fallback acceptable.)
- Top region: a server status indicator (Running / Stopped) and Start/Stop/Restart buttons mirrored from tray.
- Directly under the top bar, a top section with two required input rows (these must be validated before starting the server):
  - Port (numeric input)
  - Token (text input)
- A sideways (horizontal) tab menu under that top section with two tabs:
  - Settings
  - Endpoints
- Bottom of the main window: Start / Stop / Restart buttons (same functions) and a live status message.

Settings tab — contents

Audio Input Control Section:
- Toggle (checkbox) to enable/disable audio input control endpoints and related settings UI.
- SvvPath input (optional). Display a help text below: “Optional: svcl.exe/SoundVolumeView will be bundled; only fill this to use a local installation.”
- Mapping list with header and an inline "Add" button. The list columns:
  - Label (text input)
  - DeviceID (text input)
  - UseForStreamingServices (checkbox)
- Business rules:
  - Label and DeviceID are required for each row.
  - Only one row can have UseForStreamingServices checked at a time; selecting a new one must uncheck previous.
  - If the Audio Input Control toggle is enabled, at least one mapping row must be fully filled.
- Add/Delete row controls. Persist mapping to settings JSON.

Fan Control Section:
- Toggle to enable/disable fan control endpoints and settings.
- fancontrol.exe path row (label + input).
- fan control config path row (label + input).
- Toggle: Apply fan config on stream launch — when ON, reveal a dropdown under it populated with the fan control config names parsed from the fancontrol config path.
  - The dropdown cannot be populated until fan control config path is set.
  - If parsing fails, show a user-friendly error message with an option to refresh/try again.

Streaming / OpenStreaming setting:
- Toggle: Launch Streaming service by endpoint — enables/disables the openStreaming endpoint entirely.
  - When OFF, /openStreaming should be treated as disabled: any request to it should return a clear error (HTTP 403 or 404 with JSON explaining it is disabled).
  - When ON (default), /openStreaming behaves as specified in Endpoints & behavior.
  - Persist this toggle in settings JSON and reflect its state in the Endpoints tab status icons.
- An input for the apple tv app moniker, if possible we should find and populate this field for the user.

Endpoints tab — contents:
- Show a list of each available endpoint and its query parameters.
- Each endpoint group shows a status icon that indicates whether the feature is enabled in the settings (green = enabled / gray = disabled).
- Each endpoint entry has:
  - Endpoint path (e.g., /switch)
  - HTTP method
  - Parameters and brief descriptions
  - An example curl line and a quick "Test" button that calls the endpoint and displays the response in a small status area.
- The /openStreaming endpoint should show its enabled/disabled state tied to the Launch Streaming service by endpoint toggle.

Extra features:
- A toggle/setting: Launch on system startup. Implement using:
  - Windows: create a shortcut in the %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup folder or use registry Run entry. Provide UI toggle and explain the method used.
- Save & load settings from settings.json in the app data folder (%APPDATA%/<AppName>/settings.json).

Endpoints & behavior (keep same semantics as original PS server):
Provide these endpoints and preserve existing query parameters/behavior. (If the PS script had more endpoints, port over all.) Example expected endpoints (implement as described and add any missing from the original script):
- GET /switch?key=<key>&id=<deviceId>&token=<token> — set default playback device by key or device ID.
  - key maps to entries in the mapping list (labels -> DeviceID)
  - id overrides mapping when provided
- GET /volume?percent=<0-100>&token=<token> — set device/system volume to a percent
- GET /volume/current?token=<token> — returns JSON with systemVolume and deviceVolume
- GET /device/current?token=<token> — returns current default device id/name
- GET /openStreaming?service=<youtube|crunchyroll|netflix|disney|prime|appletv>&token=<token> — open service; if UseForStreamingServices mapping exists, route audio to that device, and optionally apply fan config (if enabled)
  - This endpoint must also obey the Launch Streaming service by endpoint toggle (if disabled, the endpoint returns a clear disabled response).
  - Apply fan config on stream launch behavior: when the toggle is enabled and a fan config selected, apply that fan profile when this endpoint is called
- GET /list?token=... — list devices or other app-specific listing functionality
- Implementation detail: protect endpoints with the configured Token. Return appropriate status codes and helpful JSON error messages. If an endpoint is disabled by settings, return an informative error.

Concurrency & server management:
- The Flask server must run in a separate thread or process from the Tkinter mainloop. Provide a safe start/stop/restart implementation so GUI remains responsive.
- Ensure clean shutdown: Stop Flask, release any launched subprocesses, and update tray/menu state.
- When server starts, update tray menu Port: #### and GUI server status indicator.

Settings persistence (schema)
Use a JSON schema like:
{
  "port": 1482,
  "token": "changeme",
  "audio": {
    "enabled": true,
    "svv_path": "C:\\path\\to\\svcl.exe",
    "mappings": [
      { "label": "headphones", "device_id": "NVIDIA\\Device\\...", "use_for_streaming": true }
    ]
  },
  "fan": {
    "enabled": true,
    "fan_exe_path": "C:\\tools\\fancontrol.exe",
    "fan_config_path": "C:\\tools\\fanconfigs\\",
    "apply_on_stream_launch": false,
    "selected_config": "stream_profile_1"
  },
  "streaming": {
    "launch_streaming_by_endpoint": true,
    "appleTVMoniker": ""
  },
  "autostart": false
}
- Persist automatically on changes, and allow "Restore defaults" and "Export/Import settings" in the GUI.

Validation rules (enforced before server start):
- Port must be integer between 1024 and 65535 (unless user needs privileged port; if so, warn).
- Token must be non-empty.
- If audio.enabled == true then mappings array must have at least one row with non-empty label and device_id.
- If fan apply_on_stream_launch is true, selected_config must be chosen and available in parsed config list.
- If streaming.launch_streaming_by_endpoint is false, the GUI should reflect that /openStreaming is disabled and the Endpoints tab should show it as disabled.

Fan config parsing notes:
- If fancontrol.exe exposes a way to list configs, call it (e.g., fancontrol.exe --list or similar). If unknown, implement a parser function that reads the configured fan_config_path and extracts config names (e.g., directory listing or parsing a known config file format). If behavior is unclear, implement a TODO and provide a stub that returns an empty list and a clear error message in the GUI (this must be documented in README).

Windows audio control notes:
- For audio control, prefer using NirSoft svcl.exe (svv) for setting default device & volumes, or use Core Audio APIs via pycaw/comtypes if desired. By default bundle svcl.exe in the app; SvvPath UI lets an advanced user override to a local install.
- Provide clear error messages if the bundled exe is missing or fails.

Packaging & distribution:
- Provide a PyInstaller spec and instructions to create a single .exe that:
  - Includes the app icon, the bundled binaries (SoundVolumeView.exe/svcl.exe, optional fancontrol.exe), and settings default JSON.
  - Ensures tray icon and GUI resources are included.
- Provide a sample installer guidance (Inno Setup or similar) for placing the app in Program Files, creating Start Menu shortcut, and setting up autostart toggle.

Autostart implementation:
- Implement autostart toggle that:
  - On Windows: creates/removes a user-level registry HKCU\Software\Microsoft\Windows\CurrentVersion\Run\<AppName> entry OR creates/removes a shortcut in the Startup folder.
  - Reflect the autostart status in the GUI and persist in settings.

Tests & QA checklist:
- Deliver a set of manual QA steps and small test scripts (or unit tests) that confirm:
  1. Start the app, set Port and Token, start server. Verify http://127.0.0.1:<Port>/ responds with 200.
  2. Call /device/current and /volume/current to ensure valid JSON or controlled failure messages.
  3. Verify /switch?key=headphones&token=<token> maps to the configured device id and returns success.
  4. Toggle audio control off and confirm endpoints return disabled responses.
  5. Verify tray menu shows Port: <port> and Start/Stop/Restart switch states correctly.
  6. Test Open MyLocalAPI opens the default browser to the server root.
  7. Test Launch on Start toggles add/remove the autostart in Windows.
  8. Test /openStreaming when streaming.launch_streaming_by_endpoint is ON behaves correctly (routes audio and applies fan profile if enabled). When that setting is OFF, verify /openStreaming returns the disabled response.
  9. Package with PyInstaller and run the generated exe on a Windows 10/11 VM to verify included exes (SoundVolumeView) are present and endpoints function.

Deliverables:
1. Full Python source code, well-structured, with comments and docstrings.
2. requirements.txt
3. README.md with:
  - Setup and run steps
  - Packaging instructions (PyInstaller spec)
  - How to bundle svv/fancontrol
  - Known limitations and TODOs
4. Sample settings.json
5. Unit tests or test scripts and the manual QA checklist above.

Edge cases & helpful details:
- When the user changes port while server running, either ask to restart to apply change or auto-restart safely.
- If the requested port is already in use, return a clear error and suggest an available port.
- Make tray icon operations resilient: menu update when server spontaneously stops (crash), and show notifications for key events (server started, stopped, error).
- Keep GUI responsive by avoiding blocking calls on the Tkinter thread.