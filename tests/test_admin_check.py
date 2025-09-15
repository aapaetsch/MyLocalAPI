#!/usr/bin/env python3
"""
Test fan control admin requirements

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE
Disclaimer: Provided AS IS. See LICENSE for details.
"""

import sys
import pathlib
# Ensure project root is on sys.path so imports work when running tests from the tests/ directory
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fan_control import FanController
from settings import SettingsManager
from utils import is_admin

def test_admin_requirements():
    print("=== Fan Control Admin Requirements Test ===")

    settings = SettingsManager()
    fan_exe = settings.get_setting('fan.fan_exe_path', '')
    fan_config = settings.get_setting('fan.fan_config_path', '')

    print(f"Current process admin status: {is_admin()}")
    print(f"Fan exe path: {fan_exe}")
    print(f"Fan config path: {fan_config}")

    controller = FanController(fan_exe, fan_config)

    print(f"Fan control configured: {controller.is_configured()}")
    print(f"Fan control requires admin: {controller.requires_admin()}")
    print(f"Can switch configs: {controller.can_switch_configs()}")
    print(f"FanControl running: {controller.is_running()}")

    if not controller.can_switch_configs():
        print("\n❌ ADMIN REQUIRED:")
        print("Fan configuration switching requires administrator privileges.")
        print("To enable fan control, please:")
        print("1. Close the current MyLocalAPI application")
        print("2. Right-click on the application or command prompt")
        print("3. Select 'Run as administrator'")
        print("4. Restart MyLocalAPI")
    else:
        print("\n✅ ADMIN PRIVILEGES DETECTED:")
        print("Fan configuration switching should work correctly.")
        try:
            print("\nTesting config switch...")
            result = controller.set_fan_profile('flat30')
            print(f"Config switch result: {result}")
        except Exception as e:
            print(f"Config switch error: {e}")


if __name__ == '__main__':
    test_admin_requirements()
