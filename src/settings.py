#!/usr/bin/env python3
"""
Settings management for MyLocalAPI
Handles JSON persistence, validation, and default values

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE (GNU GPL v3.0)
Disclaimer: Provided AS IS. See README.md 'AS IS Disclaimer' for details.
"""

import json
import os
import logging
import copy
from typing import Any, Dict, List, Optional
from src.utils import get_app_data_dir

logger = logging.getLogger(__name__)

class SettingsManager:
    """Manages application settings with JSON persistence"""
    
    DEFAULT_SETTINGS = {
        "port": 1482,
        "token": "changeme",
        "audio": {
            "enabled": True,
            "svv_path": "",
            "mappings": [
                {
                    "label": "headphones",
                    "device_id": "HyperX Cloud II Wireless\\Device\\Speakers\\Render",
                    "use_for_streaming": True
                },
                {
                    "label": "speakers", 
                    "device_id": "Bose Revolve+ SoundLink\\Device\\Speakers\\Render",
                    "use_for_streaming": False
                },
                {
                    "label": "screen",
                    "device_id": "NVIDIA High Definition Audio\\Device\\M32UC\\Render", 
                    "use_for_streaming": False,
                    "is_game": False
                }
            ]
        },
        "fan": {
            "enabled": False,
            "fan_exe_path": "",
            "fan_config_path": "",
            "apply_on_stream_launch": False,
            "apply_on_game_launch": False,
            # Two separate selected config keys so stream and game can use different configs
            "selected_config_stream": "",
            "selected_config_game": "",
            # Keep legacy key for compatibility
            "selected_config": ""
        },
        "streaming": {
            "launch_streaming_by_endpoint": True,
            "appleTVMoniker": "AppleInc.AppleTVWin_nzyj5cx40ttqa"
        },
        "gaming": {
            "enabled": True,
            "games": [
                {
                    "label": "Example Game",
                    "steam_appid": "123456",
                    "exe_path": ""
                }
            ]
        },
        "autostart": False
    }
    
    def __init__(self):
        self.settings_file = os.path.join(get_app_data_dir(), 'settings.json')
        self.settings = self._load_settings()
        
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file or return defaults"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                settings = self._deep_merge(copy.deepcopy(self.DEFAULT_SETTINGS), loaded_settings)
                logger.info(f"Loaded settings from {self.settings_file}")
                return settings
            else:
                logger.info("Settings file not found, using defaults")
                return copy.deepcopy(self.DEFAULT_SETTINGS)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading settings: {e}, using defaults")
            return copy.deepcopy(self.DEFAULT_SETTINGS)
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def save_settings(self) -> bool:
        """Save current settings to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.info(f"Settings saved to {self.settings_file}")
            return True
        except IOError as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def get_setting(self, key_path: str, default: Any = None) -> Any:
        """Get a setting value using dot notation (e.g., 'audio.enabled')"""
        keys = key_path.split('.')
        value = self.settings
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_setting(self, key_path: str, value: Any, save: bool = True) -> bool:
        """Set a setting value using dot notation"""
        # Check if this is a port change for firewall rule management
        old_port = None
        if key_path == 'port':
            old_port = self.get_setting('port', 1482)
        
        keys = key_path.split('.')
        settings_ref = self.settings
        
        # Navigate to parent
        for key in keys[:-1]:
            if key not in settings_ref:
                settings_ref[key] = {}
            settings_ref = settings_ref[key]
        
        # Set final value
        settings_ref[keys[-1]] = value
        
        # Handle port change - update firewall rules
        if key_path == 'port' and old_port != value:
            self._update_firewall_rules(old_port, value)
        
        if save:
            return self.save_settings()
        return True
    
    def get_audio_mappings(self) -> List[Dict[str, Any]]:
        """Get audio device mappings"""
        return self.get_setting('audio.mappings', [])
    
    def set_audio_mappings(self, mappings: List[Dict[str, Any]], save: bool = True) -> bool:
        """Set audio device mappings"""
        # Validate mappings
        for mapping in mappings:
            if not isinstance(mapping, dict):
                return False
            if 'label' not in mapping or 'device_id' not in mapping:
                return False
            if not mapping.get('label', '').strip() or not mapping.get('device_id', '').strip():
                return False
        
        # Ensure only one mapping has use_for_streaming=True
        streaming_count = sum(1 for m in mappings if m.get('use_for_streaming', False))
        if streaming_count > 1:
            # Keep only the first True
            first_index = next(i for i, m in enumerate(mappings) if m.get('use_for_streaming', False))
            for i, mapping in enumerate(mappings):
                mapping['use_for_streaming'] = (i == first_index)

        # Ensure only one mapping has is_game=True
        game_count = sum(1 for m in mappings if m.get('is_game', False))
        if game_count > 1:
            first_game = next(i for i, m in enumerate(mappings) if m.get('is_game', False))
            for i, mapping in enumerate(mappings):
                mapping['is_game'] = (i == first_game)
        
        return self.set_setting('audio.mappings', mappings, save)
    
    def get_streaming_device_id(self) -> Optional[str]:
        """Get the device ID marked for streaming services"""
        mappings = self.get_audio_mappings()
        for mapping in mappings:
            if mapping.get('use_for_streaming', False):
                return mapping.get('device_id')
        return None
    
    def validate_settings(self) -> List[str]:
        """Validate current settings and return list of errors"""
        errors = []
        
        # Port validation
        port = self.get_setting('port')
        if not isinstance(port, int) or port < 1024 or port > 65535:
            errors.append("Port must be an integer between 1024 and 65535")
        
        # Token validation
        token = self.get_setting('token', '').strip()
        if not token:
            errors.append("Token cannot be empty")
        
        # Audio validation
        if self.get_setting('audio.enabled', False):
            mappings = self.get_audio_mappings()
            if not mappings:
                errors.append("Audio control is enabled but no device mappings are configured")
            else:
                # Check if at least one mapping is complete
                complete_mappings = [
                    m for m in mappings 
                    if m.get('label', '').strip() and m.get('device_id', '').strip()
                ]
                if not complete_mappings:
                    errors.append("Audio control is enabled but no complete device mappings found")
        
        # Fan validation
        if self.get_setting('fan.enabled', False):
            fan_exe = self.get_setting('fan.fan_exe_path', '').strip()
            fan_config = self.get_setting('fan.fan_config_path', '').strip()
            
            if not fan_exe:
                errors.append("Fan control is enabled but fan executable path is not set")
            elif not os.path.exists(fan_exe):
                errors.append(f"Fan executable not found: {fan_exe}")
                
            if not fan_config:
                errors.append("Fan control is enabled but fan config path is not set")
            elif not os.path.exists(fan_config):
                errors.append(f"Fan config directory not found: {fan_config}")
            
            # Check selected config if apply_on_stream_launch is enabled
            if self.get_setting('fan.apply_on_stream_launch', False) or self.get_setting('fan.apply_on_game_launch', False):
                selected = self.get_setting('fan.selected_config', '').strip()
                if not selected:
                    errors.append("Fan apply on stream launch is enabled but no config is selected")
        
        # Gaming validation
        if self.get_setting('gaming.enabled', True):
            mappings = self.get_gaming_mappings()
            if mappings:
                # Check if at least one mapping is complete
                complete_mappings = []
                for m in mappings:
                    label = m.get('label', '').strip()
                    steam_appid = m.get('steam_appid', '').strip()
                    exe_path = m.get('exe_path', '').strip()
                    
                    if label and (steam_appid or exe_path) and not (steam_appid and exe_path):
                        complete_mappings.append(m)
                
                if not complete_mappings:
                    errors.append("Gaming control is enabled but no complete game mappings found")
        
        return errors
    
    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults"""
        self.settings = copy.deepcopy(self.DEFAULT_SETTINGS)
        return self.save_settings()
    
    def export_settings(self, filepath: str) -> bool:
        """Export settings to a file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            logger.error(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, filepath: str) -> bool:
        """Import settings from a file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            # Merge with defaults and validate
            self.settings = self._deep_merge(copy.deepcopy(self.DEFAULT_SETTINGS), imported_settings)
            return self.save_settings()
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error importing settings: {e}")
            return False
    
    def get_device_mapping_by_label(self, label: str) -> Optional[Dict[str, Any]]:
        """Get device mapping by label"""
        mappings = self.get_audio_mappings()
        for mapping in mappings:
            if mapping.get('label', '').strip().lower() == label.strip().lower():
                return mapping
        return None
    
    def get_gaming_mappings(self) -> List[Dict[str, Any]]:
        """Get gaming mappings"""
        return self.get_setting('gaming.games', [])
    
    def set_gaming_mappings(self, mappings: List[Dict[str, Any]], save: bool = True) -> bool:
        """Set gaming mappings"""
        # Validate mappings
        for mapping in mappings:
            if not isinstance(mapping, dict):
                return False
            if 'label' not in mapping:
                return False
            if not mapping.get('label', '').strip():
                return False
            
            # Check that either steam_appid or exe_path is filled, but not both
            steam_appid = mapping.get('steam_appid', '').strip()
            exe_path = mapping.get('exe_path', '').strip()
            if steam_appid and exe_path:
                return False  # Both filled is invalid
            if not steam_appid and not exe_path:
                return False  # Neither filled is invalid
        
        return self.set_setting('gaming.games', mappings, save)
    
    def get_game_mapping_by_label(self, label: str) -> Optional[Dict[str, Any]]:
        """Get game mapping by label"""
        mappings = self.get_gaming_mappings()
        for mapping in mappings:
            if mapping.get('label', '').strip().lower() == label.strip().lower():
                return mapping
        return None
    
    def parse_fan_configs(self) -> List[str]:
        """Parse available fan configuration names from config directory"""
        config_path = self.get_setting('fan.fan_config_path', '').strip()
        if not config_path or not os.path.exists(config_path):
            return []
        
        try:
            config_files = []
            for filename in os.listdir(config_path):
                if filename.endswith('.json'):
                    config_name = os.path.splitext(filename)[0]
                    config_files.append(config_name)
            
            return sorted(config_files)
        except OSError as e:
            logger.error(f"Error reading fan config directory: {e}")
            return []
    
    def find_apple_tv_moniker(self) -> str:
        """Try to find Apple TV app package family name"""
        try:
            import subprocess
            # Try to find Apple TV app using PowerShell
            cmd = ['powershell', '-Command', 
                   'Get-AppxPackage | Where-Object {$_.Name -like "*AppleTV*" -or $_.Name -like "*Apple.TV*"} | Select-Object -ExpandProperty PackageFamilyName']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                moniker = result.stdout.strip().split('\n')[0].strip()
                if moniker:
                    return moniker
        except Exception as e:
            logger.debug(f"Could not auto-detect Apple TV moniker: {e}")
        
        # Return default if detection fails
        # return "AppleInc.AppleTVWin_nzyj5cx40ttqa"
        return ""
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        try:
            import ipaddress
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def is_network_accessible(self) -> bool:
        """Check if server is configured for network access"""
        host = self.get_setting('host', '127.0.0.1')
        return host in ['0.0.0.0'] or (host not in ['127.0.0.1', 'localhost'])
    
    def _update_firewall_rules(self, old_port: Optional[int], new_port: int) -> None:
        """Update Windows Firewall rules when port changes"""
        try:
            from utils import create_firewall_rule, remove_firewall_rule
            
            # Remove old firewall rule if it exists
            if old_port is not None and old_port != new_port:
                logger.info(f"Removing old firewall rule for port {old_port}")
                remove_firewall_rule("MyLocalAPI", old_port)
            
            # Create new firewall rule
            allow_network = self.is_network_accessible()
            logger.info(f"Creating firewall rule for port {new_port} (network access: {allow_network})")
            
            success = create_firewall_rule(new_port, "MyLocalAPI", allow_network)
            if success:
                logger.info(f"Successfully created firewall rule for port {new_port}")
            else:
                logger.warning(f"Failed to create firewall rule for port {new_port}")
                
        except Exception as e:
            logger.error(f"Error updating firewall rules: {e}")
    
    def ensure_firewall_rule(self) -> bool:
        """Ensure current port has proper firewall rule"""
        try:
            from utils import create_firewall_rule
            
            port = self.get_setting('port', 1482)
            allow_network = self.is_network_accessible()
            
            return create_firewall_rule(port, "MyLocalAPI", allow_network)
        except Exception as e:
            logger.error(f"Error ensuring firewall rule: {e}")
            return False