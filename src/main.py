#!/usr/bin/env python3
"""
MyLocalAPI - Local HTTP server for PC control
Main entry point and application coordinator

Author: Aidan Paetsch
Date: 2025-09-15
License: See LICENSE (GNU GPL v3.0)
Disclaimer: Provided AS IS. See README.md 'AS IS Disclaimer' for details.
"""

import os
import sys
import threading
import time
import argparse
try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except Exception:
    ctk = None
    CTK_AVAILABLE = False
import tkinter as tk
from tkinter import messagebox, filedialog
import webbrowser
import tempfile
import ctypes
from ctypes import wintypes

from src.server import FlaskServer
from src.gui import MainWindow
from src.settings import SettingsManager
from src.utils import get_app_data_dir, is_admin, setup_logging, check_and_elevate
import logging


def resource_path(*relative_parts):
    """Return an absolute path to a resource bundled by PyInstaller.

    When running as a onefile bundle PyInstaller extracts files to a
    temporary folder referenced by sys._MEIPASS. When not bundled this
    returns a path relative to the project source directory.
    """
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *relative_parts)

class MyLocalAPIApp:
    """Main application class that coordinates all components"""
    
    def __init__(self):
        self.settings_manager = SettingsManager()
        self.flask_server = None
        self.main_window = None
        self.tray_icon = None
        self.running = False
        
        # Create app data directory
        self.app_data_dir = get_app_data_dir()
        os.makedirs(self.app_data_dir, exist_ok=True)
        
        # Setup logging
        setup_logging(os.path.join(self.app_data_dir, 'mylocalapi.log'))
        # On Windows, set an explicit AppUserModelID so the OS uses our icon
        # and groups windows properly in the taskbar (prevents generic Python icon)
        try:
            if sys.platform == 'win32':
                try:
                    APPID = 'com.mylocalapi'
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)
                except Exception:
                    pass
        except Exception:
            pass
        
    def create_tray_icon(self):
        """Create system tray icon"""
        # Lazy import pystray and PIL to avoid import-time dependency
        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception:
            pystray = None
            Image = None
            ImageDraw = None

        # Prefer bundled tray icon files when available (ICO for Windows).
        tray_ico = resource_path('MyLocalAPI_app_icon_new.ico')
        tray_png = resource_path('mylocalapiappicon.png')
        app_png = resource_path('mylocalapiappicon.png')

        image = None
        try:
            if Image is not None and os.path.exists(tray_ico):
                try:
                    image = Image.open(tray_ico)
                except Exception:
                    image = None

            if Image is not None and image is None:
                source = None
                for candidate in (tray_png, app_png):
                    if os.path.exists(candidate):
                        source = candidate
                        break

                if source:
                    try:
                        src_img = Image.open(source).convert('RGBA')
                        ico_sizes = [(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]
                        tmp_ico_path = os.path.join(tempfile.gettempdir(), 'mylocalapi_tray_temp.ico')
                        try:
                            src_img.save(tmp_ico_path, format='ICO', sizes=ico_sizes)
                            image = Image.open(tmp_ico_path)
                        except Exception:
                            image = src_img.resize((16,16), Image.LANCZOS)
                    except Exception:
                        image = None
        except Exception:
            image = None

        if image is None and Image is not None:
            try:
                image = Image.new('RGBA', (128, 128), color=(70, 130, 180, 255))
                draw = ImageDraw.Draw(image)
                draw.ellipse([32, 32, 96, 96], fill=(255, 255, 255, 255))
                draw.text((44, 40), "M", fill=(0, 0, 128, 255))
            except Exception:
                image = None

        # Create menu handlers and pystray icon if available
        if pystray is None:
            # pystray not available - skip creating a tray icon
            self.tray_icon = None
            return

        def on_left_click(icon, item):
            self.show_main_window()

        def on_quit(icon, item):
            self.quit_application()

        def on_start_server(icon, item):
            self.start_server()

        def on_stop_server(icon, item):
            self.stop_server()

        def on_restart_server(icon, item):
            self.restart_server()

        def on_open_browser(icon, item):
            port = self.settings_manager.get_setting('port', 1482)
            webbrowser.open(f'http://localhost:{port}/')

        menu_items = [
            pystray.MenuItem('Open MyLocalAPI', on_open_browser),
            pystray.MenuItem('Settings...', on_left_click),
            pystray.MenuItem(f'Port: {self.settings_manager.get_setting("port", 1482)}', lambda: None, enabled=False),
            pystray.MenuItem('Start', on_start_server, enabled=lambda item: not self.is_server_running()),
            pystray.MenuItem('Stop', on_stop_server, enabled=lambda item: self.is_server_running()),
            pystray.MenuItem('Restart', on_restart_server, enabled=lambda item: self.is_server_running()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', on_quit)
        ]

        # If image is None, pystray will still accept a PIL Image or other acceptable formats
        self.tray_icon = pystray.Icon("MyLocalAPI", image, menu=pystray.Menu(*menu_items))
        
    def update_tray_menu(self):
        """Update tray menu to reflect current state"""
        if not self.tray_icon:
            return
            
        port = self.settings_manager.get_setting('port', 1482)
        server_running = self.is_server_running()
        
        def on_left_click(icon, item):
            self.show_main_window()
            
        def on_quit(icon, item):
            self.quit_application()
            
        def on_start_server(icon, item):
            self.start_server()
            
        def on_stop_server(icon, item):
            self.stop_server()
            
        def on_restart_server(icon, item):
            self.restart_server()
            
        def on_open_browser(icon, item):
            webbrowser.open(f'http://localhost:{port}/')
        
        # Lazily import pystray so this function can run even if pystray
        # isn't installed in the environment used for quick import checks.
        try:
            import pystray
        except Exception:
            return

        menu_items = [
            pystray.MenuItem('Open MyLocalAPI', on_open_browser),
            pystray.MenuItem('Settings...', on_left_click),
            pystray.MenuItem(f'Port: {port}', lambda: None, enabled=False),
            pystray.MenuItem('Start', on_start_server, enabled=not server_running),
            pystray.MenuItem('Stop', on_stop_server, enabled=server_running),
            pystray.MenuItem('Restart', on_restart_server, enabled=server_running),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', on_quit)
        ]

        self.tray_icon.menu = pystray.Menu(*menu_items)
        
    def show_main_window(self):
        """Show and focus the main window"""
        if not self.main_window:
            # Create a CTk root for the application UI
            if CTK_AVAILABLE:
                root = ctk.CTk()
                try:
                    ctk.set_appearance_mode('dark')
                    ctk.set_default_color_theme('dark-blue')
                except Exception:
                    pass
            else:
                # Fallback to native Tk if customtkinter is not available
                root = tk.Tk()

            self.main_window = MainWindow(root, self)

            # (Rounded-corner region code removed to avoid rendering/taskbar issues on Windows.)
            
        # Show and focus window
        self.main_window.root.deiconify()
        self.main_window.root.lift()
        self.main_window.root.focus_force()

        # Ensure the taskbar icon is applied (some platforms/Timings require reapplying after show)
        try:
            if hasattr(self.main_window, '_ensure_taskbar_icon'):
                # Schedule slightly after show to ensure the HWND is valid/mapped
                self.main_window.root.after(50, lambda: self.main_window._ensure_taskbar_icon())
                # Secondary attempt after a longer delay to increase reliability
                try:
                    self.main_window.root.after(500, lambda: self.main_window._ensure_taskbar_icon())
                except Exception:
                    pass
        except Exception:
            pass
        
        # Try to bring to front on Windows
        try:
            import win32gui
            import win32con
            import pywintypes
            hwnd = self.main_window.root.winfo_id()
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
            except pywintypes.error:
                self.main_window.root.attributes('-topmost', True)
                self.main_window.root.after(100, lambda: self.main_window.root.attributes('-topmost', False))
        except ImportError:
            pass 
            
    def start_server(self):
        """Start the Flask server"""
        if self.flask_server and self.flask_server.is_running():
            return False
            
        # Validate settings first
        validation_errors = self.settings_manager.validate_settings()
        if validation_errors:
            messagebox.showerror("Configuration Error", 
                               f"Cannot start server:\n" + "\n".join(validation_errors))
            return False
            
        try:
            self.flask_server = FlaskServer(self.settings_manager)
            self.flask_server.start()
            
            # Ensure firewall rule is properly configured
            self.settings_manager.ensure_firewall_rule()
            
            self.update_tray_menu()
            if self.main_window:
                self.main_window.update_server_status()
            return True
        except Exception as e:
            messagebox.showerror("Server Error", f"Failed to start server: {str(e)}")
            return False
            
    def stop_server(self):
        """Stop the Flask server"""
        if self.flask_server:
            self.flask_server.stop()
            self.flask_server = None
        self.update_tray_menu()
        if self.main_window:
            self.main_window.update_server_status()
            
    def restart_server(self):
        """Restart the Flask server"""
        self.stop_server()
        time.sleep(0.5)  # Brief pause
        return self.start_server()
        
    def is_server_running(self):
        """Check if server is running"""
        return self.flask_server and self.flask_server.is_running()
        
    def quit_application(self):
        """Gracefully quit the application"""
        self.running = False
        
        # Stop server
        if self.flask_server:
            self.flask_server.stop()
            
        # Stop tray icon
        if self.tray_icon:
            self.tray_icon.stop()
            
        # Close main window
        if self.main_window:
            try:
                self.main_window.root.quit()
            except:
                pass
                
        sys.exit(0)
        
    def run(self):
        """Run the application"""
        self.running = True
        
        # Create tray icon
        self.create_tray_icon()
        
        # Start tray icon in separate thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
        
        # Show main window initially
        self.show_main_window()
        
        # Run Tkinter main loop
        try:
            self.main_window.root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.quit_application()

def main():
    """Main entry point"""
    # Handle command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='MyLocalAPI - Local HTTP server for PC control')
    parser.add_argument('--elevated', action='store_true', help='Internal flag for elevated restart')
    parser.add_argument('--no-elevation', action='store_true', help='Skip automatic elevation check')
    args = parser.parse_args()
    
    # Check for administrator privileges and elevate if needed (unless disabled)
    if sys.platform == 'win32' and not args.no_elevation:
        try:
            if check_and_elevate(force=False, show_prompt=True):
                # Elevation was requested, exit this instance
                sys.exit(0)
        except Exception as e:
            logging.warning(f"Elevation check failed: {e}")
    
    # Log admin status
    if is_admin():
        logging.info("Running with administrator privileges - full functionality available")
    else:
        logging.info("Running without administrator privileges - fan control may be limited")
    
    # Check if already running (simple check)
    import tempfile
    
    # Import fcntl only on non-Windows systems
    fcntl = None
    if sys.platform != 'win32':
        try:
            import fcntl
        except ImportError:
            pass
    
    if sys.platform == 'win32':
        # Windows single instance check
        import msvcrt
        try:
            lock_file = os.path.join(tempfile.gettempdir(), 'mylocalapi.lock')
            lock_handle = os.open(lock_file, os.O_CREAT | os.O_TRUNC | os.O_RDWR)
            msvcrt.locking(lock_handle, msvcrt.LK_NBLCK, 1)
            ctypes.windll.user32.SetProcessDpiAwarenessContext(wintypes.HANDLE(-4))
        except (OSError, IOError):
            messagebox.showerror("Already Running", 
                               "MyLocalAPI is already running. Check your system tray.")
            sys.exit(1)
    
    # Create and run application
    app = MyLocalAPIApp()

    # First-run: prompt to create desktop shortcut (non-blocking, safe)
    try:
        from .utils import prompt_create_desktop_shortcut, resource_path as _rp
        try:
            icon = _rp('MyLocalAPI_app_icon_new.ico') if hasattr(_rp, '__call__') else None
        except Exception:
            icon = None

        try:
            # Only prompt when running interactively (not when running tests)
            prompt_create_desktop_shortcut(app_name='MyLocalAPI', target=None, icon=icon)
        except Exception:
            pass
    except Exception:
        pass
    app.run()

if __name__ == '__main__':
    main()