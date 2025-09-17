#!/usr/bin/env python3
"""
Utility functions for MyLocalAPI
Common helpers for file operations, Windows integration, etc.

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE (GNU GPL v3.0)
Disclaimer: Provided AS IS. See README.md 'AS IS Disclaimer' for details.
"""

import os
import sys
import logging
import socket
import subprocess
import winreg
from pathlib import Path
from typing import Optional, List, Dict, Any

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

def request_admin_privileges(script_path: Optional[str] = None, args: Optional[List[str]] = None) -> bool:
    """
    Request administrator privileges and restart the application
    Returns True if elevation was requested, False if already admin or error
    """
    if is_admin():
        return False  # Already running as admin
    
    try:
        import ctypes
        
        # Determine the script/executable to run
        if script_path is None:
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                script_path = sys.executable
            else:
                # Running as Python script
                script_path = sys.argv[0]
        
        # Prepare arguments
        if args is None:
            args = sys.argv[1:]  # Use current command line args
        
        # Add a flag to indicate this is an elevated restart
        if '--elevated' not in args:
            args = ['--elevated'] + args
        
        if getattr(sys, 'frozen', False):
            # For compiled executable, run directly
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                script_path, 
                ' '.join(args) if args else None,
                None, 
                1  # SW_NORMAL
            )
        else:
            # For Python script, run with Python interpreter
            python_exe = sys.executable
            script_args = [script_path] + args
            
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas", 
                python_exe,
                ' '.join(f'"{arg}"' for arg in script_args),
                None,
                1  # SW_NORMAL
            )
        
        logging.info("Requested administrator privileges, application should restart elevated")
        return True
        
    except Exception as e:
        logging.error(f"Failed to request admin privileges: {e}")
        return False

def check_and_elevate(force: bool = False, show_prompt: bool = True) -> bool:
    """
    Check if admin privileges are needed and elevate if necessary
    
    Args:
        force: Force elevation regardless of need
        show_prompt: Show user prompt before elevating
    
    Returns:
        True if elevation was requested (app should exit)
        False if no elevation needed or user declined
    """
    # Check if we're already elevated or if this is an elevated restart
    if is_admin() or '--elevated' in sys.argv:
        return False
    
    # Check if admin privileges are actually needed
    need_admin = force
    
    if not need_admin:
        # Check if fan control is configured (requires admin)
        try:
            from settings import SettingsManager
            settings = SettingsManager()
            fan_enabled = settings.get_setting('fan.enabled', False)
            fan_exe = settings.get_setting('fan.fan_exe_path', '')
            
            if fan_enabled and fan_exe and os.path.exists(fan_exe):
                need_admin = True
                logging.info("Fan control is configured and enabled - admin privileges recommended")
        except Exception as e:
            logging.debug(f"Could not check fan control settings: {e}")
    
    if not need_admin:
        return False
    
    if show_prompt:
        # Show prompt to user
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            # Create a temporary root window for the messagebox
            root = tk.Tk()
            root.withdraw()  # Hide the root window
            
            message = (
                "MyLocalAPI needs administrator privileges for full functionality:\n\n"
                "• Fan control requires elevated permissions\n"
                "• Some Windows APIs need admin access\n\n"
                "Would you like to restart with administrator privileges?"
            )
            
            response = messagebox.askyesno(
                "Administrator Privileges Required",
                message,
                icon='question'
            )
            
            root.destroy()
            
            if not response:
                logging.info("User declined administrator privilege elevation")
                return False
                
        except Exception as e:
            logging.warning(f"Could not show elevation prompt: {e}")
            # Continue with elevation attempt
    
    # Request elevation
    if request_admin_privileges():
        logging.info("Administrator privilege elevation requested - exiting current instance")
        return True
    else:
        logging.warning("Failed to request administrator privileges")
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
    # Check if running as PyInstaller bundle and search the temporary
    # extraction directory (_MEIPASS) including common subfolders.
    if getattr(sys, 'frozen', False):
        bundle_dir = getattr(sys, '_MEIPASS', None)
        if bundle_dir:
            # Candidate locations inside the extracted bundle
            candidates = [
                os.path.join(bundle_dir, exe_name),
                os.path.join(bundle_dir, 'scripts', exe_name),
                os.path.join(bundle_dir, 'svcl-x64', exe_name),
                os.path.join(bundle_dir, 'scripts', 'svcl-x64', exe_name),
                os.path.join(bundle_dir, 'bin', exe_name),
                os.path.join(bundle_dir, 'tools', exe_name),
            ]
            for exe_path in candidates:
                if os.path.exists(exe_path):
                    return exe_path
    
    # Check script directory and subdirectories (development or on-disk install)
    if getattr(sys, 'frozen', False):
        # When bundled in onefile, resources are inside _MEIPASS; however
        # some users may install the onefile next to a sibling 'scripts' dir
        # so also check the executable directory as a fallback.
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

def remove_firewall_rule(rule_name: str = "MyLocalAPI", port: Optional[int] = None) -> bool:
    """Remove Windows Firewall rule"""
    if not sys.platform == 'win32':
        return True  # Not applicable on non-Windows
    
    try:
        if port:
            # Remove rule by name and port for more precision
            cmd = ['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={rule_name}', f'localport={port}']
        else:
            # Remove all rules with this name
            cmd = ['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={rule_name}']
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        success = result.returncode == 0
        
        if success:
            logging.info(f"Successfully removed firewall rule: {rule_name}")
        else:
            logging.debug(f"Firewall rule {rule_name} may not have existed")
        
        return success
        
    except Exception as e:
        logging.error(f"Failed to remove firewall rule: {e}")
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


def _get_desktop_path() -> str:
    """Return the current user's desktop path on Windows or a reasonable fallback."""
    try:
        if sys.platform == 'win32':
            from pathlib import Path
            return str(Path(os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')))
        else:
            return os.path.join(os.path.expanduser('~'), 'Desktop')
    except Exception:
        return os.path.join(os.path.expanduser('~'), 'Desktop')


def create_desktop_shortcut(app_name: str, target: str, args: str = '', icon: Optional[str] = None, description: str = '') -> bool:
    """Create a Windows .lnk desktop shortcut using win32com if available.

    Falls back to creating a simple .url file if win32com is not present.
    Returns True on success, False otherwise.
    """
    desktop = _get_desktop_path()
    try:
        os.makedirs(desktop, exist_ok=True)
        shortcut_path = os.path.join(desktop, f"{app_name}.lnk")

        try:
            # Preferred method: win32com
            from win32com.client import Dispatch
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = target
            shortcut.Arguments = args or ''
            shortcut.WorkingDirectory = os.path.dirname(target)
            if icon and os.path.exists(icon):
                shortcut.IconLocation = icon
            if description:
                shortcut.Description = description
            shortcut.save()
            return True
        except Exception:
            # Fallback: create a .url (internet shortcut) file that points to the exe
            url_path = os.path.join(desktop, f"{app_name}.url")
            try:
                with open(url_path, 'w', encoding='utf-8') as fh:
                    fh.write('[InternetShortcut]\n')
                    # file URI scheme - point to the exe path
                    fh.write('URL=file:///' + target.replace('\\', '/') + '\n')
                    if icon and os.path.exists(icon):
                        fh.write('IconFile=' + icon + '\n')
                return True
            except Exception:
                return False

    except Exception:
        return False


def prompt_create_desktop_shortcut(app_name: str = 'MyLocalAPI', target: Optional[str] = None, icon: Optional[str] = None, description: str = '') -> bool:
    """Prompt the user (first-run) to create a desktop shortcut.

    Creates a marker file in the app data dir so the prompt is only shown once.
    Returns True if a shortcut was created, False otherwise.
    """
    try:
        marker = os.path.join(get_app_data_dir(), 'first_run_shortcut_done')
        if os.path.exists(marker):
            return False

        # Determine a sensible default target if not provided
        if not target:
            if getattr(sys, 'frozen', False):
                # If running from a bundled exe, point the shortcut at the running exe
                target = sys.executable
            else:
                # If running from source, prefer a packaged executable if present
                try:
                    from pathlib import Path
                    proj_root = Path(__file__).parent.parent.resolve()
                    # Common PyInstaller outputs:
                    candidates = [
                        proj_root / 'dist' / 'MyLocalAPI.exe',
                        proj_root / 'dist' / 'MyLocalAPI' / 'MyLocalAPI.exe'
                    ]

                    # If none of the common candidates exist, search dist for any exe
                    if not any(p.exists() for p in candidates):
                        dist_dir = proj_root / 'dist'
                        if dist_dir.exists():
                            exes = list(dist_dir.rglob('*.exe'))
                            preferred = None
                            for e in exes:
                                if e.name.lower().startswith('mylocalapi'):
                                    preferred = e
                                    break
                            if preferred is None and exes:
                                preferred = exes[0]
                            if preferred:
                                candidates = [preferred]

                    # Pick the first existing candidate
                    for p in candidates:
                        if p and p.exists():
                            target = str(p)
                            break
                except Exception:
                    target = None

                # Final fallback: the running script path
                if not target:
                    target = os.path.abspath(sys.argv[0])

        # Attempt to prompt user with a simple Tk dialog
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            resp = messagebox.askyesno('Create Desktop Shortcut', f"Create a desktop shortcut for {app_name}?")
            root.destroy()
            if not resp:
                # Mark as shown to avoid prompting again
                try:
                    os.makedirs(os.path.dirname(marker), exist_ok=True)
                    with open(marker, 'w') as fh:
                        fh.write('no')
                except Exception:
                    pass
                return False
        except Exception:
            # If GUI prompt fails, don't force creation
            return False

        success = create_desktop_shortcut(app_name, target, args='', icon=icon, description=description)

        try:
            os.makedirs(os.path.dirname(marker), exist_ok=True)
            with open(marker, 'w') as fh:
                fh.write('yes' if success else 'no')
        except Exception:
            pass

        return success
    except Exception:
        return False