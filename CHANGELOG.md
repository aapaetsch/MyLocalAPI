# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2025-09-15
### Added
- Local HTTP API server (Flask) with endpoints for:
  - Health and status checks (e.g., `/health`, `/status`, `/diag`).
  - Audio control: list devices, get/set volume, switch default device, device mappings and streaming-target device selection.
  - Fan control: endpoints to query fan status and switch FanControl profiles (requires FanControl installed and configured).
  - Gaming: game mapping and launch endpoints (Steam AppID or executable path).
  - Streaming: launch streaming services and Apple TV handling.
- Settings management via `SettingsManager` with JSON persistence and validation.
- Windows integration utilities:
  - Admin-elevation helpers to detect and request UAC elevation when needed.
  - Firewall automation: add/update/remove a Windows Firewall rule named `MyLocalAPI` when the server port changes or when the server starts/stops.
  - Autostart helper for adding/removing app from Windows startup.
- Desktop GUI (CustomTkinter/Tkinter) for settings and quick testing, plus a system tray icon (pystray) with start/stop controls.
- Packaging and build tooling:
  - PyInstaller spec (`mylocalapi.spec`) with a robust spec-directory resolution fallback to avoid NameError when run programmatically.
  - `build.py` script to assist packaging and bundling extras (icons, svcl.exe guidance, version info).
  - Release zip creation process produced a distributable `dist` archive.
- Tests and QA helpers: pre-build test scripts (`test_build_ready.py`, `test_elevation.py`, `test_admin_check.py`) and `tests/*` unit/manual QA scaffolding.
- Repo metadata: top-file headers (Author/Date/License/Disclaimer) added across source and test files.

### Changed
- Improve resilience of file/icon loading and CTk theme fallback in the GUI.
- Settings save / port-change flows now automatically trigger firewall rule updates.
- Spec file no longer assumes `__file__` is defined; falls back to argv or cwd when necessary.

### Fixed
- PyInstaller spec NameError when executed programmatically (spec now safely resolves its directory).
- Minor server binding and endpoint stability fixes observed during build/test runs.

### Packaging
- Built a Windows executable with PyInstaller (produced `dist\MyLocalAPI.exe`) and created a timestamped release ZIP including `dist` and key extras (README, LICENSE, settings.json, PYINSTALLER_GUIDE.md, and optional `scripts/svcl-x64`).

### Security & Privileges
- Administrator privileges are required for firewall manipulation and FanControl profile switching; the app will detect non-elevated runs and can restart elevated on user confirmation.
- Token-based access is enforced on API endpoints; ensure you change the default token before exposing the server on a network.

### Known issues
- Some optional dependencies may not be present in the environment (e.g., CustomTkinter, pystray, Pillow). The app falls back where possible, but full GUI/tray/icon functionality requires those packages.
- Hidden-import warning during PyInstaller build: legacy reference to `requests.packages.urllib3` may appear as a non-fatal warning. It does not block the build but can be cleaned from the spec if desired.
- Firewall and FanControl behavior require testing while running elevated; tests performed non-elevated will produce expected warnings/failures for those operations.

### Verification / How to test
1. Install dependencies in a virtual environment: `python -m venv venv` then `venv\Scripts\activate` and `pip install -r requirements.txt`.
2. Run pre-build checks: `python test_build_ready.py` and `python test_elevation.py` to verify imports and elevation behavior.
3. Start the application locally: `python main.py` and visit `http://127.0.0.1:<port>/` (default port 1482).
4. Exercise the API endpoints (see `endpoints.json` and `README.md`) and verify expected responses.
5. To verify packaging: run `pyinstaller mylocalapi.spec` in the venv and inspect `dist\MyLocalAPI.exe`.

### Credits
- Author: Aidan Paetsch
- Contributors: (project history before v0.1.0)

---

For changes after v0.1.0, add entries above under the `Unreleased` or next version heading.
