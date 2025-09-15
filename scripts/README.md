Release packaging helpers

create_release.ps1

Usage examples (PowerShell):

# Create a timestamped ZIP (default)
.\scripts\create_release.ps1

# Create a ZIP for specific version and include svcl bundle
.\scripts\create_release.ps1 -Version "0.1.0" -IncludeSVCL

# Overwrite existing ZIP if present
.\scripts\create_release.ps1 -Version "0.1.0" -IncludeSVCL -Overwrite

Notes:
- The script expects a `dist` folder in the project root (output from PyInstaller). If not present, run the build first.
- Extras included by default: settings.json, README.md, LICENSE, PYINSTALLER_GUIDE.md
- When `-IncludeSVCL` is set, the script will copy `scripts\svcl-x64` into the release if it exists.
