#!/usr/bin/env python3
"""
Audio device control using NirSoft SoundVolumeCommandLine (svcl.exe)
Provides device switching, volume control, and device enumeration

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE (GNU GPL v3.0)
Disclaimer: Provided AS IS. See README.md 'AS IS Disclaimer' for details.
"""

import os
import logging
import json
import csv
import io
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from utils import find_bundled_executable, run_subprocess_safe, clean_audio_device_id

logger = logging.getLogger(__name__)

class AudioController:
    """Controls Windows audio devices via svcl.exe"""
    
    def __init__(self, svv_path: Optional[str] = None):
        """Initialize with optional custom svcl.exe path"""
        self.svv_path = self._find_svcl_executable(svv_path)
        if not self.svv_path:
            raise RuntimeError("svcl.exe not found. Please ensure it's bundled with the application.")
        
        logger.info(f"Using audio tool: {self.svv_path}")
    
    def _find_svcl_executable(self, custom_path: Optional[str] = None) -> Optional[str]:
        """Find svcl.exe executable"""
        if custom_path and os.path.exists(custom_path):
            return custom_path
        
        # Try bundled executable first
        bundled = find_bundled_executable('svcl.exe')
        if bundled:
            return bundled
        
        # Try alternative names
        for exe_name in ['svcl.exe', 'SoundVolumeView64.exe', 'SoundVolumeView.exe']:
            path = find_bundled_executable(exe_name)
            if path:
                return path
        
        return None
    
    def _run_svcl(self, args: List[str], timeout: int = 10) -> subprocess.CompletedProcess:
        """Run svcl.exe with given arguments"""
        cmd = [self.svv_path] + args
        return run_subprocess_safe(cmd, timeout=timeout, capture_output=True)
    
    def get_devices_raw(self) -> Dict[str, Any]:
        """Get raw device information from svcl.exe"""
        try:
            # Use /Stdout with /scomma to get all CSV data to stdout
            result = self._run_svcl(['/Stdout', '/scomma'])
            
            if result.returncode != 0:
                logger.error(f"svcl.exe returned error code {result.returncode}: {result.stderr}")
                return {"ok": False, "rows": [], "error": result.stderr}
            
            # Parse CSV output from stdout
            if not result.stdout.strip():
                return {"ok": False, "rows": [], "error": "No output from svcl.exe"}
            
            # Remove BOM if present and parse CSV
            csv_content = result.stdout
            if csv_content.startswith('\ufeff'):
                csv_content = csv_content[1:]  # Remove BOM
            
            # Also handle the visible BOM characters that might appear
            csv_content = csv_content.replace('ï»¿', '')
            
            csv_lines = csv_content.strip().split('\n')
            if len(csv_lines) < 2:
                return {"ok": False, "rows": [], "error": "Insufficient CSV data"}
            
            # Parse header to get column indices
            header_line = csv_lines[0]
            data_lines = csv_lines[1:]
            
            csv_reader = csv.reader([header_line])
            all_headers = next(csv_reader)
            
            # Clean up header names (remove any remaining BOM characters)
            all_headers = [h.replace('\ufeff', '').replace('ï»¿', '') for h in all_headers]
            
            # Find the columns we need
            required_columns = ['Name', 'Device Name', 'Direction', 'Default', 
                               'Default Multimedia', 'Default Communications', 
                               'Volume Percent', 'Command-Line Friendly ID']
            
            column_indices = {}
            for col in required_columns:
                try:
                    column_indices[col] = all_headers.index(col)
                except ValueError:
                    logger.warning(f"Column '{col}' not found in svcl.exe output")
            
            # Parse data rows
            rows = []
            csv_reader = csv.reader(data_lines)
            
            for row_data in csv_reader:
                if len(row_data) > max(column_indices.values(), default=-1):
                    row = {}
                    for col_name, col_index in column_indices.items():
                        row[col_name] = row_data[col_index] if col_index < len(row_data) else ""
                    rows.append(row)
            
            logger.debug(f"Parsed {len(rows)} audio devices")
            return {"ok": True, "rows": rows, "headers": list(required_columns)}
            
        except Exception as e:
            logger.error(f"Error getting device information: {e}")
            return {"ok": False, "rows": [], "error": str(e)}
    
    def get_playback_devices(self) -> Dict[str, Any]:
        """Get list of playback (render) devices"""
        raw_data = self.get_devices_raw()
        if not raw_data["ok"]:
            return raw_data
        
        playback_devices = []
        for device in raw_data["rows"]:
            direction = device.get("Direction", "").lower()
            if direction == "render":
                # Clean up the device data
                clean_device = {
                    "name": device.get("Name", ""),
                    "device_name": device.get("Device Name", ""),
                    "direction": "Render",
                    "default": device.get("Default", ""),
                    "default_multimedia": device.get("Default Multimedia", ""),
                    "default_communications": device.get("Default Communications", ""),
                    "volume_percent": self._parse_volume(device.get("Volume Percent", "")),
                    "device_id": clean_audio_device_id(device.get("Command-Line Friendly ID", ""))
                }
                playback_devices.append(clean_device)
        
        return {
            "ok": True,
            "devices": playback_devices,
            "total": len(playback_devices)
        }
    
    def _parse_volume(self, volume_str: str) -> Optional[int]:
        """Parse volume string to integer percentage"""
        if not volume_str:
            return None
        
        try:
            # Remove non-numeric characters except decimal point
            import re
            volume_clean = re.sub(r'[^\d\.]', '', str(volume_str))
            if volume_clean:
                volume_float = float(volume_clean)
                return max(0, min(100, int(round(volume_float))))
        except (ValueError, TypeError):
            pass
        
        return None
    
    def get_current_default_device(self) -> Dict[str, Any]:
        """Get current default render device information"""
        try:
            # Use GetColumnValue to get default device ID
            result = self._run_svcl(['/Stdout', '/GetColumnValue', 'DefaultRenderDevice', 'Command-Line Friendly ID'])
            
            if result.returncode != 0:
                return {"ok": False, "error": f"Failed to get default device: {result.stderr}"}
            
            device_id = clean_audio_device_id(result.stdout.strip())
            if not device_id:
                return {"ok": False, "error": "No default render device found"}
            
            # Get volume for default device
            volume_result = self._run_svcl(['/Stdout', '/GetPercent', 'DefaultRenderDevice'])
            volume = None
            if volume_result.returncode == 0:
                volume = self._parse_volume(volume_result.stdout.strip())
            
            # Try to get device details from device list
            devices_info = self.get_playback_devices()
            device_name = None
            name = None
            
            if devices_info["ok"]:
                for device in devices_info["devices"]:
                    if device["device_id"].lower() == device_id.lower():
                        device_name = device["device_name"]
                        name = device["name"]
                        if volume is None:
                            volume = device["volume_percent"]
                        break
            
            # If no device name found, try to extract from device ID
            if not device_name and device_id:
                parts = device_id.split('\\')
                if len(parts) >= 3:
                    device_name = parts[0]
                    name = parts[2] if len(parts) > 2 else parts[1]
            
            return {
                "ok": True,
                "device_id": device_id,
                "device_name": device_name,
                "name": name,
                "volume": volume
            }
            
        except Exception as e:
            logger.error(f"Error getting current default device: {e}")
            return {"ok": False, "error": str(e)}
    
    def set_default_device(self, device_id: str, role: str = "Console") -> bool:
        """Set default audio device by ID"""
        if not device_id.strip():
            raise ValueError("Device ID cannot be empty")
        
        try:
            # Map role to numeric value (from PowerShell script)
            role_map = {"Console": "0", "Multimedia": "1", "Communications": "2"}
            role_num = role_map.get(role, "0")
            
            result = self._run_svcl(['/SetDefault', device_id, role_num])
            
            if result.returncode != 0:
                logger.error(f"Failed to set default device: {result.stderr}")
                return False
            
            logger.info(f"Set default device to: {device_id} (role: {role})")
            return True
            
        except Exception as e:
            logger.error(f"Error setting default device: {e}")
            return False
    
    def set_volume(self, percent: int, device_id: Optional[str] = None) -> bool:
        """Set volume for device (default device if not specified)"""
        if percent < 0 or percent > 100:
            raise ValueError("Volume percent must be between 0 and 100")
        
        try:
            target = device_id if device_id else "DefaultRenderDevice"
            result = self._run_svcl(['/SetVolume', target, str(percent)])
            
            if result.returncode != 0:
                logger.error(f"Failed to set volume: {result.stderr}")
                return False
            
            logger.info(f"Set volume to {percent}% for device: {target}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False
    
    def get_current_volume(self, device_id: Optional[str] = None) -> Optional[int]:
        """Get current volume for device"""
        try:
            target = device_id if device_id else "DefaultRenderDevice"
            result = self._run_svcl(['/Stdout', '/GetPercent', target])
            
            if result.returncode != 0:
                logger.error(f"Failed to get volume: {result.stderr}")
                return None
            
            return self._parse_volume(result.stdout.strip())
            
        except Exception as e:
            logger.error(f"Error getting volume: {e}")
            return None
    
    def get_audio_snapshot(self, device_mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get comprehensive audio status snapshot"""
        try:
            # Get current default device
            current_device = self.get_current_default_device()
            if not current_device["ok"]:
                return {
                    "ok": False,
                    "reason": "no_default_device",
                    "error": current_device.get("error", "Unknown error")
                }
            
            device_id = current_device["device_id"]
            volume = current_device["volume"]
            
            # Map device ID to label from mappings
            active_key = "unknown"
            matched = False
            
            if device_mappings:
                for mapping in device_mappings:
                    mapping_id = mapping.get("device_id", "").strip()
                    if mapping_id and mapping_id.lower() == device_id.lower():
                        active_key = mapping.get("label", "unknown")
                        matched = True
                        break
            
            return {
                "ok": True,
                "device_id": device_id,
                "device_name": current_device["device_name"],
                "name": current_device["name"],
                "volume": volume,
                "active_key": active_key,
                "matched": matched
            }
            
        except Exception as e:
            logger.error(f"Error getting audio snapshot: {e}")
            return {
                "ok": False,
                "reason": "exception",
                "error": str(e)
            }
    
    def switch_to_device_by_key(self, key: str, device_mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Switch to audio device by mapping key"""
        # Find device ID by key
        device_id = None
        for mapping in device_mappings:
            if mapping.get("label", "").strip().lower() == key.strip().lower():
                device_id = mapping.get("device_id", "").strip()
                break
        
        if not device_id:
            return {
                "ok": False,
                "error": f"Device key '{key}' not found in mappings"
            }
        
        # Set as default device
        success = self.set_default_device(device_id)
        if success:
            return {
                "ok": True,
                "device_id": device_id,
                "key": key
            }
        else:
            return {
                "ok": False,
                "error": f"Failed to set device '{device_id}' as default"
            }
    
    def get_streaming_device_id(self, device_mappings: List[Dict[str, Any]]) -> Optional[str]:
        """Get device ID marked for streaming services"""
        for mapping in device_mappings:
            if mapping.get("use_for_streaming", False):
                return mapping.get("device_id", "").strip()
        return None
    
    def switch_to_streaming_device(self, device_mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Switch to the device configured for streaming services"""
        streaming_device_id = self.get_streaming_device_id(device_mappings)
        
        if not streaming_device_id:
            return {
                "ok": False,
                "error": "No device configured for streaming services"
            }
        
        success = self.set_default_device(streaming_device_id)
        if success:
            return {
                "ok": True,
                "device_id": streaming_device_id,
                "reason": "switched_for_streaming"
            }
        else:
            return {
                "ok": False,
                "error": f"Failed to switch to streaming device '{streaming_device_id}'"
            }
    
    def test_audio_system(self) -> Dict[str, Any]:
        """Test audio system and return diagnostic information"""
        try:
            # Test basic device enumeration
            devices = self.get_playback_devices()
            
            # Test current device detection
            current = self.get_current_default_device()
            
            # Test volume reading
            volume = self.get_current_volume()
            
            return {
                "ok": True,
                "svcl_path": self.svv_path,
                "devices_found": devices["total"] if devices["ok"] else 0,
                "current_device_ok": current["ok"],
                "volume_readable": volume is not None,
                "system_ready": devices["ok"] and current["ok"]
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "svcl_path": self.svv_path
            }