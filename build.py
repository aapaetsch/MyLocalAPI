#!/usr/bin/env python3
"""
Build script for MyLocalAPI
Automates the packaging process with PyInstaller and dependency bundling

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE
Disclaimer: Provided AS IS. See LICENSE for details.
"""

import os
import sys
import subprocess
import shutil
import requests
import zipfile
import tempfile
from pathlib import Path
import argparse

class MyLocalAPIBuilder:
    """Handles building and packaging MyLocalAPI"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.dist_dir = self.project_root / 'dist'
        self.build_dir = self.project_root / 'build'
        self.scripts_dir = self.project_root / 'scripts'
        
    def clean_build_dirs(self):
        """Clean existing build directories"""
        print("🧹 Cleaning build directories...")
        
        dirs_to_clean = [self.dist_dir, self.build_dir]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"   Removed: {dir_path}")
        
        print("✓ Build directories cleaned")
    
    def check_dependencies(self):
        """Check if all required dependencies are installed"""
        print("📦 Checking dependencies...")
        
        # Check if we're in a virtual environment (recommended)
        import sys
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        
        if not in_venv:
            print("⚠️  WARNING: Not running in a virtual environment")
            print("   Recommended: Create venv to avoid conflicts")
            print("   Run: python -m venv venv && venv\\Scripts\\activate")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                return False
        else:
            print("✓ Running in virtual environment")
        
        # Map pip package names to their canonical import names
        package_import_map = {
            'Flask': 'flask',
            'Flask-Cors': 'flask_cors',
            'pystray': 'pystray',
            'Pillow': 'PIL',
            'requests': 'requests',
            'psutil': 'psutil',
            'pyinstaller': 'PyInstaller'
        }

        missing_packages = []
        for package, import_name in package_import_map.items():
            try:
                __import__(import_name)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            print(f"❌ Missing packages: {', '.join(missing_packages)}")
            print("Please install them with: pip install -r requirements.txt")
            return False
        
        print("✓ All dependencies are installed")
        return True
    
    def download_svcl_exe(self):
        """Download and bundle svcl.exe if not present"""
        svcl_dir = self.scripts_dir / 'svcl-x64'
        svcl_exe = svcl_dir / 'svcl.exe'
        
        if svcl_exe.exists():
            print("✓ svcl.exe already present")
            return True
        
        print("📥 Downloading svcl.exe (SoundVolumeCommandLine)...")
        
        # Create directories
        svcl_dir.mkdir(parents=True, exist_ok=True)
        
        # Download URL for svcl.exe (this would need to be the actual URL)
        # Note: In a real implementation, you'd need the actual download URL
        svcl_url = "https://www.nirsoft.net/utils/svcl-x64.zip"
        
        try:
            # This is a placeholder - actual implementation would need real download logic
            print("⚠️  Manual step required:")
            print(f"   Please download svcl.exe from NirSoft and place it in: {svcl_dir}")
            print("   URL: https://www.nirsoft.net/utils/sound_volume_command_line.html")
            print("   Extract svcl.exe to the scripts/svcl-x64/ directory")
            
            # Check if user completed manual step
            if not svcl_exe.exists():
                response = input("Have you downloaded and placed svcl.exe? (y/N): ")
                if response.lower() != 'y':
                    print("❌ svcl.exe is required for audio control functionality")
                    return False
            
            if svcl_exe.exists():
                print("✓ svcl.exe found and ready for bundling")
                return True
            else:
                print("❌ svcl.exe still not found")
                return False
                
        except Exception as e:
            print(f"❌ Error setting up svcl.exe: {e}")
            return False
    
    def create_version_info(self):
        """Create version info file for Windows executable"""
        # Version set to 1.0.4 for this release
        version_content = '''# UTF-8
#
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1, 0, 4, 0),
        prodvers=(1, 0, 4, 0),
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    u'040904B0',
                    [StringStruct(u'CompanyName', u'MyLocalAPI'),
                     StringStruct(u'FileDescription', u'Local HTTP server for PC control'),
                     StringStruct(u'FileVersion', u'1.0.4.0'),
                     StringStruct(u'InternalName', u'MyLocalAPI'),
                     StringStruct(u'LegalCopyright', u'Copyright (C) 2024'),
                     StringStruct(u'OriginalFilename', u'MyLocalAPI.exe'),
                     StringStruct(u'ProductName', u'MyLocalAPI'),
                     StringStruct(u'ProductVersion', u'1.0.4.0')])
            ]), 
        VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
    ]
)
'''

        version_file = self.project_root / 'version_info.py'
        with open(version_file, 'w', encoding='utf-8') as f:
                f.write(version_content)

        print("✓ Version info file created")
        return version_file
    
    def create_icon(self):
        """Create application icon"""
        print("🎨 Checking application icon...")
        
        existing_icon = self.project_root / 'MyLocalAPI_app_icon_new.ico'
        if existing_icon.exists():
            print("✓ Using existing application icon")
            return existing_icon
        
        # Could not find or create an icon - return None
        print("⚠️  Could not find or create an application icon")
        return None
    
    def build_executable(self, build_type='onefile'):
        """Build executable using PyInstaller"""
        print(f"🔨 Building executable ({build_type})...")
        
        args = [
            'pyinstaller',
            '--clean',
            '--noconfirm',
        ]
        
        if build_type == 'onefile':
            args.append('--onefile')
        elif build_type == 'onedir':
            args.append('--onedir')
        
        args.append('--noconsole')  # No console window
        
        if self.scripts_dir.exists():
            args.extend(['--add-data', f'{self.scripts_dir};scripts'])
        
        icon_path = self.project_root / 'MyLocalAPI_app_icon_new.ico'
        if not icon_path.exists():
            icon_path = self.project_root / 'icon.ico'
        
        if icon_path.exists():
            args.extend(['--icon', str(icon_path)])
            # Also bundle the icon file into the onefile archive so it is
            # available at runtime via sys._MEIPASS. This is required when
            # using --onefile so runtime code can load the icon (e.g. for
            # tkinter.root.iconbitmap or pystray).
            args.extend(['--add-data', f'{str(icon_path)};.'])

        # Ensure the produced executable has a consistent name (match spec)
        # Without this, PyInstaller defaults to the script basename (main.exe)
        # and the packaging step then copies/renames it to MyLocalAPI.exe which
        # results in both main.exe and MyLocalAPI.exe appearing in dist/.
        args.extend(['--name', 'MyLocalAPI'])
        
        version_file = self.project_root / 'version_info.py'
        if version_file.exists():
            args.extend(['--version-file', str(version_file)])
        
        excludes = [
            'matplotlib', 'numpy', 'scipy', 'pandas', 'jupyter',
            'notebook', 'IPython', 'test', 'tests', 'unittest', 'xml.etree'
        ]
        
        for exclude in excludes:
            args.extend(['--exclude-module', exclude])
        
        hidden_imports = [
            'win32gui', 'win32con', 'win32process', 'win32com.shell',
            'pystray._win32', 'PIL._tkinter_finder', 'psutil'
        ]
        
        for hidden in hidden_imports:
            args.extend(['--hidden-import', hidden])
        
        args.append('main.py')
        
        try:
            print(f"Running: {' '.join(args)}")
            result = subprocess.run(args, check=True, capture_output=True, text=True)
            print("✓ Executable built successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ PyInstaller failed:")
            print(f"   stdout: {e.stdout}")
            print(f"   stderr: {e.stderr}")
            return False
    
    def create_distribution_package(self):
        """Create distribution package with documentation"""
        print("📦 Creating distribution package...")
        
        # Find the built executable
        exe_path = None
        if (self.dist_dir / 'MyLocalAPI.exe').exists():
            exe_path = self.dist_dir / 'MyLocalAPI.exe'
        elif (self.dist_dir / 'main.exe').exists():
            exe_path = self.dist_dir / 'main.exe'
        elif (self.dist_dir / 'MyLocalAPI').exists(): 
            exe_path = self.dist_dir / 'MyLocalAPI'
        
        if not exe_path:
            print("❌ Could not find built executable")
            return False
        
        package_dir = self.dist_dir / 'MyLocalAPI-Package'
        package_dir.mkdir(exist_ok=True)
        
        if exe_path.is_file():
            shutil.copy2(exe_path, package_dir / 'MyLocalAPI.exe')
        else:
            shutil.copytree(exe_path, package_dir / 'MyLocalAPI', dirs_exist_ok=True)
        
        docs_to_copy = [
            ('README.md', 'README.md'),
            ('LICENSE', 'LICENSE.txt'),
            ('settings.json', 'settings-sample.json'),
        ]
        
        for src, dst in docs_to_copy:
            src_path = self.project_root / src
            if src_path.exists():
                shutil.copy2(src_path, package_dir / dst)
        
        # Create quick start guide
        quickstart_content = """MyLocalAPI - Quick Start Guide
=============================

1. Run MyLocalAPI.exe
2. The app will start in the system tray
3. Right-click the tray icon and select "Settings..."
4. Configure your audio devices in the Settings tab
5. Click "Start" to begin the HTTP server
6. Test with: http://127.0.0.1:1482/

For full documentation, see README.md

API Examples:
- Switch audio: GET /switch?key=headphones&token=changeme  
- Set volume: GET /volume?percent=50&token=changeme
- Get current: GET /device/current?token=changeme

Change the token in settings for security!
"""
        
        with open(package_dir / 'QUICKSTART.txt', 'w') as f:
            f.write(quickstart_content)
        
        print(f"✓ Distribution package created: {package_dir}")
        return True
    
    def run_tests(self):
        """Run unit tests before building"""
        print("🧪 Running tests...")
        
        test_file = self.project_root / 'tests' / 'test_unit.py'
        if not test_file.exists():
            print("⚠️  No unit tests found, skipping...")
            return True
        
        try:
            result = subprocess.run([sys.executable, str(test_file)], 
                                  capture_output=True, text=True, check=True)
            print("✓ All tests passed")
            return True
        except subprocess.CalledProcessError as e:
            print("❌ Tests failed:")
            print(e.stdout)
            print(e.stderr)
            return False
    
    def build_all(self, build_type='onefile', skip_tests=False):
        """Run complete build process"""
        print("🚀 Starting MyLocalAPI build process...")
        print("=" * 50)
        
        self.clean_build_dirs()
        if not self.check_dependencies():
            return False
        
        if not skip_tests and not self.run_tests():
            print("❌ Build failed: Tests did not pass")
            return False
        
        if not self.download_svcl_exe():
            print("⚠️  Continuing without svcl.exe - audio features may not work")
        
        self.create_version_info()
        self.create_icon()
        
        if not self.build_executable(build_type):
            return False
        
        if not self.create_distribution_package():
            return False
        
        print("\n🎉 Build completed successfully!")
        print(f"📁 Output directory: {self.dist_dir}")
        print("\nNext steps:")
        print("1. Test the executable on a clean Windows system")
        print("2. Create an installer with Inno Setup (optional)")
        print("3. Distribute to users")
        
        return True

def main():
    """Main build script entry point"""
    parser = argparse.ArgumentParser(description='Build MyLocalAPI executable')
    parser.add_argument('--type', choices=['onefile', 'onedir'], default='onefile',
                        help='Build type: single file or directory (default: onefile)')
    parser.add_argument('--skip-tests', action='store_true',
                        help='Skip running unit tests before build')
    parser.add_argument('--clean-only', action='store_true',
                        help='Only clean build directories and exit')
    
    args = parser.parse_args()
    
    builder = MyLocalAPIBuilder()
    
    if args.clean_only:
        builder.clean_build_dirs()
        return 0
    
    success = builder.build_all(build_type=args.type, skip_tests=args.skip_tests)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())