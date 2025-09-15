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
import pathlib
import requests
import time
import json
from typing import Dict, Any

# Ensure project root is on sys.path so imports work when running tests from the tests/ directory
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

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

    # Use an assertion so pytest treats failures properly and the test function returns None
    assert not failed_imports, f"Import test failed: {failed_imports}"

    print("✓ All imports successful")

if __name__ == '__main__':
    try:
        test_imports()
    except AssertionError as e:
        print(e)
        import sys
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import sys
        sys.exit(1)
    else:
        print("All imports successful")
        import sys
        sys.exit(0)
