#!/usr/bin/env python3
"""
Gaming control for MyLocalAPI
Handles game launching via Steam or direct executable paths

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE (GNU GPL v3.0)
Disclaimer: Provided AS IS. See README.md 'AS IS Disclaimer' for details.
"""

import os
import subprocess
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class GamingController:
    """Controller for game launching functionality"""
    
    def __init__(self):
        """Initialize gaming controller"""
        pass
    
    def launch_game_by_steam_id(self, steam_appid: str) -> Dict[str, Any]:
        """Launch a game by Steam App ID"""
        try:
            if not steam_appid:
                return {"ok": False, "error": "Steam App ID is required"}
            
            # Steam URL protocol for launching games
            steam_url = f"steam://run/{steam_appid}"
            
            # Use os.startfile on Windows or subprocess on other platforms
            if os.name == 'nt':
                os.startfile(steam_url)
            else:
                subprocess.run(['xdg-open', steam_url], check=False)
            
            logger.info(f"Launched game via Steam App ID: {steam_appid}")
            return {
                "ok": True,
                "method": "steam",
                "steam_appid": steam_appid,
                "message": f"Launched game with Steam App ID: {steam_appid}"
            }
            
        except Exception as e:
            logger.error(f"Failed to launch game via Steam ID {steam_appid}: {e}")
            return {
                "ok": False,
                "error": f"Failed to launch game via Steam: {str(e)}"
            }
    
    def launch_game_by_executable(self, exe_path: str) -> Dict[str, Any]:
        """Launch a game by executable path"""
        try:
            if not exe_path:
                return {"ok": False, "error": "Executable path is required"}
            
            if not os.path.exists(exe_path):
                return {"ok": False, "error": f"Executable not found: {exe_path}"}
            
            if not os.path.isfile(exe_path):
                return {"ok": False, "error": f"Path is not a file: {exe_path}"}
            
            # Launch the executable
            if os.name == 'nt':
                # On Windows, use CREATE_NEW_PROCESS_GROUP to launch independently
                subprocess.Popen([exe_path], 
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            else:
                # On other platforms, use standard Popen
                subprocess.Popen([exe_path])
            
            logger.info(f"Launched game executable: {exe_path}")
            return {
                "ok": True,
                "method": "executable",
                "exe_path": exe_path,
                "message": f"Launched executable: {os.path.basename(exe_path)}"
            }
            
        except Exception as e:
            logger.error(f"Failed to launch game executable {exe_path}: {e}")
            return {
                "ok": False,
                "error": f"Failed to launch executable: {str(e)}"
            }
    
    def launch_game_by_label(self, label: str, mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Launch a game by label using mappings"""
        try:
            # Find matching mapping
            mapping = None
            for m in mappings:
                if m.get('label', '').strip().lower() == label.strip().lower():
                    mapping = m
                    break
            
            if not mapping:
                return {
                    "ok": False,
                    "error": f"No game mapping found for label: {label}"
                }
            
            # Check what launch method to use
            steam_appid = mapping.get('steam_appid', '').strip()
            exe_path = mapping.get('exe_path', '').strip()
            
            if steam_appid:
                # Launch via Steam
                result = self.launch_game_by_steam_id(steam_appid)
                if result["ok"]:
                    result["label"] = label
                    result["mapping"] = mapping
                return result
            
            elif exe_path:
                # Launch via executable
                result = self.launch_game_by_executable(exe_path)
                if result["ok"]:
                    result["label"] = label
                    result["mapping"] = mapping
                return result
            
            else:
                return {
                    "ok": False,
                    "error": f"Game mapping for '{label}' has no Steam App ID or executable path configured"
                }
                
        except Exception as e:
            logger.error(f"Failed to launch game by label {label}: {e}")
            return {
                "ok": False,
                "error": f"Failed to launch game: {str(e)}"
            }
    
    def get_audio_device_for_game(self, label: str, mappings: List[Dict[str, Any]]) -> Optional[str]:
        """Get the audio device that should be used for a specific game"""
        try:
            # Find the game mapping
            for mapping in mappings:
                if mapping.get('label', '').strip().lower() == label.strip().lower():
                    if mapping.get('use_for_audio', False):
                        return mapping.get('label')  # Return the game label
            return None
        except Exception as e:
            logger.error(f"Failed to get audio device for game {label}: {e}")
            return None
    
    def test_gaming_system(self) -> Dict[str, Any]:
        """Test gaming system functionality"""
        try:
            result = {
                "ok": True,
                "steam_available": False,
                "executable_launch": True,  # Always available
                "issues": []
            }
            
            # Test Steam availability (check if Steam is installed)
            steam_paths = [
                os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Steam\\Steam.lnk"),
                "C:\\Program Files (x86)\\Steam\\steam.exe",
                "C:\\Program Files\\Steam\\steam.exe"
            ]
            
            for steam_path in steam_paths:
                if os.path.exists(steam_path):
                    result["steam_available"] = True
                    break
            
            if not result["steam_available"]:
                result["issues"].append("Steam installation not detected - Steam App ID launches may not work")
            
            return result
            
        except Exception as e:
            logger.error(f"Gaming system test failed: {e}")
            return {
                "ok": False,
                "error": f"Gaming system test failed: {str(e)}"
            }