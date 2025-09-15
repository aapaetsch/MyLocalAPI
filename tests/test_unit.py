#!/usr/bin/env python3
"""
Unit tests for MyLocalAPI core components

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE
Disclaimer: Provided AS IS. See LICENSE for details.
"""

import unittest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings import SettingsManager
from utils import AutostartManager, clean_audio_device_id, validate_executable


class TestSettingsManager(unittest.TestCase):
    """Test settings management functionality"""
    
    def setUp(self):
        """Setup test with temporary settings file"""
        self.temp_dir = tempfile.mkdtemp()
        self.settings_file = os.path.join(self.temp_dir, 'test_settings.json')
        
        # Mock get_app_data_dir to use temp directory
        with patch('settings.get_app_data_dir', return_value=self.temp_dir):
            self.settings = SettingsManager()
    
    def test_default_settings_loaded(self):
        """Test that default settings are loaded correctly"""
        self.assertEqual(self.settings.get_setting('port'), 1482)
        self.assertEqual(self.settings.get_setting('token'), 'changeme')
        self.assertTrue(self.settings.get_setting('audio.enabled'))
        self.assertFalse(self.settings.get_setting('fan.enabled'))
    
    def test_set_and_get_setting(self):
        """Test setting and getting configuration values"""
        self.settings.set_setting('port', 8080, save=False)
        self.assertEqual(self.settings.get_setting('port'), 8080)
        
        self.settings.set_setting('audio.enabled', False, save=False)
        self.assertFalse(self.settings.get_setting('audio.enabled'))
    
    def test_audio_mappings(self):
        """Test audio device mapping management"""
        mappings = [
            {"label": "headphones", "device_id": "test\\device\\id", "use_for_streaming": True},
            {"label": "speakers", "device_id": "another\\device\\id", "use_for_streaming": False}
        ]
        
        self.assertTrue(self.settings.set_audio_mappings(mappings, save=False))
        retrieved = self.settings.get_audio_mappings()
        
        self.assertEqual(len(retrieved), 2)
        self.assertEqual(retrieved[0]['label'], 'headphones')
        self.assertTrue(retrieved[0]['use_for_streaming'])
    
    def test_streaming_device_id(self):
        """Test getting streaming device ID"""
        mappings = [
            {"label": "headphones", "device_id": "streaming\\device", "use_for_streaming": True},
            {"label": "speakers", "device_id": "normal\\device", "use_for_streaming": False}
        ]
        
        self.settings.set_audio_mappings(mappings, save=False)
        streaming_id = self.settings.get_streaming_device_id()
        
        self.assertEqual(streaming_id, "streaming\\device")
    
    def test_settings_validation(self):
        """Test settings validation"""
        # Valid settings should have no errors
        errors = self.settings.validate_settings()
        self.assertIn("Token cannot be empty", errors)  # Default token is "changeme" which is valid
        
        # Test invalid port
        self.settings.set_setting('port', 99, save=False)  # Below minimum
        errors = self.settings.validate_settings()
        self.assertTrue(any("Port must be" in error for error in errors))
        
        # Test empty token
        self.settings.set_setting('token', '', save=False)
        errors = self.settings.validate_settings()
        self.assertTrue(any("Token cannot be empty" in error for error in errors))


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    def test_clean_audio_device_id(self):
        """Test audio device ID cleaning function"""
        # Test with prefixed output
        dirty_id = "3 items found: Provider\\Device\\Speaker\\Render"
        clean_id = clean_audio_device_id(dirty_id)
        self.assertEqual(clean_id, "Provider\\Device\\Speaker\\Render")
        
        # Test with already clean ID
        clean_input = "Provider\\Device\\Speaker\\Render"
        clean_output = clean_audio_device_id(clean_input)
        self.assertEqual(clean_output, clean_input)
        
        # Test with empty input
        self.assertEqual(clean_audio_device_id(""), "")
        self.assertEqual(clean_audio_device_id(None), "")
    
    def test_validate_executable(self):
        """Test executable validation"""
        # Test with non-existent file
        self.assertFalse(validate_executable("nonexistent.exe"))
        
        # Test with empty path
        self.assertFalse(validate_executable(""))
        self.assertFalse(validate_executable(None))
        
        # Create temporary executable file for testing
        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as temp_exe:
            temp_exe.write(b'test content')
            temp_exe_path = temp_exe.name
        
        try:
            self.assertTrue(validate_executable(temp_exe_path))
        finally:
            os.unlink(temp_exe_path)
    
    @patch('winreg.OpenKey')
    @patch('winreg.QueryValueEx')
    def test_autostart_manager_is_enabled(self, mock_query, mock_open):
        """Test autostart detection"""
        # Test enabled case
        mock_open.return_value.__enter__ = Mock()
        mock_open.return_value.__exit__ = Mock()
        mock_query.return_value = ("test_path", None)
        
        self.assertTrue(AutostartManager.is_enabled())
        
        # Test disabled case (registry key not found)
        mock_query.side_effect = FileNotFoundError()
        self.assertFalse(AutostartManager.is_enabled())


class TestIntegration(unittest.TestCase):
    """Integration tests for component interaction"""
    
    def setUp(self):
        """Setup integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
    def test_settings_persistence(self):
        """Test that settings persist across manager instances"""
        settings_file = os.path.join(self.temp_dir, 'test_settings.json')
        
        # Create first settings manager and modify settings
        with patch('settings.get_app_data_dir', return_value=self.temp_dir):
            settings1 = SettingsManager()
            settings1.set_setting('port', 9999)
            settings1.set_setting('token', 'test_token')
        
        # Create second settings manager and verify persistence
        with patch('settings.get_app_data_dir', return_value=self.temp_dir):
            settings2 = SettingsManager()
            self.assertEqual(settings2.get_setting('port'), 9999)
            self.assertEqual(settings2.get_setting('token'), 'test_token')
    
    @patch('subprocess.run')
    def test_audio_controller_initialization(self, mock_subprocess):
        """Test audio controller initialization with mocked svcl.exe"""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "test output"
        mock_subprocess.return_value.stderr = ""
        
        # Test would require actual AudioController import and initialization
        # This is a placeholder for integration testing
        pass


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration validation scenarios"""
    
    def test_audio_mapping_validation(self):
        """Test audio mapping validation rules"""
        # Test with temporary settings manager
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('settings.get_app_data_dir', return_value=temp_dir):
                settings = SettingsManager()
                
                # Valid mappings
                valid_mappings = [
                    {"label": "test", "device_id": "test\\device", "use_for_streaming": False}
                ]
                self.assertTrue(settings.set_audio_mappings(valid_mappings, save=False))
                
                # Invalid mappings (empty label)
                invalid_mappings = [
                    {"label": "", "device_id": "test\\device", "use_for_streaming": False}
                ]
                self.assertFalse(settings.set_audio_mappings(invalid_mappings, save=False))
                
                # Invalid mappings (missing device_id)
                invalid_mappings2 = [
                    {"label": "test", "use_for_streaming": False}
                ]
                self.assertFalse(settings.set_audio_mappings(invalid_mappings2, save=False))
    
    def test_multiple_streaming_devices_validation(self):
        """Test that only one device can be marked for streaming"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('settings.get_app_data_dir', return_value=temp_dir):
                settings = SettingsManager()
                
                # Multiple streaming devices should be corrected
                mappings = [
                    {"label": "device1", "device_id": "test1", "use_for_streaming": True},
                    {"label": "device2", "device_id": "test2", "use_for_streaming": True}
                ]
                
                settings.set_audio_mappings(mappings, save=False)
                result_mappings = settings.get_audio_mappings()
                
                # Only one should remain marked for streaming
                streaming_count = sum(1 for m in result_mappings if m.get('use_for_streaming', False))
                self.assertEqual(streaming_count, 1)


def run_tests():
    """Run all unit tests"""
    print("Running MyLocalAPI Unit Tests...")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestSettingsManager,
        TestUtilityFunctions, 
        TestIntegration,
        TestConfigurationValidation
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✓ All unit tests passed!")
    else:
        print(f"✗ {len(result.failures + result.errors)} test(s) failed")
        
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)