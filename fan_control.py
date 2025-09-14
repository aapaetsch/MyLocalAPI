#!/usr/bin/env python3
"""
Fan control integration using FanControl.exe
Manages fan profiles, configurations, and process lifecycle
"""

import os
import time
import logging
import subprocess
import psutil
from typing import Dict, List, Optional, Any
from utils import run_subprocess_safe, safe_kill_process_by_name, is_admin

logger = logging.getLogger(__name__)

class FanController:
    """Controls fan profiles via FanControl.exe"""
    
    def __init__(self, fan_exe_path: str, fan_config_path: str):
        """Initialize fan controller with paths"""
        self.fan_exe_path = fan_exe_path.strip() if fan_exe_path else ""
        self.fan_config_path = fan_config_path.strip() if fan_config_path else ""
        
        if self.fan_exe_path and not os.path.exists(self.fan_exe_path):
            logger.warning(f"FanControl.exe not found at: {self.fan_exe_path}")
        
        if self.fan_config_path and not os.path.exists(self.fan_config_path):
            logger.warning(f"Fan config directory not found at: {self.fan_config_path}")
    
    def is_configured(self) -> bool:
        """Check if fan control is properly configured"""
        return (bool(self.fan_exe_path and os.path.exists(self.fan_exe_path)) and
                bool(self.fan_config_path and os.path.exists(self.fan_config_path)))
    
    def get_fancontrol_processes(self) -> List[psutil.Process]:
        """Get all running FanControl processes"""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['name'] and 'fancontrol' in proc.info['name'].lower():
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.debug(f"Error enumerating processes: {e}")
        
        return processes
    
    def is_running(self) -> bool:
        """Check if FanControl is currently running"""
        return len(self.get_fancontrol_processes()) > 0
    
    def get_running_exe_path(self) -> Optional[str]:
        """Get the path of the running FanControl.exe"""
        processes = self.get_fancontrol_processes()
        if processes:
            try:
                return processes[0].exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return self.fan_exe_path if self.fan_exe_path else None
    
    def stop_fancontrol(self, force: bool = False) -> bool:
        """Stop all FanControl processes"""
        try:
            processes = self.get_fancontrol_processes()
            if not processes:
                return True  # Already stopped
            
            # Try graceful shutdown first
            for proc in processes:
                try:
                    if not force:
                        # Try to close main window first
                        proc.terminate()
                        proc.wait(timeout=3)
                    else:
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    continue
            
            # Wait a bit and check if any are still running
            time.sleep(0.5)
            remaining = self.get_fancontrol_processes()
            
            if remaining and not force:
                # Force kill remaining processes
                for proc in remaining:
                    try:
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                time.sleep(0.2)
            
            # Final check using taskkill as fallback
            if self.get_fancontrol_processes():
                safe_kill_process_by_name("FanControl.exe")
                time.sleep(0.2)
            
            success = len(self.get_fancontrol_processes()) == 0
            if success:
                logger.info("FanControl stopped successfully")
            return success
            
        except Exception as e:
            logger.error(f"Error stopping FanControl: {e}")
            return False
    
    def start_fancontrol(self, minimized: bool = True, config_path: Optional[str] = None) -> bool:
        """Start FanControl.exe"""
        if not self.fan_exe_path or not os.path.exists(self.fan_exe_path):
            raise RuntimeError(f"FanControl.exe not found: {self.fan_exe_path}")
        
        try:
            # Prepare arguments
            args = [self.fan_exe_path]
            if minimized:
                args.append('-m')
            if config_path:
                args.extend(['-c', config_path])
            
            # Determine how to start based on current process privileges
            if is_admin():
                # If we're admin, start unelevated for desktop interaction
                logger.info("Starting FanControl unelevated from admin context")
                self._start_unelevated(args)
            else:
                # Normal start
                subprocess.Popen(args, 
                               creationflags=subprocess.CREATE_NO_WINDOW if not minimized else 0)
            
            # Wait a moment for process to start
            time.sleep(0.5)
            
            success = self.is_running()
            if success:
                logger.info(f"FanControl started successfully (minimized: {minimized})")
            return success
            
        except Exception as e:
            logger.error(f"Error starting FanControl: {e}")
            return False
    
    def _start_unelevated(self, args: List[str]) -> None:
        """Start process unelevated (for admin contexts)"""
        try:
            import win32com.shell.shell as shell
            
            exe_path = args[0]
            exe_args = ' '.join(args[1:]) if len(args) > 1 else ""
            working_dir = os.path.dirname(exe_path)
            
            shell.ShellExecute(exe_path, exe_args, working_dir, 'open', 0)
            
        except ImportError:
            # Fallback without pywin32
            subprocess.Popen(args)
        except Exception as e:
            logger.warning(f"Unelevated start failed, using normal start: {e}")
            subprocess.Popen(args)
    
    def ensure_running(self) -> bool:
        """Ensure FanControl is running, start if needed"""
        if self.is_running():
            return True
        
        return self.start_fancontrol(minimized=True)
    
    def restart_with_config(self, config_path: str) -> bool:
        """Stop FanControl and restart with specific config"""
        if not os.path.exists(config_path):
            raise RuntimeError(f"Config file not found: {config_path}")
        
        # Stop current instance
        self.stop_fancontrol()
        
        # Start with new config
        return self.start_fancontrol(minimized=True, config_path=config_path)
    
    def switch_config(self, config_path: str) -> bool:
        """Switch to a different config (uses running instance if available)"""
        if not os.path.exists(config_path):
            raise RuntimeError(f"Config file not found: {config_path}")
        
        try:
            # If not running, start with config
            if not self.is_running():
                return self.start_fancontrol(minimized=True, config_path=config_path)
            
            # If running, send config change command to existing instance
            exe_path = self.get_running_exe_path()
            if exe_path:
                # FanControl supports single-instance, so starting with -c should switch config
                subprocess.Popen([exe_path, '-c', config_path],
                               creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(0.2)
                return True
            else:
                # Fallback to restart
                return self.restart_with_config(config_path)
                
        except Exception as e:
            logger.error(f"Error switching config: {e}")
            return False
    
    def refresh_sensors(self) -> bool:
        """Refresh FanControl sensors"""
        try:
            if not self.ensure_running():
                return False
            
            exe_path = self.get_running_exe_path()
            if exe_path:
                # Send refresh command to running instance
                subprocess.Popen([exe_path, '-r'],
                               creationflags=subprocess.CREATE_NO_WINDOW)
                logger.info("Sent refresh command to FanControl")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing sensors: {e}")
            return False
    
    def get_config_files(self) -> List[Dict[str, Any]]:
        """Get list of available config files"""
        if not self.fan_config_path or not os.path.exists(self.fan_config_path):
            return []
        
        try:
            configs = []
            for filename in os.listdir(self.fan_config_path):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.fan_config_path, filename)
                    if os.path.isfile(filepath):
                        config_name = os.path.splitext(filename)[0]
                        
                        # Try to extract percentage from filename
                        percentage = None
                        import re
                        match = re.search(r'(\d{1,3})', config_name)
                        if match:
                            pct = int(match.group(1))
                            if 0 <= pct <= 100:
                                percentage = pct
                        
                        configs.append({
                            "name": config_name,
                            "filename": filename,
                            "filepath": filepath,
                            "percentage": percentage,
                            "size": os.path.getsize(filepath),
                            "modified": os.path.getmtime(filepath)
                        })
            
            # Sort by percentage if available, then by name
            configs.sort(key=lambda x: (x["percentage"] is None, x["percentage"], x["name"]))
            return configs
            
        except Exception as e:
            logger.error(f"Error reading config files: {e}")
            return []
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of available configs"""
        configs = self.get_config_files()
        
        with_percentage = [c for c in configs if c["percentage"] is not None]
        
        return {
            "total": len(configs),
            "with_percentage": len(with_percentage),
            "configs": configs,
            "percentage_configs": with_percentage
        }
    
    def set_fan_percentage(self, percentage: int) -> Dict[str, Any]:
        """Set fan speed by finding closest percentage-based config"""
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100")
        
        configs = self.get_config_files()
        percentage_configs = [c for c in configs if c["percentage"] is not None]
        
        if not percentage_configs:
            raise RuntimeError("No percentage-based configs found")
        
        # Find exact match first
        exact_match = next((c for c in percentage_configs if c["percentage"] == percentage), None)
        if exact_match:
            success = self.switch_config(exact_match["filepath"])
            return {
                "ok": success,
                "requested": percentage,
                "applied": percentage,
                "config": exact_match["filepath"],
                "config_name": exact_match["name"],
                "exact_match": True
            }
        
        # Find closest match
        closest = min(percentage_configs, key=lambda x: abs(x["percentage"] - percentage))
        success = self.switch_config(closest["filepath"])
        
        return {
            "ok": success,
            "requested": percentage,
            "applied": closest["percentage"],
            "config": closest["filepath"],
            "config_name": closest["name"],
            "exact_match": False
        }
    
    def set_fan_profile(self, profile_name: str) -> Dict[str, Any]:
        """Set fan profile by name"""
        configs = self.get_config_files()
        
        # Find config by name (case insensitive)
        matching_config = None
        for config in configs:
            if config["name"].lower() == profile_name.lower():
                matching_config = config
                break
        
        if not matching_config:
            available_names = [c["name"] for c in configs]
            raise RuntimeError(f"Profile '{profile_name}' not found. Available: {available_names}")
        
        success = self.switch_config(matching_config["filepath"])
        
        return {
            "ok": success,
            "profile": profile_name,
            "config": matching_config["filepath"],
            "config_name": matching_config["name"]
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get fan control status"""
        try:
            processes = self.get_fancontrol_processes()
            running = len(processes) > 0
            
            status = {
                "configured": self.is_configured(),
                "running": running,
                "exe_path": self.fan_exe_path,
                "config_path": self.fan_config_path,
                "processes": []
            }
            
            for proc in processes:
                try:
                    status["processes"].append({
                        "pid": proc.pid,
                        "exe": proc.exe(),
                        "started": proc.create_time()
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if self.fan_config_path and os.path.exists(self.fan_config_path):
                config_summary = self.get_config_summary()
                status["configs"] = config_summary
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting fan status: {e}")
            return {
                "configured": False,
                "running": False,
                "error": str(e)
            }
    
    def test_fan_system(self) -> Dict[str, Any]:
        """Test fan control system"""
        try:
            test_results = {
                "exe_exists": os.path.exists(self.fan_exe_path) if self.fan_exe_path else False,
                "config_dir_exists": os.path.exists(self.fan_config_path) if self.fan_config_path else False,
                "running": self.is_running(),
                "config_count": 0,
                "percentage_config_count": 0
            }
            
            if test_results["config_dir_exists"]:
                configs = self.get_config_files()
                test_results["config_count"] = len(configs)
                test_results["percentage_config_count"] = len([c for c in configs if c["percentage"] is not None])
            
            test_results["system_ready"] = (
                test_results["exe_exists"] and 
                test_results["config_dir_exists"] and 
                test_results["config_count"] > 0
            )
            
            return test_results
            
        except Exception as e:
            return {
                "system_ready": False,
                "error": str(e)
            }