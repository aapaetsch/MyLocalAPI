# Changelog

All notable changes to this project are documented in this file.

## [1.0.4] - 2025-09-17
### Launched
- The following changes have been released in version 1.0.4:
### Added
- POST /gaming/games endpoint to add new game mappings (assigns UUID id and persists via SettingsManager).

### Changed
- Health endpoint (`/health`) now reports the package application version (from `src.__version__`) instead of a hardcoded value.
- `static/endpoints.json` synchronized with implemented server endpoints:
  - Added Gaming Management entries (GET/POST `/gaming/games`, POST `/gaming/launch`).
  - Added audio-specific endpoints (`/audio/devices`, `/audio/set_default`, `/audio/current`) and aliases.
  - Added `/health` to the System group so the GUI displays the health endpoint.
  - Ensured all auth-protected endpoints include `token=<token>` in their `params` field.
 - Improved CTk theme loading in the GUI: theme lookup now prefers bundled `assets/themes/` (via `resource_path`) and falls back to a programmatic theme object when files are missing; added debug logging around theme application to aid troubleshooting.

### Fixed
- GUI endpoints loader updated to use `resource_path('static','endpoints.json')` so the Endpoints tab loads correctly from both dev and PyInstaller onefile builds.
 - Make resource lookups more resilient for one-file builds: theme and static file resolution now uses the same `resource_path` strategy so packaged assets (themes, `static/endpoints.json`) are discovered reliably at runtime.

### Verification
- Ran import checks for modified modules and a headless server smoke test that confirmed `/health` returns the package version.
- Ran a validation script to confirm every `@self._require_auth` route is present in `static/endpoints.json` and includes `token` in params.

### Notes
- A small validator script was added at `tools/validate_endpoints_auth.py` to assist in verifying consistency between `src/server.py` and `static/endpoints.json`.

### Files touched in this change
- `src/server.py` — health endpoint updated to use package version; POST `/gaming/games` added; other minor controller wiring updates.
- `src/gui.py` — endpoints loader updated to use `resource_path` (previously changed in session).
- `static/endpoints.json` — synchronized with server: added audio endpoints, gaming management, `/streaming/launch`, `/switch` alias, `/health` entry, and ensured token param presence for auth-protected routes.
- `tools/validate_endpoints_auth.py` — validation helper (added for verification).

### Added
- Optional `showID` query parameter for streaming launch endpoints (`/streaming/launch`, `/openStreaming`). When provided, supported services will open the show's info/detail page directly (Netflix, Prime Video, Crunchyroll). The server forwards `showID` to `StreamingController.launch_service(service, show_id)` and the controller constructs service-specific URLs (e.g., `https://www.netflix.com/title/{showID}`).

### Changed
- `StreamingController` updated to accept an optional `show_id` parameter and to construct service-specific deep links when `showID` is provided (Netflix, Prime Video, Crunchyroll). This improves launch behavior for services that support direct title links and is documented in `static/endpoints.json`.

### Verification
- Updated `static/endpoints.json` to document the optional `showID` parameter for `/streaming/launch` and ran import smoke-tests for modified modules.


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
