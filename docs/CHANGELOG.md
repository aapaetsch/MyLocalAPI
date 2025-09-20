# Changelog
All notable changes to this project are (probably) documented in this file.
 
## [1.0.5] - 2025-09-18
- [Added]: API: `/audio/list` now returns an additional `labels` array containing configured device mapping labels; clients can pass `key=<label>` to `/audio/switch` to switch to a mapped device.
- [Changed]: `/audio/list` response clarified — returns `ok`, `devices`, `total`, and `labels` (an array of configured mapping labels).
- [Changed]: Documentation: `static/endpoints.json` synchronized with the server implementation so the GUI Endpoints tab reflects current route paths and parameter names (e.g., `/audio/switch`, `/audio/volume`, `/audio/list`).
- [Changed]: Gaming: the gaming launch endpoint accepts `steamid=<steam_appid>` when launching via Steam AppID.
- [Fixed]: Corrected mismatches between `static/endpoints.json` and `src/server.py` so GUI and docs show accurate endpoints and parameter names.
- [Verification]: Updated `static/endpoints.json` and confirmed `/audio/list` handler populates `labels` from `SettingsManager.get_audio_mappings()`; ran a light endpoint-sync/import smoke-check to ensure token-bearing routes are documented.
- [Note]: The API still accepts direct device ids (`id=<device_id>`) and mapping keys (`key=<label>`). Labels are preferred when available; change is backwards-compatible.
- [Added]: `src/win_dpi_mixin.py` (SmoothMoveMixin) — Windows-only message hook to pause heavy redraws while moving/resizing across displays with different DPI settings and to handle WM_DPICHANGED for relayout/rescaling; reduces visual tearing and lag when dragging the GUI between monitors.
 - [Added]: GUI: Added a "Logs" tab in the main window that displays application log files (searches logger file handlers and looks in common locations including the user's Roaming AppData `MyLocalAPI` folder).

## [1.0.4] - 2025-09-17
- [Added]: POST /gaming/games endpoint to add new game mappings (assigns UUID id and persists via SettingsManager).
- [Changed]: Health endpoint (`/health`) now reports the package application version (from `src.__version__`) instead of a hardcoded value.
- [Changed]: `static/endpoints.json` synchronized with implemented server endpoints:
  - Added Gaming Management entries (GET/POST `/gaming/games`, POST `/gaming/launch`).
  - Added audio-specific endpoints (`/audio/devices`, `/audio/set_default`, `/audio/current`) and aliases.
  - Added `/health` to the System group so the GUI displays the health endpoint.
  - Ensured all auth-protected endpoints include `token=<token>` in their `params` field.
- [Changed]: Improved CTk theme loading in the GUI: theme lookup now prefers bundled `assets/themes/` (via `resource_path`) and falls back to a programmatic theme object when files are missing; added debug logging around theme application to aid troubleshooting.
- [Fixed]: GUI endpoints loader updated to use `resource_path('static','endpoints.json')` so the Endpoints tab loads correctly from both dev and PyInstaller onefile builds.
 - Make resource lookups more resilient for one-file builds: theme and static file resolution now uses the same `resource_path` strategy so packaged assets (themes, `static/endpoints.json`) are discovered reliably at runtime.
- [Added]: Optional `showID` query parameter for streaming launch endpoints (`/streaming/launch`, `/openStreaming`). When provided, supported services will open the show's info/detail page directly (Netflix, Prime Video, Crunchyroll). The server forwards `showID` to `StreamingController.launch_service(service, show_id)` and the controller constructs service-specific URLs (e.g., `https://www.netflix.com/title/{showID}`).

- [Changed]: `StreamingController` updated to accept an optional `show_id` parameter and to construct service-specific deep links when `showID` is provided (Netflix, Prime Video, Crunchyroll). This improves launch behavior for services that support direct title links and is documented in `static/endpoints.json`.

- [Verification]: Updated `static/endpoints.json` to document the optional `showID` parameter for `/streaming/launch` and ran import smoke-tests for modified modules.

### Notes
- #### Files touched in this change:
  - `src/server.py` — health endpoint updated to use package version; POST `/gaming/games` added; other minor controller wiring updates.
  - `src/gui.py` — endpoints loader updated to use `resource_path` (previously changed in session).
  - `static/endpoints.json` — synchronized with server: added audio endpoints, gaming management, `/streaming/launch`, `/switch` alias, `/health` entry, and ensured token param presence for auth-protected routes.
  - `tools/validate_endpoints_auth.py` — validation helper (added for verification).


## [0.1.0] - 2025-09-15
- [Added]: Local HTTP API server (Flask) with endpoints for:
  - Health and status checks (e.g., `/health`, `/status`, `/diag`).
  - Audio control: list devices, get/set volume, switch default device, device mappings and streaming-target device selection.
  - Fan control: endpoints to query fan status and switch FanControl profiles (requires FanControl installed and configured).
  - Gaming: game mapping and launch endpoints (Steam AppID or executable path).
  - Streaming: launch streaming services and Apple TV handling.
- [Added]: Settings management via `SettingsManager` with JSON persistence and validation.
- [Added]: Windows integration utilities:
  - Admin-elevation helpers to detect and request UAC elevation when needed.
  - Firewall automation: add/update/remove a Windows Firewall rule named `MyLocalAPI` when the server port changes or when the server starts/stops.
  - Autostart helper for adding/removing app from Windows startup.
- [Added]: Desktop GUI (CustomTkinter/Tkinter) for settings and quick testing, plus a system tray icon (pystray) with start/stop controls.
- [Added]: Packaging and build tooling:
  - PyInstaller spec (`mylocalapi.spec`) with a robust spec-directory resolution fallback to avoid NameError when run programmatically.
  - `build.py` script to assist packaging and bundling extras (icons, svcl.exe guidance, version info).
  - Release zip creation process produced a distributable `dist` archive.
- [Added]: Tests and QA helpers: pre-build test scripts (`test_build_ready.py`, `test_elevation.py`, `test_admin_check.py`) and `tests/*` unit/manual QA scaffolding.
- [Added]: Repo metadata: top-file headers (Author/Date/License/Disclaimer) added across source and test files.
- [Changed]: Improve resilience of file/icon loading and CTk theme fallback in the GUI.
- [Changed]: Settings save / port-change flows now automatically trigger firewall rule updates.
- [Changed]: Spec file no longer assumes `__file__` is defined; falls back to argv or cwd when necessary.
- [Fixed]: PyInstaller spec NameError when executed programmatically (spec now safely resolves its directory).
- [Fixed]: Minor server binding and endpoint stability fixes observed during build/test runs.
- [Added]: Built a Windows executable with PyInstaller (produced `dist\MyLocalAPI.exe`) and created a timestamped release ZIP including `dist` and key extras (README, LICENSE, settings.json, PYINSTALLER_GUIDE.md, and optional `scripts/svcl-x64`).
- [Added]: Administrator privileges are required for firewall manipulation and FanControl profile switching; the app will detect non-elevated runs and can restart elevated on user confirmation.
- [Added]: Token-based access is enforced on API endpoints; ensure you change the default token before exposing the server on a network.

---

For changes after v0.1.0, add entries above under the `Unreleased` or next version heading.


