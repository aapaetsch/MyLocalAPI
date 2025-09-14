#!/usr/bin/env python3
"""
Streaming services integration
Handles launching streaming services and managing browser/app focus
"""

import os
import sys
import time
import logging
import subprocess
import webbrowser
from typing import Dict, Optional, List
from utils import run_subprocess_safe

logger = logging.getLogger(__name__)

class StreamingController:
    """Controls streaming service launching and window management"""
    
    # Service to URL/app mapping
    SERVICES = {
        "youtube": {
            "url": "https://www.youtube.com",
            "browser": "chrome"
        },
        "crunchyroll": {
            "url": "https://www.crunchyroll.com", 
            "browser": "chrome"
        },
        "netflix": {
            "url": "https://www.netflix.com",
            "browser": "edge"
        },
        "disney": {
            "url": "https://www.disneyplus.com",
            "browser": "edge"
        },
        "prime": {
            "url": "https://www.primevideo.com",
            "browser": "edge"
        },
        "appletv": {
            "app": True,
            "fallback_url": "https://tv.apple.com/"
        }
    }
    
    def __init__(self, apple_tv_moniker: str = "AppleInc.AppleTVWin_nzyj5cx40ttqa"):
        """Initialize streaming controller"""
        self.apple_tv_moniker = apple_tv_moniker
        self.chrome_paths = self._find_chrome_paths()
        self.edge_paths = self._find_edge_paths()
        
    def _find_chrome_paths(self) -> List[str]:
        """Find Google Chrome installation paths"""
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe")
        ]
        return [path for path in paths if os.path.exists(path)]
    
    def _find_edge_paths(self) -> List[str]:
        """Find Microsoft Edge installation paths"""
        paths = [
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe")
        ]
        return [path for path in paths if os.path.exists(path)]
    
    def _focus_window_by_process(self, process: subprocess.Popen, timeout: int = 5) -> bool:
        """Try to focus window by process handle"""
        try:
            import win32gui
            import win32con
            import win32process
            import psutil
            
            # Get process ID
            if hasattr(process, 'pid'):
                pid = process.pid
            else:
                return False
            
            # Wait for window to appear
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Find windows belonging to this process
                    def enum_windows_callback(hwnd, results):
                        _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if window_pid == pid and win32gui.IsWindowVisible(hwnd):
                            results.append(hwnd)
                        return True
                    
                    windows = []
                    win32gui.EnumWindows(enum_windows_callback, windows)
                    
                    if windows:
                        hwnd = windows[0]  # Use first window
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        win32gui.SetForegroundWindow(hwnd)
                        return True
                        
                except Exception as e:
                    logger.debug(f"Window focus attempt failed: {e}")
                
                time.sleep(0.1)
            
            return False
            
        except ImportError:
            logger.debug("win32gui not available, skipping window focus")
            return False
        except Exception as e:
            logger.debug(f"Window focus failed: {e}")
            return False
    
    def _focus_window_by_title(self, title_pattern: str, timeout: int = 5) -> bool:
        """Try to focus window by title pattern"""
        try:
            import win32gui
            import win32con
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                def enum_windows_callback(hwnd, results):
                    if win32gui.IsWindowVisible(hwnd):
                        window_title = win32gui.GetWindowText(hwnd).lower()
                        if title_pattern.lower() in window_title:
                            results.append(hwnd)
                    return True
                
                windows = []
                win32gui.EnumWindows(enum_windows_callback, windows)
                
                if windows:
                    hwnd = windows[0]
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    return True
                
                time.sleep(0.2)
            
            return False
            
        except ImportError:
            return False
        except Exception as e:
            logger.debug(f"Window focus by title failed: {e}")
            return False
    
    def launch_in_chrome(self, url: str) -> Dict[str, any]:
        """Launch URL in Google Chrome"""
        if not self.chrome_paths:
            return {
                "ok": False,
                "error": "Google Chrome not found"
            }
        
        try:
            chrome_path = self.chrome_paths[0]
            process = subprocess.Popen([chrome_path, url])
            
            # Try to focus the window
            focused = self._focus_window_by_process(process, timeout=3)
            if not focused:
                focused = self._focus_window_by_title("chrome", timeout=2)
            
            return {
                "ok": True,
                "browser": "chrome",
                "url": url,
                "focused": focused
            }
            
        except Exception as e:
            logger.error(f"Failed to launch Chrome: {e}")
            return {
                "ok": False,
                "error": f"Failed to launch Chrome: {str(e)}"
            }
    
    def launch_in_edge(self, url: str) -> Dict[str, any]:
        """Launch URL in Microsoft Edge"""
        if not self.edge_paths:
            return {
                "ok": False,
                "error": "Microsoft Edge not found"
            }
        
        try:
            edge_path = self.edge_paths[0]
            process = subprocess.Popen([edge_path, url])
            
            # Try to focus the window
            focused = self._focus_window_by_process(process, timeout=3)
            if not focused:
                focused = self._focus_window_by_title("edge", timeout=2)
            
            return {
                "ok": True,
                "browser": "edge", 
                "url": url,
                "focused": focused
            }
            
        except Exception as e:
            logger.error(f"Failed to launch Edge: {e}")
            return {
                "ok": False,
                "error": f"Failed to launch Edge: {str(e)}"
            }
    
    def launch_apple_tv_app(self, timeout: int = 10) -> Dict[str, any]:
        """Launch Apple TV app using Windows app moniker"""
        if not self.apple_tv_moniker:
            return self._fallback_apple_tv()
        
        try:
            # Launch via explorer using the app moniker
            app_path = f"shell:AppsFolder\\{self.apple_tv_moniker}!App"
            process = subprocess.Popen(['explorer.exe', app_path])
            
            # Wait for Apple TV process/window to appear
            start_time = time.time()
            apple_tv_found = False
            
            while time.time() - start_time < timeout:
                try:
                    import psutil
                    
                    # Look for processes that might be Apple TV
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            proc_name = proc.info['name'].lower()
                            if 'appletv' in proc_name or 'apple' in proc_name:
                                # Try to focus this process
                                focused = self._focus_window_by_title("apple", timeout=1)
                                if focused:
                                    apple_tv_found = True
                                    break
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    if apple_tv_found:
                        break
                        
                except ImportError:
                    # Without psutil, just try title-based focus
                    if self._focus_window_by_title("apple", timeout=1):
                        apple_tv_found = True
                        break
                
                time.sleep(0.4)
            
            if apple_tv_found:
                return {
                    "ok": True,
                    "service": "appletv",
                    "method": "app",
                    "focused": True
                }
            else:
                logger.warning("Apple TV app launched but window not found, falling back to browser")
                return self._fallback_apple_tv()
                
        except Exception as e:
            logger.error(f"Failed to launch Apple TV app: {e}")
            return self._fallback_apple_tv()
    
    def _fallback_apple_tv(self) -> Dict[str, any]:
        """Fallback to opening Apple TV in browser"""
        try:
            # Try Edge first, then default browser
            if self.edge_paths:
                return self.launch_in_edge("https://tv.apple.com/")
            else:
                webbrowser.open("https://tv.apple.com/")
                return {
                    "ok": True,
                    "service": "appletv",
                    "method": "browser_fallback",
                    "url": "https://tv.apple.com/"
                }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Apple TV fallback failed: {str(e)}"
            }
    
    def launch_service(self, service: str) -> Dict[str, any]:
        """Launch a streaming service"""
        service = service.lower().strip()
        
        if service not in self.SERVICES:
            return {
                "ok": False,
                "error": f"Unknown service: {service}. Available: {', '.join(self.SERVICES.keys())}"
            }
        
        service_config = self.SERVICES[service]
        
        try:
            # Special handling for Apple TV app
            if service == "appletv":
                return self.launch_apple_tv_app()
            
            # Browser-based services
            url = service_config["url"]
            preferred_browser = service_config.get("browser", "default")
            
            if preferred_browser == "chrome":
                result = self.launch_in_chrome(url)
                if not result["ok"] and self.edge_paths:
                    # Fallback to Edge if Chrome fails
                    logger.info(f"Chrome failed for {service}, trying Edge")
                    result = self.launch_in_edge(url)
            elif preferred_browser == "edge":
                result = self.launch_in_edge(url)
                if not result["ok"] and self.chrome_paths:
                    # Fallback to Chrome if Edge fails
                    logger.info(f"Edge failed for {service}, trying Chrome")
                    result = self.launch_in_chrome(url)
            else:
                # Default browser
                webbrowser.open(url)
                result = {
                    "ok": True,
                    "service": service,
                    "url": url,
                    "browser": "default"
                }
            
            # Add service info to result
            if result["ok"]:
                result["service"] = service
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to launch service {service}: {e}")
            return {
                "ok": False,
                "error": f"Failed to launch {service}: {str(e)}"
            }
    
    def get_available_services(self) -> Dict[str, Dict[str, any]]:
        """Get list of available services and their status"""
        services_status = {}
        
        for service_name, config in self.SERVICES.items():
            status = {
                "available": True,
                "method": "browser",
                "requirements": []
            }
            
            if service_name == "appletv":
                status["method"] = "app"
                if not self.apple_tv_moniker:
                    status["available"] = False
                    status["requirements"].append("Apple TV app moniker not configured")
            else:
                preferred_browser = config.get("browser", "default")
                if preferred_browser == "chrome" and not self.chrome_paths:
                    status["requirements"].append("Google Chrome not found")
                elif preferred_browser == "edge" and not self.edge_paths:
                    status["requirements"].append("Microsoft Edge not found")
            
            services_status[service_name] = status
        
        return services_status
    
    def test_browsers(self) -> Dict[str, any]:
        """Test browser availability"""
        return {
            "chrome": {
                "available": len(self.chrome_paths) > 0,
                "paths": self.chrome_paths
            },
            "edge": {
                "available": len(self.edge_paths) > 0,
                "paths": self.edge_paths
            },
            "apple_tv_moniker": self.apple_tv_moniker
        }
    
    def update_apple_tv_moniker(self, moniker: str):
        """Update Apple TV app moniker"""
        self.apple_tv_moniker = moniker.strip()