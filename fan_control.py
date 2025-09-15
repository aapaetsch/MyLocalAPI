#!/usr/bin/env python3
"""
Fan control integration using FanControl.exe
Manages fan profiles, configurations, and process lifecycle

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE (GNU GPL v3.0)
Disclaimer: Provided AS IS. See README.md 'AS IS Disclaimer' for details.
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
    
    def requires_admin(self) -> bool:
        """Check if fan control requires admin privileges"""
        return True  # FanControl.exe -e and -c commands require elevation
    
    def can_switch_configs(self) -> bool:
        """Check if config switching is available (requires admin privileges)"""
        return self.is_configured() and is_admin()
    
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
                return True
            
            for proc in processes:
                try:
                    if not force:
                        proc.terminate()
                        proc.wait(timeout=3)
                    else:
                        proc.kill()
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    continue
           
            time.sleep(0.5)
            remaining = self.get_fancontrol_processes()
            
            if remaining and not force:
                for proc in remaining:
                    try:
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                time.sleep(0.2)
            
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
            args = [self.fan_exe_path]
            if minimized:
                args.append('-m')
            if config_path:
                args.extend(['-c', config_path])
            
            if is_admin():
                logger.info("Starting FanControl unelevated from admin context")
                self._start_unelevated(args)
            else:
                subprocess.Popen(args, 
                               creationflags=subprocess.CREATE_NO_WINDOW if not minimized else 0)
            
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
        
        self.stop_fancontrol()
        return self.start_fancontrol(minimized=True, config_path=config_path)
    
    def switch_config(self, config_path: str) -> bool:
        """Switch to a different config (uses config file replacement strategy)"""
        if not os.path.exists(config_path):
            raise RuntimeError(f"Config file not found: {config_path}")
        
        try:
            if self.is_running():
                return self._switch_config_by_replacement(config_path)
            else:
                return self.start_fancontrol(minimized=True, config_path=config_path)
                
        except Exception as e:
            logger.error(f"Error switching config: {e}")
            return False
    
    def _switch_config_by_replacement(self, config_path: str) -> bool:
        """Switch config by properly killing FanControl and restarting with new config"""
        try:
            if not is_admin():
                logger.error("Fan control switching requires administrator privileges to use FanControl.exe -e and -c commands")
                logger.error("Please run MyLocalAPI as administrator to enable fan configuration switching")
                return False
            
            exe_path = self.get_running_exe_path()
            if not exe_path:
                exe_path = self.fan_exe_path
            
            if not exe_path or not os.path.exists(exe_path):
                logger.error(f"FanControl.exe not found: {exe_path}")
                return False
            
            logger.info("Stopping FanControl using -e command")
            try:
                result = subprocess.run([exe_path, '-e'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=10,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode != 0:
                    logger.warning(f"FanControl -e returned code {result.returncode}: {result.stderr}")
                else:
                    logger.info("FanControl stopped successfully with -e")
                    
            except subprocess.TimeoutExpired:
                logger.warning("FanControl -e command timed out")
            except Exception as e:
                logger.warning(f"Failed to stop FanControl with -e: {e}")
            
            time.sleep(1.0)
            
            max_wait = 5
            wait_count = 0
            while self.is_running() and wait_count < max_wait:
                time.sleep(0.5)
                wait_count += 1
            
            if self.is_running():
                logger.warning("FanControl still running after -e command, forcing termination")
                self.stop_fancontrol(force=True)
                time.sleep(0.5)
            
            logger.info(f"Starting FanControl with config: {config_path}")
            try:
                args = [exe_path, '-m', '-c', config_path]
                
                subprocess.Popen(args, creationflags=subprocess.CREATE_NO_WINDOW)
                logger.info(f"Launched FanControl with: {' '.join(args)}")
                
                time.sleep(1.5)
                
                if self.is_running():
                    logger.info(f"Successfully switched to config: {os.path.basename(config_path)}")
                    return True
                else:
                    logger.error("FanControl failed to start with new config")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to start FanControl with config: {e}")
                
                # Try to restart with previous method as fallback
                try:
                    logger.info("Attempting fallback restart")
                    self.start_fancontrol(minimized=True)
                except:
                    pass
                    
                return False
            
        except Exception as e:
            logger.error(f"Config switch failed: {e}")
            return False
    
    def refresh_sensors(self) -> bool:
        """Refresh FanControl sensors using -r command"""
        try:
            if not self.ensure_running():
                return False
            
            exe_path = self.get_running_exe_path()
            if exe_path:
                try:
                    result = subprocess.run([exe_path, '-r'],
                                          capture_output=True,
                                          text=True,
                                          timeout=5,
                                          creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    if result.returncode == 0:
                        logger.info("Sent sensor refresh command to FanControl")
                        return True
                    else:
                        logger.warning(f"Sensor refresh returned code {result.returncode}: {result.stderr}")
                        return False
                        
                except subprocess.TimeoutExpired:
                    logger.warning("Sensor refresh command timed out")
                    return False
                except Exception as e:
                    logger.error(f"Error sending sensor refresh: {e}")
                    return False
            else:
                logger.error("Could not find running FanControl executable path")
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