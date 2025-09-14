#!/usr/bin/env python3
"""
Utility functions for MyLocalAPI
Common helpers for file operations, Windows integration, etc.
"""

import os
import sys
import logging
import socket
import subprocess
import winreg
from pathlib import Path
from typing import Optional, List, Dict

def get_app_data_dir() -> str:
    """Get application data directory"""
    if sys.platform == 'win32':
        app_data = os.environ.get('APPDATA', '')
        if app_data:
            return os.path.join(app_data, 'MyLocalAPI')
    
    # Fallback for non-Windows or missing APPDATA
    home = os.path.expanduser('~')
    return os.path.join(home, '.mylocalapi')

def setup_logging(log_file: Optional[str] = None) -> None:
    """Setup application logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler()]
    if log_file:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            handlers.append(logging.FileHandler(log_file))
        except OSError:
            pass  # Continue without file logging if it fails
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers
    )

def is_admin() -> bool:
    """Check if running with administrator privileges"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def find_available_port(start_port: int = 1482, max_attempts: int = 100) -> int:
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    
    raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_attempts}")

def is_port_in_use(port: int, host: str = '127.0.0.1') -> bool:
    """Check if a port is in use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False

class AutostartManager:
    """Manages application autostart on Windows"""
    
    APP_NAME = "MyLocalAPI"
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if autostart is enabled"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REGISTRY_PATH) as key:
                winreg.QueryValueEx(key, cls.APP_NAME)
                return True
        except FileNotFoundError:
            return False
        except Exception:
            return False
    
    @classmethod
    def enable(cls, executable_path: str) -> bool:
        """Enable autostart"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REGISTRY_PATH, 0, 
                              winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, executable_path)
            return True
        except Exception as e:
            logging.error(f"Failed to enable autostart: {e}")
            return False
    
    @classmethod
    def disable(cls) -> bool:
        """Disable autostart"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REGISTRY_PATH, 0,
                              winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, cls.APP_NAME)
            return True
        except FileNotFoundError:
            return True  # Already disabled
        except Exception as e:
            logging.error(f"Failed to disable autostart: {e}")
            return False

def run_subprocess_safe(cmd: List[str], timeout: int = 30, 
                       capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run subprocess with safe error handling and timeout"""
    try:
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command timed out after {timeout} seconds: {' '.join(cmd)}")
    except FileNotFoundError:
        raise RuntimeError(f"Command not found: {cmd[0]}")
    except Exception as e:
        raise RuntimeError(f"Command failed: {e}")

def find_bundled_executable(exe_name: str) -> Optional[str]:
    """Find bundled executable in various common locations"""
    # Check if running as PyInstaller bundle
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
        exe_path = os.path.join(bundle_dir, exe_name)
        if os.path.exists(exe_path):
            return exe_path
    
    # Check script directory and subdirectories
    if hasattr(sys, 'frozen'):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    search_paths = [
        base_dir,
        os.path.join(base_dir, 'bin'),
        os.path.join(base_dir, 'tools'),
        os.path.join(base_dir, 'scripts'),
        os.path.join(base_dir, 'scripts', 'svcl-x64'),
    ]
    
    for path in search_paths:
        exe_path = os.path.join(path, exe_name)
        if os.path.exists(exe_path):
            return exe_path
    
    # Check PATH
    try:
        result = subprocess.run(['where' if sys.platform == 'win32' else 'which', exe_name], 
                              capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except Exception:
        pass
    
    return None

def open_file_location(filepath: str) -> bool:
    """Open file location in Windows Explorer"""
    if not os.path.exists(filepath):
        return False
    
    try:
        if sys.platform == 'win32':
            subprocess.run(['explorer', '/select,', filepath], check=True)
        else:
            # Fallback for non-Windows (shouldn't happen in this app)
            subprocess.run(['xdg-open', os.path.dirname(filepath)], check=True)
        return True
    except Exception:
        return False

def safe_kill_process_by_name(process_name: str) -> bool:
    """Safely kill processes by name"""
    try:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/IM', process_name], 
                         capture_output=True, check=False)
        else:
            subprocess.run(['pkill', '-f', process_name], 
                         capture_output=True, check=False)
        return True
    except Exception:
        return False

def get_windows_version() -> str:
    """Get Windows version string"""
    try:
        import platform
        return f"{platform.system()} {platform.version()}"
    except Exception:
        return "Unknown"

def ensure_single_instance(app_name: str = "MyLocalAPI") -> bool:
    """Ensure only one instance of the app is running"""
    if sys.platform == 'win32':
        try:
            import msvcrt
            import tempfile
            lock_file = os.path.join(tempfile.gettempdir(), f'{app_name}.lock')
            try:
                lock_handle = os.open(lock_file, os.O_CREAT | os.O_TRUNC | os.O_RDWR)
                msvcrt.locking(lock_handle, msvcrt.LK_NBLCK, 1)
                return True
            except (OSError, IOError):
                return False
        except ImportError:
            pass
    
    # Fallback method using socket (cross-platform)
    try:
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.bind(('127.0.0.1', 0))  # Bind to any available port
        return True
    except Exception:
        return False

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def truncate_string(text: str, max_length: int = 50) -> str:
    """Truncate string with ellipsis if too long"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def validate_executable(exe_path: str) -> bool:
    """Validate that a file exists and appears to be executable"""
    if not exe_path or not os.path.exists(exe_path):
        return False
    
    if not os.path.isfile(exe_path):
        return False
    
    # Check if it has executable extension on Windows
    if sys.platform == 'win32':
        valid_extensions = ['.exe', '.cmd', '.bat', '.com']
        if not any(exe_path.lower().endswith(ext) for ext in valid_extensions):
            return False
    
    return True

def create_firewall_rule(port: int, rule_name: str = "MyLocalAPI", allow_network: bool = False) -> bool:
    """Create Windows Firewall rule for the application"""
    if not sys.platform == 'win32':
        return True  # Not applicable on non-Windows
    
    try:
        # Remove existing rule first
        subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={rule_name}'],
                      capture_output=True, check=False)
        
        # Create new rule
        if allow_network:
            # Allow from any address
            cmd = [
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                f'name={rule_name}', 'dir=in', 'action=allow', 'protocol=TCP',
                f'localport={port}', 'profile=private,domain'
            ]
        else:
            # Allow only from localhost
            cmd = [
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                f'name={rule_name}', 'dir=in', 'action=allow', 'protocol=TCP',
                f'localport={port}', 'remoteip=127.0.0.1', 'profile=private,domain'
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
        
    except Exception as e:
        logging.error(f"Failed to create firewall rule: {e}")
        return False

def get_local_network_ip() -> Optional[str]:
    """Get the local network IP address"""
    try:
        import socket
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return None

def get_network_interfaces() -> List[Dict[str, str]]:
    """Get available network interfaces"""
    interfaces = []
    try:
        import socket
        import psutil

        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:  # IPv4
                    interfaces.append({
                        'name': interface,
                        'ip': addr.address,
                        'netmask': addr.netmask
                    })

        return interfaces
    except Exception:
        return []

def clean_audio_device_id(device_id: Optional[str]) -> str:
    """Clean and normalize audio device ID string"""
    if not device_id:
        return ""

    # Remove common prefixes that svcl.exe might output
    device_id = device_id.strip()

    # Remove "X items found:" prefix if present
    import re
    device_id = re.sub(r'^\d+\s+items?\s+found:\s*', '', device_id, flags=re.IGNORECASE)

    # Extract the actual device ID if it's embedded in other text
    match = re.search(r'([^\\]+\\Device\\[^\\]+\\Render)', device_id, re.IGNORECASE)
    if match:
        return match.group(1)

    return device_id.strip()