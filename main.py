#!/usr/bin/env python3
"""
MyLocalAPI - Local HTTP server for PC control
Main entry point and application coordinator
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw
import webbrowser
import tempfile

from server import FlaskServer
from gui import MainWindow
from settings import SettingsManager
from utils import get_app_data_dir, is_admin, setup_logging
import logging

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
        
    def create_tray_icon(self):
        """Create system tray icon"""
        # Prefer bundled tray icon files when available (ICO for Windows).
        # To avoid an extremely tiny icon on high-DPI systems, create an ICO
        # that contains multiple sizes so Windows can pick the best one.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tray_ico = os.path.join(base_dir, 'MyLocalAPI_app_icon_new.ico')
        tray_png = os.path.join(base_dir, 'mylocalapiappicon.png')
        app_png = os.path.join(base_dir, 'mylocalapiappicon.png')

        image = None
        try:
            # If there's a real ICO, prefer it (it may already contain multiple sizes)
            if os.path.exists(tray_ico):
                try:
                    image = Image.open(tray_ico)
                except Exception:
                    image = None

            # If no ICO, try PNG sources and build a multi-size ICO in temp
            if image is None:
                source = None
                for candidate in (tray_png, app_png):
                    if os.path.exists(candidate):
                        source = candidate
                        break

                if source:
                    try:
                        src_img = Image.open(source).convert('RGBA')
                        # Create a multi-size ICO file so Windows will select an appropriate size
                        ico_sizes = [(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]
                        tmp_ico_path = os.path.join(tempfile.gettempdir(), 'mylocalapi_tray_temp.ico')
                        try:
                            src_img.save(tmp_ico_path, format='ICO', sizes=ico_sizes)
                            image = Image.open(tmp_ico_path)
                        except Exception:
                            # If ICO creation fails, fall back to a larger PNG resized
                            image = src_img.resize((64,64), Image.LANCZOS)
                    except Exception:
                        image = None
        except Exception:
            image = None

        # Fallback: generate a simple icon if no image was loaded
        if image is None:
            image = Image.new('RGBA', (128, 128), color=(70, 130, 180, 255))
            draw = ImageDraw.Draw(image)
            draw.ellipse([32, 32, 96, 96], fill=(255, 255, 255, 255))
            draw.text((44, 40), "M", fill=(0, 0, 128, 255))

        # Log what we will use for the tray icon (helpful for debugging tiny icons)
        logger = logging.getLogger(__name__)
        try:
            logger.debug(f"Tray icon image size: {getattr(image, 'size', None)}; mode: {getattr(image, 'mode', None)}")
        except Exception:
            pass

        # Many tray backends and Windows scale icons down if the provided image is very small
        # or contains lots of transparent padding. Provide a reasonably large, square image
        # for pystray to convert: 64x64 is a good compromise for most DPI settings.
        try:
            py_icon = image
            if getattr(py_icon, 'size', (0, 0)) != (64, 64):
                try:
                    py_icon = image.resize((64, 64), Image.LANCZOS)
                except Exception:
                    py_icon = image.copy()
        except Exception:
            py_icon = image
        
        def on_left_click(icon, item):
            """Handle left click - show main window"""
            self.show_main_window()
            
        def on_quit(icon, item):
            """Handle quit action"""
            self.quit_application()
            
        def on_start_server(icon, item):
            """Handle start server action"""
            self.start_server()
            
        def on_stop_server(icon, item):
            """Handle stop server action"""
            self.stop_server()
            
        def on_restart_server(icon, item):
            """Handle restart server action"""
            self.restart_server()
            
        def on_open_browser(icon, item):
            """Handle open in browser action"""
            port = self.settings_manager.get_setting('port', 1482)
            webbrowser.open(f'http://127.0.0.1:{port}/')
        
        # Create menu items
        menu_items = [
            pystray.MenuItem('Open MyLocalAPI', on_open_browser),
            pystray.MenuItem('Settings...', on_left_click),
            pystray.MenuItem(f'Port: {self.settings_manager.get_setting("port", 1482)}', 
                           lambda: None, enabled=False),
            pystray.MenuItem('Start', on_start_server, 
                           enabled=lambda item: not self.is_server_running()),
            pystray.MenuItem('Stop', on_stop_server,
                           enabled=lambda item: self.is_server_running()),
            pystray.MenuItem('Restart', on_restart_server,
                           enabled=lambda item: self.is_server_running()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', on_quit)
        ]
        
        self.tray_icon = pystray.Icon(
            "MyLocalAPI",
            image,
            menu=pystray.Menu(*menu_items)
        )
        
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
            root = tk.Tk()
            self.main_window = MainWindow(root, self)
            
        # Show and focus window
        self.main_window.root.deiconify()
        self.main_window.root.lift()
        self.main_window.root.focus_force()

        # Ensure the taskbar icon is applied (some platforms/Timings require reapplying after show)
        try:
            if hasattr(self.main_window, '_ensure_taskbar_icon'):
                # Schedule slightly after show to ensure the HWND is valid/mapped
                self.main_window.root.after(50, lambda: self.main_window._ensure_taskbar_icon())
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
                # SetForegroundWindow can fail due to foreground-locking rules.
                # Fallback: briefly set the window as topmost to bring it to front.
                self.main_window.root.attributes('-topmost', True)
                self.main_window.root.after(100, lambda: self.main_window.root.attributes('-topmost', False))
        except ImportError:
            pass  # pywin32 not available
            
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
            
            # Create appropriate firewall rule
            port = self.settings_manager.get_setting('port', 1482)
            host = self.settings_manager.get_setting('host', '127.0.0.1')
            allow_network = (host == '0.0.0.0' or host not in ['127.0.0.1', 'localhost'])
            
            from utils import create_firewall_rule
            create_firewall_rule(port, "MyLocalAPI", allow_network)
            
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
        except (OSError, IOError):
            messagebox.showerror("Already Running", 
                               "MyLocalAPI is already running. Check your system tray.")
            sys.exit(1)
    
    # Create and run application
    app = MyLocalAPIApp()
    app.run()

if __name__ == '__main__':
    main()