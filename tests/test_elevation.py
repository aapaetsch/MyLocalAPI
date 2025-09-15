#!/usr/bin/env python3
"""
Test script for admin privilege elevation functionality

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE
Disclaimer: Provided AS IS. See LICENSE for details.
"""

import sys
import os
import pathlib

# Ensure project root is on sys.path so imports work when running tests from the tests/ directory
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from utils import is_admin, check_and_elevate, request_admin_privileges
import logging

def test_elevation():
    """Test the elevation functionality"""
    print("=== Admin Privilege Elevation Test ===")
    print()

    # Setup basic logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Check current admin status
    admin_status = is_admin()
    print(f"Current admin status: {admin_status}")

    if '--elevated' in sys.argv:
        print("✅ This instance was started with elevated privileges!")
        print("The elevation functionality is working correctly.")
        return

    if admin_status:
        print("✅ Already running as administrator")
        print("The elevation check would skip automatic elevation.")
    else:
        print("❌ Not running as administrator")
        print()

        # Test the elevation check
        print("Testing elevation functionality...")
        print("This will show a prompt asking if you want to elevate.")
        print()

        try:
            should_exit = check_and_elevate(force=True, show_prompt=True)

            if should_exit:
                print("✅ Elevation was requested - this instance should now exit")
                print("A new elevated instance should start automatically")
                # Don't actually exit the test runner; return to let pytest continue
                return
            else:
                print("ℹ️ Elevation was not requested (user declined or error)")
        except Exception as e:
            print(f"❌ Error during elevation test: {e}")

    print()
    print("Test completed. If elevation was requested, check for the new elevated window.")

if __name__ == '__main__':
    test_elevation()
