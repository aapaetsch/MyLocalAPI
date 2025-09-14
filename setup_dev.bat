@echo off
REM MyLocalAPI Development Environment Setup
REM Automatically creates venv and installs dependencies

echo MyLocalAPI - Development Environment Setup
echo ============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

echo ✓ Python found
python --version
echo.

REM Show current directory
echo Current directory: %CD%
echo.

REM Check if we're already in a virtual environment
python -c "import sys; exit(0 if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else 1)" >nul 2>&1
if %errorlevel% equ 0 (
    echo WARNING: Already in a virtual environment
    echo Continuing anyway...
    echo.
)

REM Remove existing venv if it exists and seems corrupted
if exist "venv\" (
    echo Existing venv folder found. Checking if it's valid...
    if not exist "venv\Scripts\activate.bat" (
        echo Removing corrupted venv folder...
        rmdir /s /q "venv" >nul 2>&1
    )
)

REM Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo Creating virtual environment...
    echo Running: python -m venv venv
    python -m venv venv
    if %errorlevel% neq 0 (
        echo.
        echo ❌ ERROR: Failed to create virtual environment
        echo.
        echo Troubleshooting steps:
        echo 1. Check if Python was installed with 'Add to PATH' option
        echo 2. Try running as Administrator
        echo 3. Check if path has spaces or special characters
        echo 4. Temporarily disable antivirus
        echo 5. Try manual creation: python -m venv test_venv
        echo.
        echo Current Python executable: 
        where python
        echo.
        echo Python modules available:
        python -c "help('modules')" 2>nul | findstr venv
        echo.
        pause
        exit /b 1
    )
    echo ✓ Virtual environment created
) else (
    echo ✓ Virtual environment already exists
)

REM Check if activation script exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment seems incomplete
    echo Missing: venv\Scripts\activate.bat
    echo Try deleting the venv folder and running this script again
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    echo The venv was created but activation failed
    echo Try running manually: venv\Scripts\activate.bat
    pause
    exit /b 1
)

REM Verify we're in the virtual environment
python -c "import sys; print('Virtual env active:', hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))"

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo WARNING: Failed to upgrade pip, continuing anyway...
)

REM Check if requirements.txt exists
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found in current directory
    echo Make sure you're in the MyLocalAPI project folder
    echo Current files:
    dir /b
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ ERROR: Failed to install some dependencies
    echo This might be due to:
    echo 1. Network connection issues
    echo 2. Missing build tools (Visual Studio Build Tools)
    echo 3. Incompatible package versions
    echo.
    echo Try installing manually: pip install -r requirements.txt
    pause
    exit /b 1
) else (
    echo ✅ All dependencies installed successfully!
)

echo.
echo 🎉 Development environment setup complete!
echo.
echo Next steps:
echo 1. Run the application: python main.py
echo 2. Build executable: python build.py
echo 3. Run tests: python tests\test_unit.py
echo 4. When done: deactivate
echo.
echo Virtual environment is now active.
echo Python executable: 
where python
echo.
pause