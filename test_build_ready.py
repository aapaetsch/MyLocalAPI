#!/usr/bin/env python3
"""
Comprehensive test script for MyLocalAPI before building executable

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE
Disclaimer: Provided AS IS. See LICENSE for details.
"""

import sys
import os
import requests
import time
import json
from typing import Dict, Any

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    modules_to_test = [
        'main', 'server', 'settings', 'utils', 'gui',
        'audio_control', 'fan_control', 'gaming_control', 'streaming'
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except Exception as e:
            print(f"  ❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Import test failed: {failed_imports}")
        return False
    
    print("✓ All imports successful")
    return True

def test_settings():
    """Test settings functionality"""
    print("\nTesting settings...")
    
    try:
        from settings import SettingsManager
        
        settings = SettingsManager()
        
        # Test basic get/set
        original_port = settings.get_setting('port', 1482)
        settings.set_setting('port', 5555, save=False)
        new_port = settings.get_setting('port', 1482)
        
        if new_port == 5555:
            print("  ✓ Settings get/set working")
            
            # Restore original
            settings.set_setting('port', original_port, save=False)
        else:
            print("  ❌ Settings get/set failed")
            return False
        
        # Test firewall rule management
        if hasattr(settings, 'ensure_firewall_rule'):
            print("  ✓ Firewall rule management available")
        else:
            print("  ❌ Firewall rule management missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Settings test failed: {e}")
        return False

def test_controllers():
    """Test controller initialization"""
    print("\nTesting controllers...")
    
    try:
        from settings import SettingsManager
        from audio_control import AudioController
        from fan_control import FanController
        from gaming_control import GamingController
        from streaming import StreamingController
        
        settings = SettingsManager()
        
        # Test audio controller
        try:
            audio = AudioController()
            print("  ✓ AudioController initialized")
        except Exception as e:
            print(f"  ⚠️  AudioController: {e}")
        
        # Test fan controller
        try:
            fan_exe = settings.get_setting('fan.fan_exe_path', '')
            fan_config = settings.get_setting('fan.fan_config_path', '')
            if fan_exe and fan_config:
                fan = FanController(fan_exe, fan_config)
                print("  ✓ FanController initialized")
            else:
                print("  ⚠️  FanController: Not configured")
        except Exception as e:
            print(f"  ⚠️  FanController: {e}")
        
        # Test gaming controller
        try:
            gaming = GamingController()
            print("  ✓ GamingController initialized")
        except Exception as e:
            print(f"  ❌ GamingController: {e}")
            return False
        
        # Test streaming controller
        try:
            streaming = StreamingController()
            print("  ✓ StreamingController initialized")
        except Exception as e:
            print(f"  ❌ StreamingController: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Controller test failed: {e}")
        return False

def test_server_startup():
    """Test server can start and respond"""
    print("\nTesting server startup...")
    
    try:
        from settings import SettingsManager
        from server import FlaskServer
        
        settings = SettingsManager()
        
        # Use a different port for testing
        test_port = 15482
        settings.set_setting('port', test_port, save=False)
        
        server = FlaskServer(settings)
        
        # Start server
        if server.start():
            print("  ✓ Server started")
            
            # Wait a moment
            time.sleep(1)
            
            # Test health endpoint
            try:
                response = requests.get(f'http://127.0.0.1:{test_port}/health', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'healthy':
                        print("  ✓ Health endpoint working")
                    else:
                        print("  ❌ Health endpoint returned wrong data")
                        return False
                else:
                    print(f"  ❌ Health endpoint returned {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"  ❌ Health endpoint test failed: {e}")
                return False
            finally:
                server.stop()
                print("  ✓ Server stopped")
            
            return True
        else:
            print("  ❌ Server failed to start")
            return False
            
    except Exception as e:
        print(f"  ❌ Server test failed: {e}")
        return False

def test_gui_imports():
    """Test GUI can be imported (but don't create windows)"""
    print("\nTesting GUI imports...")
    
    try:
        import customtkinter as ctk
        print("  ✓ CustomTkinter available")
        
        from gui import MainWindow
        print("  ✓ MainWindow can be imported")
        
        return True
        
    except Exception as e:
        print(f"  ❌ GUI test failed: {e}")
        return False

def test_elevation_functions():
    """Test elevation detection"""
    print("\nTesting elevation functions...")
    
    try:
        from utils import is_admin, check_and_elevate
        
        admin_status = is_admin()
        print(f"  Current admin status: {admin_status}")
        
        # Test check_and_elevate (but don't actually elevate)
        print("  ✓ Elevation functions available")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Elevation test failed: {e}")
        return False

def test_pyinstaller_compatibility():
    """Test PyInstaller compatibility"""
    print("\nTesting PyInstaller compatibility...")
    
    # Check for known problematic modules
    try:
        import win32gui
        import win32con
        import pystray
        import psutil
        print("  ✓ Windows modules available")
        
        # Check bundled files exist
        bundled_files = [
            'MyLocalAPI_app_icon_new.ico',
            'ctk_steel_blue_theme.json'
        ]
        
        for file_path in bundled_files:
            if os.path.exists(file_path):
                print(f"  ✓ {file_path} exists")
            else:
                print(f"  ⚠️  {file_path} missing (will affect bundle)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ PyInstaller compatibility test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 MyLocalAPI Pre-Build Testing")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("Settings Test", test_settings), 
        ("Controllers Test", test_controllers),
        ("Server Test", test_server_startup),
        ("GUI Test", test_gui_imports),
        ("Elevation Test", test_elevation_functions),
        ("PyInstaller Test", test_pyinstaller_compatibility)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    print("\n📊 Test Results:")
    print("-" * 20)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Ready for PyInstaller build.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues before building.")
        return 1

if __name__ == '__main__':
    sys.exit(main())