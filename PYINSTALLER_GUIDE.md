# MyLocalAPI - PyInstaller Build Instructions

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE (GNU GPL v3.0)
Disclaimer: Provided AS IS. See README.md 'AS IS Disclaimer' for details.

## Prerequisites

### 1. Python Environment
- **Python 3.9+** recommended
- **Virtual environment** strongly recommended
- All dependencies installed via `pip install -r requirements.txt`

### 2. Windows Dependencies
- **Windows 10/11** (64-bit recommended)
- **Microsoft Visual C++ Redistributable** (usually pre-installed)
- **Windows SDK** (for win32 modules, usually included with Python)

### 3. Required System Tools
- **PyInstaller**: `pip install pyinstaller`
- **Windows PowerShell** (for build scripts)

## Build Process

### Method 1: Automated Build (Recommended)

1. **Activate virtual environment:**
   ```powershell
   .\venv\Scripts\activate.ps1
   ```

2. **Install all dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Run pre-build tests:**
   ```powershell
   python test_build_ready.py
   ```

4. **Run automated build:**
   ```powershell
   python build.py
   ```

   **Options:**
   - `python build.py --type onefile` - Single executable file
   - `python build.py --type onedir` - Directory with dependencies
   - `python build.py --skip-tests` - Skip unit tests
   - `python build.py --clean-only` - Clean build directories only

### Method 2: Manual PyInstaller

1. **Activate virtual environment:**
   ```powershell
   .\venv\Scripts\activate.ps1
   ```

2. **Clean previous builds:**
   ```powershell
   Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
   ```

3. **Run PyInstaller:**
   ```powershell
   pyinstaller mylocalapi.spec
   ```

   **Or directly:**
   ```powershell
   pyinstaller --onefile --noconsole --icon=MyLocalAPI_app_icon_new.ico --add-data "scripts;scripts" --add-data "MyLocalAPI_app_icon_new.ico;." --add-data "ctk_steel_blue_theme.json;." main.py
   ```

## Build Output

### Single File Build (`--onefile`)
- **Output:** `dist\MyLocalAPI.exe`
- **Size:** ~50-80 MB
- **Startup:** Slightly slower (extracts to temp)
- **Distribution:** Easiest - single file

### Directory Build (`--onedir`) 
- **Output:** `dist\MyLocalAPI\` folder
- **Size:** ~100-150 MB (many files)
- **Startup:** Faster
- **Distribution:** Requires entire folder

## Manual Build Steps

### 1. Prepare Environment

```powershell
# Navigate to project directory
cd "C:\path\to\MyLocalAPI"

# Activate virtual environment
.\venv\Scripts\activate.ps1

# Install/update dependencies
pip install -r requirements.txt

# Verify environment
python test_build_ready.py
```

### 2. Configure Build

Edit `mylocalapi.spec` if needed:
- Change build type (onefile vs onedir)
- Adjust excluded modules for size optimization
- Modify data files to include
- Update icon path

### 3. Build Executable

```powershell
# Clean previous builds
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

# Build with spec file
pyinstaller mylocalapi.spec

# Or build manually with full command
pyinstaller --onefile --noconsole --name "MyLocalAPI" --icon "MyLocalAPI_app_icon_new.ico" --add-data "scripts;scripts" --add-data "*.ico;." --add-data "*.json;." --add-data "*.png;." --hidden-import "win32gui" --hidden-import "win32con" --hidden-import "win32process" --hidden-import "win32api" --hidden-import "pystray._win32" --hidden-import "customtkinter" --exclude-module "matplotlib" --exclude-module "numpy" --exclude-module "scipy" main.py
```

### 4. Test Executable

```powershell
# Test the built executable
.\dist\MyLocalAPI.exe

# Or if directory build:
.\dist\MyLocalAPI\MyLocalAPI.exe
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError at Runtime**
   - Add missing modules to `hiddenimports` in spec file
   - Use `--hidden-import modulename` flag

2. **File Not Found Errors**
   - Add missing files to `datas` in spec file  
   - Use `--add-data "source;dest"` flag

3. **Large Executable Size**
   - Add more modules to `excludes` in spec file
   - Use `--exclude-module modulename` flag
   - Consider directory build instead of onefile

4. **Slow Startup**
   - Use directory build (`--onedir`) instead of `--onefile`
   - Optimize excluded modules

5. **Icon Issues**
   - Verify icon file exists and is valid ICO format
   - Use absolute path to icon file
   - Convert PNG to ICO if needed

6. **Missing Dependencies**
   - Run `python test_build_ready.py` to verify all imports
   - Check virtual environment is activated
   - Install missing packages with pip

### Advanced Troubleshooting

1. **Debug Mode:**
   ```powershell
   pyinstaller --debug=all mylocalapi.spec
   ```

2. **Check Dependencies:**
   ```powershell
   pyi-archive_viewer dist\MyLocalAPI.exe
   ```

3. **Module Analysis:**
   ```powershell
   pyi-makespec --onefile main.py
   # Then edit the generated spec file
   ```

## Distribution

### For End Users

1. **Single File Distribution:**
   - Distribute `dist\MyLocalAPI.exe`
   - Include `README.md` and `QUICKSTART.txt`
   - Consider creating installer with Inno Setup

2. **Directory Distribution:**  
   - Zip entire `dist\MyLocalAPI\` folder
   - Include documentation in zip root
   - Provide extraction instructions

3. **Additional Files:**
   - Sample `settings.json`
   - Network setup guide (`NETWORK_SETUP.md`)
   - Quick start guide
   - License information

### Testing Distribution

1. **Clean System Test:**
   - Test on Windows system without Python installed
   - Test with Windows Defender enabled
   - Test with different user privilege levels

2. **Functionality Test:**
   - Verify all features work (audio, gaming, fan control)
   - Test network access from other devices
   - Test administrator privilege elevation

3. **Performance Test:**
   - Measure startup time
   - Check memory usage
   - Verify no resource leaks

## Version Management

Update version information in:
- `version_info.py` (for Windows properties)
- `build.py` (version constant)
- `main.py` (application version)
- `README.md` (release notes)

## Security Considerations

- Built executable may trigger antivirus warnings (false positive)
- Code signing recommended for distribution
- Test with Windows SmartScreen enabled
- Consider excluding from Windows Defender if needed

## Optimization Tips

### Size Reduction
- Exclude unused modules (`matplotlib`, `numpy`, etc.)
- Remove test files and development dependencies
- Use UPX compression (included in PyInstaller)

### Performance
- Use directory build for faster startup
- Pre-compile Python bytecode
- Optimize imports in main modules

### Compatibility
- Build on oldest supported Windows version
- Test on different Windows configurations
- Include all required Visual C++ redistributables

## Final Checklist

Before distributing:

- [ ] All tests pass (`python test_build_ready.py`)
- [ ] Executable starts and shows system tray icon
- [ ] GUI opens and all tabs work
- [ ] Server starts and responds to HTTP requests
- [ ] Firewall rule management works
- [ ] Elevation prompts work correctly
- [ ] All features tested (audio, gaming, fan control)
- [ ] Network access tested from other devices
- [ ] Clean system test completed
- [ ] Documentation updated
- [ ] Version information correct
- [ ] License and legal information included