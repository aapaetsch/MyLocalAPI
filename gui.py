#!/usr/bin/env python3
"""
Tkinter GUI for MyLocalAPI
Main window with settings management and server control
"""

import os
import sys
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
import requests
import json
import logging
from typing import Any, Dict, List, Optional

from utils import AutostartManager, validate_executable, open_file_location
from settings import SettingsManager

logger = logging.getLogger(__name__)

class MainWindow:
    """Main GUI window for MyLocalAPI"""
    
    def __init__(self, root: tk.Tk, app):
        self.root = root
        self.app = app  # Reference to main app
        self.settings_manager = app.settings_manager
        
        # GUI state variables
        self.port_var = tk.StringVar()
        self.token_var = tk.StringVar()
        self.server_status_var = tk.StringVar()
        
        # Settings variables
        self.audio_enabled_var = tk.BooleanVar()
        self.svv_path_var = tk.StringVar()
        self.fan_enabled_var = tk.BooleanVar()
        self.fan_exe_var = tk.StringVar()
        self.fan_config_var = tk.StringVar()
        self.fan_apply_var = tk.BooleanVar()
        self.streaming_enabled_var = tk.BooleanVar()
        self.apple_tv_moniker_var = tk.StringVar()
        self.autostart_var = tk.BooleanVar()
        
        self._setup_window()
        self._create_widgets()
        self._load_settings()
        self._setup_bindings()
        
        # Start status update timer
        self.root.after(1000, self._update_status_timer)
    
    def _setup_window(self):
        """Setup main window properties"""
        self.root.title("MyLocalAPI - Settings")
        self.root.geometry("700x800")
        self.root.minsize(600, 800)
        self._apply_steel_blue_theme()

        # Hide native title bar and create a custom one that matches the theme.
        # overrideredirect removes the OS chrome; we must provide our own controls.
        try:
            # Remove native decorations
            self.root.overrideredirect(True)
        except Exception:
            # If this fails for some platforms, continue without custom titlebar
            logger.debug("overrideredirect not available; using native title bar")

        # Load icons (keep references on self to avoid GC) and ensure they're small
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_dir, 'mylocalapiappicon.png')
            tray_path = os.path.join(base_dir, 'systemtrayicon.png')
            # Prefer bundled ICOs when available (Windows)
            app_ico_path = os.path.join(base_dir, 'MyLocalAPI_app_icon_new.ico')
            tray_ico_path = os.path.join(base_dir, 'MyLocalAPI_tray_icon_new.ico')
            # Expose for later use
            self._app_ico_path = app_ico_path
            self._tray_ico_path = tray_ico_path

            # Desired display sizes (increased app icon size)
            APP_ICON_SIZE = (32, 32)
            TRAY_ICON_SIZE = (16, 16)

            # Try Pillow for high-quality resize
            try:
                from PIL import Image, ImageTk
                try:
                    img = Image.open(icon_path).convert('RGBA')
                    img = img.resize(APP_ICON_SIZE, Image.LANCZOS)
                    self._app_icon = ImageTk.PhotoImage(img)
                    try:
                        self.root.iconphoto(True, self._app_icon)
                    except Exception:
                        pass
                except Exception:
                    self._app_icon = None

                try:
                    timg = Image.open(tray_path).convert('RGBA')
                    timg = timg.resize(TRAY_ICON_SIZE, Image.LANCZOS)
                    self._tray_icon_img = ImageTk.PhotoImage(timg)
                except Exception:
                    self._tray_icon_img = None
                # On Windows, prefer bundled .ico files; otherwise create a temp .ico from the PNG
                try:
                    if os.name == 'nt':
                        if os.path.exists(app_ico_path):
                            try:
                                self.root.iconbitmap(app_ico_path)
                                self._temp_icon_ico = app_ico_path
                            except Exception:
                                pass
                        elif os.path.exists(icon_path):
                            ico_path = os.path.join(tempfile.gettempdir(), 'mylocalapi_temp_icon.ico')
                            try:
                                with Image.open(icon_path) as _im:
                                    _im.save(ico_path, format='ICO', sizes=[APP_ICON_SIZE])
                                try:
                                    self.root.iconbitmap(ico_path)
                                    self._temp_icon_ico = ico_path
                                except Exception:
                                    pass
                            except Exception:
                                pass
                except Exception:
                    pass
            except Exception:
                # Pillow not available - fall back to PhotoImage and subsample if needed
                try:
                    tmp = tk.PhotoImage(file=icon_path)
                    iw = tmp.width()
                    ih = tmp.height()
                    maxdim = max(APP_ICON_SIZE)
                    if iw > maxdim or ih > maxdim:
                        sx = max(1, int(iw / maxdim))
                        sy = max(1, int(ih / maxdim))
                        s = max(sx, sy)
                        tmp = tmp.subsample(s, s)
                    self._app_icon = tmp
                    try:
                        self.root.iconphoto(True, self._app_icon)
                    except Exception:
                        pass
                except Exception:
                    self._app_icon = None

                try:
                    tmp2 = tk.PhotoImage(file=tray_path)
                    iw = tmp2.width()
                    ih = tmp2.height()
                    maxdim = max(TRAY_ICON_SIZE)
                    if iw > maxdim or ih > maxdim:
                        sx = max(1, int(iw / maxdim))
                        sy = max(1, int(ih / maxdim))
                        s = max(sx, sy)
                        tmp2 = tmp2.subsample(s, s)
                    self._tray_icon_img = tmp2
                except Exception:
                    self._tray_icon_img = None
                # If Pillow isn't available, try to set iconbitmap from provided .ico files
                try:
                    if os.name == 'nt':
                        # Prefer the bundled ICO names if present
                        for candidate in (app_ico_path, os.path.splitext(icon_path)[0] + '.ico'):
                            if os.path.exists(candidate):
                                try:
                                    self.root.iconbitmap(candidate)
                                    self._temp_icon_ico = candidate
                                    break
                                except Exception:
                                    pass
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Could not load icons: {e}")

        # Build the custom titlebar (if overrideredirect succeeded)
        try:
            if self.root.overrideredirect():
                # overrideredirect() returns current state when called with no args
                # If it returned True above then we proceed, otherwise try to create anyway
                self._create_custom_titlebar()
            else:
                # Attempt to create custom titlebar even if overrideredirect returned False
                # Some platforms ignore overrideredirect - this will still add a top bar inside the client area
                self._create_custom_titlebar()
        except Exception:
            # If anything goes wrong, fall back to native title bar
            logger.debug("Could not create custom titlebar; falling back to native title bar")
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Schedule a deferred ensure of taskbar icon on Windows. Some backends
        # require the window to be mapped before window styles and WM_SETICON can be applied.
        try:
            if os.name == 'nt':
                # run shortly after the main loop starts / window is created
                self.root.after(100, lambda: self._ensure_taskbar_icon())
        except Exception:
            pass
        
        # Note: platform-specific window styling (rounded corners) is intentionally
        # omitted here. If you want native rounded corners on Windows, we can add
        # pywin32-based calls later behind a capability check.
    
    def _apply_steel_blue_theme(self):
        """Apply a steel-blue dark theme to the Tkinter/ttk UI"""
        try:
            style = ttk.Style(self.root)
            # Prefer a theme that allows color tuning
            try:
                style.theme_use('clam')
            except Exception:
                try:
                    style.theme_use(style.theme_use())
                except Exception:
                    pass

            # Your requested palette
            app_bg = "#282A3A"   # app background
            field_bg = "#1E1F2B" # fields / panels
            accent = "#4682B4"   # steel blue accent for buttons/links
            accent_hover = "#5A9AD0"
            fg = "#E6EEF3"
            muted = "#9AA7B2"

            # Expose palette on self so other methods (custom titlebar) can reuse
            self._app_bg = app_bg
            self._field_bg = field_bg
            self._accent = accent
            self._accent_hover = accent_hover
            self._fg = fg
            self._muted = muted

            # Root/background
            self.root.configure(bg=app_bg)
            self.root.option_add('*Foreground', fg)
            self.root.option_add('*Font', 'TkDefaultFont 10')
            self.root.option_add('*Listbox.background', field_bg)
            self.root.option_add('*Entry.background', field_bg)
            self.root.option_add('*Text.background', field_bg)
            self.root.option_add('*TCombobox*Listbox.background', field_bg)

            # General ttk styling
            style.configure('.', background=app_bg, foreground=fg, fieldbackground=field_bg)
            style.configure('TFrame', background=field_bg)
            style.configure('TLabel', background=field_bg, foreground=fg)
            style.configure('TLabelframe', background=field_bg, foreground=fg)
            style.configure('TLabelframe.Label', background=field_bg, foreground=fg)
            style.configure('TEntry', fieldbackground=field_bg, foreground=fg)
            style.configure('TCombobox', fieldbackground=field_bg, background=field_bg, foreground=fg)
            style.map('TCombobox',
                      fieldbackground=[('readonly', field_bg), ('!readonly', field_bg)],
                      background=[('readonly', field_bg), ('!readonly', field_bg)])

            # Notebook / Tabs
            style.configure('TNotebook', background=field_bg)
            style.configure('TNotebook.Tab', background=field_bg, foreground=muted, padding=(8, 6))
            style.map('TNotebook.Tab',
                      background=[('selected', app_bg)],
                      foreground=[('selected', fg)])

            # Scrollbar troughs and thumbs
            style.configure('Vertical.TScrollbar', troughcolor=field_bg, background=app_bg)
            style.configure('Horizontal.TScrollbar', troughcolor=field_bg, background=app_bg)

            # Button: create a pill-like style (flat, no border) — real rounded corners require custom images/widgets
            style.configure('Rounded.TButton',
                            background=accent,
                            foreground=fg,
                            relief='flat',
                            borderwidth=0,
                            focusthickness=0,
                            padding=(8, 6))
            style.map('Rounded.TButton',
                      background=[('active', accent_hover), ('disabled', '#2A2D36')])

            # Make default TButton use the rounded look
            style.configure('TButton', background=accent, foreground=fg, padding=(6,4))
            style.map('TButton', background=[('active', accent_hover)])

            # Hover style for ttk buttons (used when pointer is over a button)
            style.configure('Hover.TButton', background=accent_hover, foreground=fg)

            # Ensure buttons show pointer cursor by default
            try:
                self.root.option_add('*Button.cursor', 'hand2')
                self.root.option_add('*TButton.cursor', 'hand2')
            except Exception:
                pass

            # Bind class-level events so all buttons get hover/cursor behavior
            try:
                # ttk Buttons
                self.root.bind_class('TButton', '<Enter>', lambda e: self._on_button_enter(e), add='+')
                self.root.bind_class('TButton', '<Leave>', lambda e: self._on_button_leave(e), add='+')
                # tk Buttons
                self.root.bind_class('Button', '<Enter>', lambda e: self._on_button_enter(e), add='+')
                self.root.bind_class('Button', '<Leave>', lambda e: self._on_button_leave(e), add='+')
            except Exception:
                pass

            # For widgets that ignore ttk style, set option defaults
            self.root.option_add('*Button.background', accent)
            self.root.option_add('*Button.foreground', fg)
            self.root.option_add('*Label.background', field_bg)
            self.root.option_add('*Entry.background', field_bg)
        except Exception as e:
            logger.debug(f"Could not apply custom theme: {e}")

    def _ensure_taskbar_icon(self):
        """Ensure the window shows a proper taskbar icon on Windows.

        This is separated so callers (for example `show_main_window`) can
        reapply styles and WM_SETICON after the window is mapped.
        """
        if os.name != 'nt':
            return

        try:
            import ctypes

            # Constants
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080

            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1
            IMAGE_ICON = 1
            LR_LOADFROMFILE = 0x00000010

            hwnd = self.root.winfo_id()

            # Update extended style: add APPWINDOW, remove TOOLWINDOW
            try:
                exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                exstyle = (exstyle & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle)

                # Apply the style changes
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_NOZORDER = 0x0004
                SWP_FRAMECHANGED = 0x0020
                flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED
                ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, flags)
            except Exception:
                # non-fatal
                pass

            # If we have a .ico path available from earlier setup, load it and set WM_SETICON
            try:
                ico_path = getattr(self, '_app_ico_path', None)
                if ico_path and os.path.exists(ico_path):
                    hicon = ctypes.windll.user32.LoadImageW(0, ico_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
                    if hicon:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
            except Exception:
                pass

            # Reapply Tk iconphoto too (some environments need both native and Tk bindings)
            try:
                if getattr(self, '_app_icon', None):
                    try:
                        self.root.iconphoto(False, self._app_icon)
                    except Exception:
                        pass
            except Exception:
                pass

            # Gentle refresh
            try:
                self.root.withdraw()
                self.root.deiconify()
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"_ensure_taskbar_icon failed: {e}")

    def _shade_color(self, hex_color: str, percent: float) -> str:
        """Lighten (positive percent) or darken (negative percent) a hex color."""
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)

            def clamp(v):
                return max(0, min(255, int(v)))

            factor = 1.0 + (percent / 100.0)
            r2 = clamp(r * factor)
            g2 = clamp(g * factor)
            b2 = clamp(b * factor)
            return f"#{r2:02x}{g2:02x}{b2:02x}"
        except Exception:
            return hex_color

    def _on_button_enter(self, event):
        """Class-level enter handler for Buttons to show pointer cursor and hover style."""
        try:
            widget = event.widget
            # If the widget is disabled, don't apply hover effects or change cursor
            try:
                # ttk buttons support instate
                if isinstance(widget, ttk.Button) or widget.winfo_class() == 'TButton':
                    try:
                        if widget.instate(['disabled']):
                            return
                    except Exception:
                        # fall back to cget
                        try:
                            if widget.cget('state') == 'disabled':
                                return
                        except Exception:
                            pass
                else:
                    # tk Button
                    try:
                        if widget.cget('state') == 'disabled':
                            return
                    except Exception:
                        pass
            except Exception:
                pass
            # For ttk buttons, change to hover style
            try:
                if isinstance(widget, ttk.Button) or widget.winfo_class() == 'TButton':
                    widget.configure(style='Hover.TButton')
            except Exception:
                pass
            try:
                widget.configure(cursor='hand2')
            except Exception:
                pass
        except Exception:
            pass

    def _on_button_leave(self, event):
        """Class-level leave handler for Buttons to restore style and cursor."""
        try:
            widget = event.widget
            # If widget is disabled, just ensure cursor is default and don't change style
            try:
                disabled = False
                if isinstance(widget, ttk.Button) or widget.winfo_class() == 'TButton':
                    try:
                        disabled = widget.instate(['disabled'])
                    except Exception:
                        try:
                            disabled = (widget.cget('state') == 'disabled')
                        except Exception:
                            disabled = False
                else:
                    try:
                        disabled = (widget.cget('state') == 'disabled')
                    except Exception:
                        disabled = False
                if not disabled:
                    try:
                        if isinstance(widget, ttk.Button) or widget.winfo_class() == 'TButton':
                            widget.configure(style='TButton')
                    except Exception:
                        pass
                # Always try to restore cursor to default
                try:
                    widget.configure(cursor='')
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass

    def _create_custom_titlebar(self):
        """Create a custom titlebar to replace the native one."""
        try:
            # Titlebar container (tall enough for a larger icon)
            titlebar = tk.Frame(self.root, bg=self._app_bg, height=32)
            titlebar.pack(fill=tk.X, side=tk.TOP)

            # Left: app icon (if loaded)
            if getattr(self, '_app_icon', None):
                icon_label = tk.Label(titlebar, image=self._app_icon, bg=self._app_bg)
                icon_label.pack(side=tk.LEFT, padx=(6, 6), pady=2)
            else:
                icon_label = tk.Label(titlebar, text=' ', bg=self._app_bg)
                icon_label.pack(side=tk.LEFT, padx=(6, 6), pady=2)

            # Title
            title_label = tk.Label(titlebar, text=self.root.title(), bg=self._app_bg, fg=self._fg,
                                   font=("TkDefaultFont", 10, "bold"))
            title_label.pack(side=tk.LEFT, padx=(0, 6))

            # Middle spacer
            spacer = tk.Frame(titlebar, bg=self._app_bg)
            spacer.pack(side=tk.LEFT, expand=True, fill=tk.X)

            # Left-side Minimize button (per user request)
            min_btn = tk.Button(titlebar, text='—', bg=self._field_bg, fg=self._fg,
                                relief='flat', bd=0, width=3, command=self._minimize_window, cursor='hand2')
            min_btn.pack(side=tk.LEFT, padx=(6, 4), pady=6)

            # Close button on the right
            close_btn = tk.Button(titlebar, text='✕', bg=self._field_bg, fg=self._fg,
                                  relief='flat', bd=0, width=3, command=self._on_window_close, cursor='hand2')
            close_btn.pack(side=tk.RIGHT, padx=(0, 6), pady=6)

            # Hover effects for buttons
            def _on_enter(btn):
                try:
                    btn.configure(bg=self._shade_color(self._field_bg, 12))
                except Exception:
                    pass

            def _on_leave(btn):
                try:
                    btn.configure(bg=self._field_bg)
                except Exception:
                    pass

            for b in (min_btn, close_btn):
                b.bind('<Enter>', lambda e, btn=b: _on_enter(btn))
                b.bind('<Leave>', lambda e, btn=b: _on_leave(btn))

            # Enable dragging the window by the titlebar
            for widget in (titlebar, title_label, icon_label):
                widget.bind('<ButtonPress-1>', self._start_move)
                widget.bind('<ButtonRelease-1>', self._stop_move)
                widget.bind('<B1-Motion>', self._on_move)

            # Keep references so GC doesn't collect
            self._titlebar_widgets = {
                'frame': titlebar,
                'title': title_label,
                'icon': icon_label,
                'min': min_btn,
                'close': close_btn
            }
        except Exception as e:
            logger.debug(f"Failed to create custom titlebar: {e}")

    # Window dragging helpers
    def _start_move(self, event):
        try:
            self._x_offset = event.x
            self._y_offset = event.y
            # Set a grab/move cursor on titlebar widgets while dragging
            try:
                prev = {}
                widgets = getattr(self, '_titlebar_widgets', {})
                for name, w in widgets.items():
                    # store previous cursor to restore later
                    try:
                        prev[name] = w.cget('cursor')
                    except Exception:
                        prev[name] = ''
                    try:
                        # Use a hand cursor during the drag to indicate a grab (not the move/cross icon)
                        w.configure(cursor='trek')
                    except Exception:
                        pass
                self._titlebar_prev_cursors = prev
            except Exception:
                pass
        except Exception:
            self._x_offset = 0
            self._y_offset = 0

    def _stop_move(self, event):
        # Restore previous cursors for titlebar widgets
        try:
            prev = getattr(self, '_titlebar_prev_cursors', None)
            widgets = getattr(self, '_titlebar_widgets', {})
            if prev:
                for name, w in widgets.items():
                    try:
                        orig = prev.get(name, '')
                        w.configure(cursor=orig if orig else '')
                    except Exception:
                        pass
                try:
                    del self._titlebar_prev_cursors
                except Exception:
                    pass
        except Exception:
            pass

        self._x_offset = None
        self._y_offset = None

    def _on_move(self, event):
        try:
            x = event.x_root - self._x_offset
            y = event.y_root - self._y_offset
            self.root.geometry(f'+{x}+{y}')
        except Exception:
            pass

    def _minimize_window(self):
        """Minimize to tray (withdraw)."""
        try:
            self.root.withdraw()
        except Exception:
            try:
                self.root.iconify()
            except Exception:
                pass
    
    def _create_widgets(self):
        """Create all GUI widgets"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Server status section
        self._create_status_section(main_frame)
        
        # Port and Token section
        self._create_connection_section(main_frame)
        
        # Tabbed interface
        self._create_tabbed_interface(main_frame)
        
        # Bottom controls
        self._create_bottom_controls(main_frame)
    
    def _create_status_section(self, parent):
        """Create server status section"""
        status_frame = ttk.LabelFrame(parent, text="Server Status")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Status display
        status_display_frame = ttk.Frame(status_frame)
        status_display_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(status_display_frame, text="Status:").pack(side=tk.LEFT)
        self.status_label = ttk.Label(status_display_frame, textvariable=self.server_status_var,
                                     foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Control buttons
        button_frame = ttk.Frame(status_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="Start", command=self._start_server)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self._stop_server)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.restart_button = ttk.Button(button_frame, text="Restart", command=self._restart_server)
        self.restart_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="Open Browser", 
                  command=self._open_browser).pack(side=tk.RIGHT)
    
    def _create_connection_section(self, parent):
        """Create connection settings section"""
        conn_frame = ttk.LabelFrame(parent, text="Connection Settings")
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Port setting
        port_frame = ttk.Frame(conn_frame)
        port_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(port_frame, text="Port:").pack(side=tk.LEFT)
        port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=8)
        port_entry.pack(side=tk.LEFT, padx=(5, 8))
        
        # Token setting
        token_frame = ttk.Frame(conn_frame)
        token_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(token_frame, text="Token:").pack(side=tk.LEFT)
        token_entry = ttk.Entry(token_frame, textvariable=self.token_var, width=30, show="*")
        token_entry.pack(side=tk.LEFT, padx=(5, 8), fill=tk.X, expand=True)
        
        ttk.Button(token_frame, text="Show", command=self._toggle_token_visibility).pack(side=tk.RIGHT, padx=(8,0))
    
    def _create_tabbed_interface(self, parent):
        """Create tabbed interface"""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Settings tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        self._create_settings_tab()
        
        # Endpoints tab
        self.endpoints_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.endpoints_frame, text="Endpoints")
        self._create_endpoints_tab()

    def _attach_mousewheel(self, canvas: tk.Canvas, widget: tk.Widget):
        """Attach cross-platform mousewheel scrolling when pointer is over widget/canvas.

        On <Enter> we bind global mousewheel events so scrolling works without focus.
        On <Leave> we unbind them to avoid interfering with other widgets.
        """
        def _on_mousewheel(event):
            # Linux (Button-4/5)
            if getattr(event, 'num', None) == 4:
                canvas.yview_scroll(-1, 'units')
            elif getattr(event, 'num', None) == 5:
                canvas.yview_scroll(1, 'units')
            else:
                # Windows and macOS use event.delta
                delta = getattr(event, 'delta', 0)
                if delta:
                    # On Windows, delta is multiple of 120. Positive = wheel up.
                    try:
                        step = int(delta / 120)
                    except Exception:
                        step = 1 if delta > 0 else -1
                    # Invert sign so wheel-up scrolls up
                    canvas.yview_scroll(-step, 'units')

        def _bind_all(e=None):
            widget.bind_all('<MouseWheel>', _on_mousewheel)
            widget.bind_all('<Button-4>', _on_mousewheel)
            widget.bind_all('<Button-5>', _on_mousewheel)

        def _unbind_all(e=None):
            try:
                widget.unbind_all('<MouseWheel>')
                widget.unbind_all('<Button-4>')
                widget.unbind_all('<Button-5>')
            except Exception:
                pass

        # Bind enter/leave on both the canvas and the inner widget so hovering anywhere works
        widget.bind('<Enter>', _bind_all)
        widget.bind('<Leave>', _unbind_all)
        canvas.bind('<Enter>', _bind_all)
        canvas.bind('<Leave>', _unbind_all)
    
    def _create_settings_tab(self):
        """Create settings tab content"""
        # Create scrollable frame
        canvas = tk.Canvas(self.settings_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # Create window and ensure the inner frame width always matches the canvas width
        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def _on_canvas_config(e):
            try:
                canvas.itemconfigure(window_id, width=e.width)
            except Exception:
                pass

        canvas.bind('<Configure>', _on_canvas_config)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.configure(yscrollcommand=scrollbar.set)
        # Attach mousewheel scrolling when hovering anywhere in the scrollable area
        self._attach_mousewheel(canvas, scrollable_frame)
        
        # Audio section
        self._create_audio_section(scrollable_frame)
        
        # Fan section
        self._create_fan_section(scrollable_frame)
        
        # Streaming section
        self._create_streaming_section(scrollable_frame)
        
        # System section
        self._create_system_section(scrollable_frame)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_audio_section(self, parent):
        """Create audio control section"""
        audio_frame = ttk.LabelFrame(parent, text="Audio Control")
        audio_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Enable checkbox
        ttk.Checkbutton(audio_frame, text="Enable audio control endpoints",
                       variable=self.audio_enabled_var,
                       command=self._on_audio_enabled_changed).pack(anchor=tk.W, padx=10, pady=5)
        
        # SVV path
        svv_frame = ttk.Frame(audio_frame)
        svv_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(svv_frame, text="SoundVolumeView Path:").pack(anchor=tk.W)
        path_frame = ttk.Frame(svv_frame)
        path_frame.pack(fill=tk.X, pady=(2, 0))
        
        self.svv_entry = ttk.Entry(path_frame, textvariable=self.svv_path_var)
        self.svv_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(path_frame, text="Browse", command=self._browse_svv_path).pack(side=tk.RIGHT)
        
        help_label = ttk.Label(svv_frame, text="Optional: svcl.exe/SoundVolumeView will be bundled; only fill this to use a local installation.",
                              foreground="gray", font=("TkDefaultFont", 8))
        help_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Device mappings
        mapping_frame = ttk.LabelFrame(audio_frame, text="Device Mappings")
        mapping_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Mappings header
        header_frame = ttk.Frame(mapping_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(header_frame, text="Label").grid(row=0, column=0, sticky="w", padx=(0, 10))
        # Nudge the Device ID header right so it lines up with the device_id entry widgets
        ttk.Label(header_frame, text="Device ID").grid(row=0, column=1, sticky="w", padx=(6, 10))
        # Center the header for the streaming column so checkboxes align beneath it
        ttk.Label(header_frame, text="For Streaming", anchor='center').grid(row=0, column=2, sticky="ew", padx=(0, 10))
        ttk.Button(header_frame, text="Add", command=self._add_device_mapping).grid(row=0, column=3, sticky="e")

        header_frame.columnconfigure(1, weight=1)
        # Give the streaming column a minimum width so the checkbox can be centered
        header_frame.columnconfigure(2, minsize=80)
        
        # Mappings container
        self.mappings_container = ttk.Frame(mapping_frame)
        self.mappings_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        self.mapping_rows = []
    
    def _create_fan_section(self, parent):
        """Create fan control section"""
        fan_frame = ttk.LabelFrame(parent, text="Fan Control")
        fan_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Enable checkbox
        ttk.Checkbutton(fan_frame, text="Enable fan control endpoints",
                       variable=self.fan_enabled_var,
                       command=self._on_fan_enabled_changed).pack(anchor=tk.W, padx=10, pady=5)
        
        # Fan exe path
        exe_frame = ttk.Frame(fan_frame)
        exe_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(exe_frame, text="FanControl.exe Path:").pack(anchor=tk.W)
        exe_path_frame = ttk.Frame(exe_frame)
        exe_path_frame.pack(fill=tk.X, pady=(2, 0))
        
        self.fan_exe_entry = ttk.Entry(exe_path_frame, textvariable=self.fan_exe_var)
        self.fan_exe_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(exe_path_frame, text="Browse", command=self._browse_fan_exe).pack(side=tk.RIGHT)
        
        # Fan config path
        config_frame = ttk.Frame(fan_frame)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(config_frame, text="Fan Config Directory:").pack(anchor=tk.W)
        config_path_frame = ttk.Frame(config_frame)
        config_path_frame.pack(fill=tk.X, pady=(2, 0))
        
        self.fan_config_entry = ttk.Entry(config_path_frame, textvariable=self.fan_config_var)
        self.fan_config_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(config_path_frame, text="Browse", command=self._browse_fan_config).pack(side=tk.RIGHT)
        
        # Apply on stream launch
        apply_frame = ttk.Frame(fan_frame)
        apply_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Checkbutton(apply_frame, text="Apply fan config on stream launch",
                       variable=self.fan_apply_var,
                       command=self._on_fan_apply_changed).pack(anchor=tk.W)
        
        # Config selection dropdown (shown when apply is enabled)
        self.fan_config_select_frame = ttk.Frame(apply_frame)
        
        ttk.Label(self.fan_config_select_frame, text="Selected Config:").pack(anchor=tk.W, pady=(5, 2))
        
        config_select_frame = ttk.Frame(self.fan_config_select_frame)
        config_select_frame.pack(fill=tk.X)
        
        self.fan_config_combo = ttk.Combobox(config_select_frame, state="readonly")
        self.fan_config_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(config_select_frame, text="Refresh", 
                  command=self._refresh_fan_configs).pack(side=tk.RIGHT)
    
    def _create_streaming_section(self, parent):
        """Create streaming section"""
        streaming_frame = ttk.LabelFrame(parent, text="Streaming Services")
        streaming_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Enable streaming endpoint
        ttk.Checkbutton(streaming_frame, text="Launch streaming service by endpoint",
                       variable=self.streaming_enabled_var,
                       command=self._on_streaming_enabled_changed).pack(anchor=tk.W, padx=10, pady=5)
        
        # Apple TV moniker
        appletv_frame = ttk.Frame(streaming_frame)
        appletv_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(appletv_frame, text="Apple TV App Moniker:").pack(anchor=tk.W)
        moniker_frame = ttk.Frame(appletv_frame)
        moniker_frame.pack(fill=tk.X, pady=(2, 0))
        
        self.appletv_entry = ttk.Entry(moniker_frame, textvariable=self.apple_tv_moniker_var)
        self.appletv_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(moniker_frame, text="Auto-detect", 
                  command=self._auto_detect_appletv).pack(side=tk.RIGHT)
    
    def _create_system_section(self, parent):
        """Create system section"""
        system_frame = ttk.LabelFrame(parent, text="System")
        system_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Autostart
        ttk.Checkbutton(system_frame, text="Launch on system startup",
                       variable=self.autostart_var,
                       command=self._on_autostart_changed).pack(anchor=tk.W, padx=10, pady=5)
        
        # Settings management
        settings_frame = ttk.Frame(system_frame)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(settings_frame, text="Reset to Defaults",
                  command=self._reset_settings).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(settings_frame, text="Export Settings",
                  command=self._export_settings).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(settings_frame, text="Import Settings",
                  command=self._import_settings).pack(side=tk.LEFT)
    
    def _create_endpoints_tab(self):
        """Create endpoints tab content"""
        # Create scrollable frame
        canvas = tk.Canvas(self.endpoints_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.endpoints_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # Create window and ensure the inner frame width always matches the canvas width
        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def _on_canvas_config(e):
            try:
                canvas.itemconfigure(window_id, width=e.width)
            except Exception:
                pass

        canvas.bind('<Configure>', _on_canvas_config)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.configure(yscrollcommand=scrollbar.set)
        # Attach mousewheel scrolling when hovering anywhere in the scrollable area
        self._attach_mousewheel(canvas, scrollable_frame)
        
        # Endpoint definitions
        endpoints = [
            {
                "group": "Audio Control",
                "enabled_setting": "audio.enabled",
                "endpoints": [
                    {
                        "path": "/switch",
                        "method": "GET", 
                        "params": "key=<label>&token=<token> OR id=<device_id>&token=<token>",
                        "description": "Switch default audio device",
                        "test_params": "key=headphones"
                    },
                    {
                        "path": "/volume",
                        "method": "GET",
                        "params": "percent=<0-100>&token=<token>",
                        "description": "Set system volume percentage",
                        "test_params": "percent=50"
                    },
                    {
                        "path": "/volume/current",
                        "method": "GET",
                        "params": "token=<token>",
                        "description": "Get current volume and device info",
                        "test_params": ""
                    },
                    {
                        "path": "/device/current",
                        "method": "GET", 
                        "params": "token=<token>",
                        "description": "Get current default device info",
                        "test_params": ""
                    },
                    {
                        "path": "/list",
                        "method": "GET",
                        "params": "token=<token>",
                        "description": "List all playback devices",
                        "test_params": ""
                    }
                ]
            },
            {
                "group": "Streaming Services",
                "enabled_setting": "streaming.launch_streaming_by_endpoint", 
                "endpoints": [
                    {
                        "path": "/openStreaming",
                        "method": "GET",
                        "params": "service=<youtube|crunchyroll|netflix|disney|prime|appletv>&token=<token>",
                        "description": "Launch streaming service and switch audio",
                        "test_params": "service=youtube"
                    }
                ]
            },
            {
                "group": "Fan Control",
                "enabled_setting": "fan.enabled",
                "endpoints": [
                    {
                        "path": "/fan/apply",
                        "method": "GET",
                        "params": "name=<config>&token=<token> OR percent=<0-100>&token=<token>",
                        "description": "Apply fan configuration or percentage",
                        "test_params": "percent=50"
                    },
                    {
                        "path": "/fan/refresh",
                        "method": "GET",
                        "params": "token=<token>",
                        "description": "Refresh fan sensors",
                        "test_params": ""
                    },
                    {
                        "path": "/fan/configs",
                        "method": "GET",
                        "params": "token=<token>&nearestTo=<percent>",
                        "description": "Get available fan configurations",
                        "test_params": "nearestTo=75"
                    },
                    {
                        "path": "/fan/status",
                        "method": "GET",
                        "params": "token=<token>",
                        "description": "Get fan control status",
                        "test_params": ""
                    }
                ]
            },
            {
                "group": "System",
                "enabled_setting": None,  # Always enabled
                "endpoints": [
                    {
                        "path": "/status",
                        "method": "GET",
                        "params": "token=<token>",
                        "description": "Get overall system status",
                        "test_params": ""
                    },
                    {
                        "path": "/diag",
                        "method": "GET",
                        "params": "token=<token>",
                        "description": "Get diagnostic information",
                        "test_params": ""
                    }
                ]
            }
        ]
        
        self.endpoint_widgets = []
        
        for group_info in endpoints:
            # Group frame
            group_frame = ttk.LabelFrame(scrollable_frame, text=group_info["group"])
            group_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Status indicator
            status_frame = ttk.Frame(group_frame)
            status_frame.pack(fill=tk.X, padx=10, pady=5)
            
            status_indicator = tk.Label(status_frame, text="●", font=("TkDefaultFont", 12))
            status_indicator.pack(side=tk.LEFT)
            
            status_label = ttk.Label(status_frame, text="Enabled" if group_info["enabled_setting"] is None else "Unknown")
            status_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # Store for updating
            self.endpoint_widgets.append({
                "group": group_info["group"],
                "enabled_setting": group_info["enabled_setting"],
                "indicator": status_indicator,
                "label": status_label
            })
            
            # Endpoints
            for endpoint in group_info["endpoints"]:
                ep_frame = ttk.Frame(group_frame)
                ep_frame.pack(fill=tk.X, padx=20, pady=2)
                
                # Endpoint info
                info_frame = ttk.Frame(ep_frame)
                info_frame.pack(fill=tk.X)
                
                ttk.Label(info_frame, text=f"{endpoint['method']} {endpoint['path']}",
                         font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)
                
                ttk.Label(info_frame, text=endpoint["description"],
                         foreground="gray").pack(anchor=tk.W)
                
                if endpoint["params"]:
                    ttk.Label(info_frame, text=f"Parameters: {endpoint['params']}",
                             font=("TkDefaultFont", 8)).pack(anchor=tk.W)
                
                # Test button and result
                test_frame = ttk.Frame(ep_frame)
                test_frame.pack(fill=tk.X, pady=(2, 5))
                
                test_button = ttk.Button(test_frame, text="Test", width=8,
                                        command=lambda ep=endpoint: self._test_endpoint(ep))
                test_button.pack(side=tk.LEFT, padx=(0, 5))
                
                # Copy curl button
                curl_button = ttk.Button(test_frame, text="Copy cURL", width=10,
                                        command=lambda ep=endpoint: self._copy_curl(ep))
                curl_button.pack(side=tk.LEFT, padx=(0, 5))
                
                # Result area
                result_text = tk.Text(test_frame, height=2, wrap=tk.WORD, font=("TkDefaultFont", 8))
                result_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                # Store for testing
                endpoint["test_button"] = test_button
                endpoint["result_text"] = result_text
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_bottom_controls(self, parent):
        """Create bottom control buttons"""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Server controls (left side)
        server_frame = ttk.Frame(bottom_frame)
        server_frame.pack(side=tk.LEFT)
        
        self.bottom_start_btn = ttk.Button(server_frame, text="Start", command=self._start_server)
        self.bottom_start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.bottom_stop_btn = ttk.Button(server_frame, text="Stop", command=self._stop_server)
        self.bottom_stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.bottom_restart_btn = ttk.Button(server_frame, text="Restart", command=self._restart_server)
        self.bottom_restart_btn.pack(side=tk.LEFT)
        
        # Status message (right side)
        self.status_message_var = tk.StringVar()
        self.status_message_label = ttk.Label(bottom_frame, textvariable=self.status_message_var,
                                             foreground="gray")
        self.status_message_label.pack(side=tk.RIGHT)
    
    def _setup_bindings(self):
        """Setup event bindings"""
        # Settings change handlers
        self.port_var.trace_add("write", self._on_port_changed)
        self.token_var.trace_add("write", self._on_token_changed)
        self.svv_path_var.trace_add("write", self._on_svv_path_changed)
        self.fan_exe_var.trace_add("write", self._on_fan_exe_changed)
        self.fan_config_var.trace_add("write", self._on_fan_config_changed)
        self.apple_tv_moniker_var.trace_add("write", self._on_apple_tv_moniker_changed)
    
    def _load_settings(self):
        """Load settings into GUI"""
        # Connection settings
        self.port_var.set(str(self.settings_manager.get_setting('port', 1482)))
        self.token_var.set(self.settings_manager.get_setting('token', 'changeme'))
        
        # Audio settings
        self.audio_enabled_var.set(self.settings_manager.get_setting('audio.enabled', True))
        self.svv_path_var.set(self.settings_manager.get_setting('audio.svv_path', ''))
        
        # Fan settings
        self.fan_enabled_var.set(self.settings_manager.get_setting('fan.enabled', False))
        self.fan_exe_var.set(self.settings_manager.get_setting('fan.fan_exe_path', ''))
        self.fan_config_var.set(self.settings_manager.get_setting('fan.fan_config_path', ''))
        self.fan_apply_var.set(self.settings_manager.get_setting('fan.apply_on_stream_launch', False))
        
        # Streaming settings
        self.streaming_enabled_var.set(self.settings_manager.get_setting('streaming.launch_streaming_by_endpoint', True))
        self.apple_tv_moniker_var.set(self.settings_manager.get_setting('streaming.appleTVMoniker', ''))
        
        # System settings
        self.autostart_var.set(AutostartManager.is_enabled())
        
        # Load device mappings
        self._load_device_mappings()
        
        # Update UI state
        self._update_audio_ui_state()
        self._update_fan_ui_state()
        self._update_endpoints_status()
        
        # Try to auto-detect Apple TV moniker if not set
        if not self.apple_tv_moniker_var.get():
            self._auto_detect_appletv()
    
    def _load_device_mappings(self):
        """Load device mappings into UI"""
        # Clear existing rows
        for row_data in self.mapping_rows:
            for widget in row_data["widgets"]:
                widget.destroy()
        self.mapping_rows.clear()
        
        # Load mappings from settings
        mappings = self.settings_manager.get_audio_mappings()
        for mapping in mappings:
            self._add_device_mapping_row(
                mapping.get("label", ""),
                mapping.get("device_id", ""),
                mapping.get("use_for_streaming", False)
            )
        
        # Add one empty row if no mappings exist
        if not mappings:
            self._add_device_mapping_row()
    
    def _add_device_mapping_row(self, label="", device_id="", use_for_streaming=False):
        """Add a device mapping row"""
        row_frame = ttk.Frame(self.mappings_container)
        row_frame.pack(fill=tk.X, pady=2)
        
        label_var = tk.StringVar(value=label)
        device_id_var = tk.StringVar(value=device_id)
        streaming_var = tk.BooleanVar(value=use_for_streaming)
        
        label_entry = ttk.Entry(row_frame, textvariable=label_var, width=15)
        label_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        device_entry = ttk.Entry(row_frame, textvariable=device_id_var)
        device_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        
        streaming_cb = ttk.Checkbutton(row_frame, variable=streaming_var,
                                      command=lambda: self._on_streaming_checkbox_changed(streaming_var))
        # Center the checkbutton in its grid cell
        streaming_cb.grid(row=0, column=2, padx=(0, 5), sticky='nsew')
        try:
            streaming_cb.configure(anchor='center')
        except Exception:
            pass
        
        delete_btn = ttk.Button(row_frame, text="Delete", width=8,
                               command=lambda: self._delete_device_mapping_row(row_data))
        delete_btn.grid(row=0, column=3)

        row_frame.columnconfigure(1, weight=1)
        # Ensure the streaming column can center its child
        row_frame.columnconfigure(2, minsize=80)

        row_data = {
            "frame": row_frame,
            "widgets": [label_entry, device_entry, streaming_cb, delete_btn],
            "vars": {"label": label_var, "device_id": device_id_var, "streaming": streaming_var}
        }
        
        # Setup change handlers
        label_var.trace_add("write", lambda *args: self._save_device_mappings())
        device_id_var.trace_add("write", lambda *args: self._save_device_mappings())
        streaming_var.trace_add("write", lambda *args: self._save_device_mappings())
        
        self.mapping_rows.append(row_data)
        
        return row_data
    
    def _delete_device_mapping_row(self, row_data):
        """Delete a device mapping row"""
        if row_data in self.mapping_rows:
            self.mapping_rows.remove(row_data)
            for widget in row_data["widgets"]:
                widget.destroy()
            row_data["frame"].destroy()
            self._save_device_mappings()
    
    def _save_device_mappings(self):
        """Save device mappings to settings"""
        mappings = []
        for row_data in self.mapping_rows:
            label = row_data["vars"]["label"].get().strip()
            device_id = row_data["vars"]["device_id"].get().strip()
            streaming = row_data["vars"]["streaming"].get()
            
            if label or device_id:  # Only save non-empty rows
                mappings.append({
                    "label": label,
                    "device_id": device_id,
                    "use_for_streaming": streaming
                })
        
        self.settings_manager.set_audio_mappings(mappings)
    
    def _on_streaming_checkbox_changed(self, changed_var):
        """Handle streaming checkbox change - ensure only one is selected"""
        if changed_var.get():  # If this one was checked
            # Uncheck all others
            for row_data in self.mapping_rows:
                streaming_var = row_data["vars"]["streaming"]
                if streaming_var != changed_var:
                    streaming_var.set(False)
        
        self._save_device_mappings()
    
    # Event handlers
    def _on_port_changed(self, *args):
        """Handle port change"""
        try:
            port = int(self.port_var.get())
            if 1024 <= port <= 65535:
                self.settings_manager.set_setting('port', port)
                if self.app.tray_icon:
                    self.app.update_tray_menu()
        except ValueError:
            pass
    
    def _on_token_changed(self, *args):
        """Handle token change"""
        self.settings_manager.set_setting('token', self.token_var.get())
    
    def _on_audio_enabled_changed(self):
        """Handle audio enabled change"""
        self.settings_manager.set_setting('audio.enabled', self.audio_enabled_var.get())
        self._update_audio_ui_state()
        self._update_endpoints_status()
    
    def _on_svv_path_changed(self, *args):
        """Handle SVV path change"""
        self.settings_manager.set_setting('audio.svv_path', self.svv_path_var.get())
    
    def _on_fan_enabled_changed(self):
        """Handle fan enabled change"""
        self.settings_manager.set_setting('fan.enabled', self.fan_enabled_var.get())
        self._update_fan_ui_state()
        self._update_endpoints_status()
    
    def _on_fan_exe_changed(self, *args):
        """Handle fan exe path change"""
        self.settings_manager.set_setting('fan.fan_exe_path', self.fan_exe_var.get())
        self._refresh_fan_configs()
    
    def _on_fan_config_changed(self, *args):
        """Handle fan config path change"""
        self.settings_manager.set_setting('fan.fan_config_path', self.fan_config_var.get())
        self._refresh_fan_configs()
    
    def _on_fan_apply_changed(self):
        """Handle fan apply on stream launch change"""
        enabled = self.fan_apply_var.get()
        self.settings_manager.set_setting('fan.apply_on_stream_launch', enabled)
        
        if enabled:
            self.fan_config_select_frame.pack(fill=tk.X, pady=(5, 0))
            self._refresh_fan_configs()
        else:
            self.fan_config_select_frame.pack_forget()
    
    def _on_streaming_enabled_changed(self):
        """Handle streaming enabled change"""
        self.settings_manager.set_setting('streaming.launch_streaming_by_endpoint', 
                                         self.streaming_enabled_var.get())
        self._update_endpoints_status()
    
    def _on_apple_tv_moniker_changed(self, *args):
        """Handle Apple TV moniker change"""
        self.settings_manager.set_setting('streaming.appleTVMoniker', 
                                         self.apple_tv_moniker_var.get())
    
    def _on_autostart_changed(self):
        """Handle autostart change"""
        enabled = self.autostart_var.get()
        self.settings_manager.set_setting('autostart', enabled)
        
        if enabled:
            # Get executable path
            import sys
            exe_path = sys.executable if hasattr(sys, 'frozen') else __file__
            success = AutostartManager.enable(exe_path)
            if not success:
                messagebox.showerror("Error", "Failed to enable autostart")
                self.autostart_var.set(False)
        else:
            success = AutostartManager.disable()
            if not success:
                messagebox.showwarning("Warning", "Failed to disable autostart")
    
    def _update_audio_ui_state(self):
        """Update audio UI state based on enabled setting"""
        enabled = self.audio_enabled_var.get()
        
        # Enable/disable audio-related widgets
        widgets = [self.svv_entry] + [widget for row in self.mapping_rows for widget in row["widgets"]]
        
        state = "normal" if enabled else "disabled"
        for widget in widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass  # Some widgets don't support state
    
    def _update_fan_ui_state(self):
        """Update fan UI state based on enabled setting"""
        enabled = self.fan_enabled_var.get()
        
        widgets = [self.fan_exe_entry, self.fan_config_entry]
        state = "normal" if enabled else "disabled"
        
        for widget in widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass
        
        # Handle fan apply UI
        if enabled and self.fan_apply_var.get():
            self.fan_config_select_frame.pack(fill=tk.X, pady=(5, 0))
        else:
            self.fan_config_select_frame.pack_forget()
    
    def _update_endpoints_status(self):
        """Update endpoints status indicators"""
        for widget_info in self.endpoint_widgets:
            enabled_setting = widget_info["enabled_setting"]
            
            if enabled_setting is None:
                # Always enabled
                enabled = True
            else:
                enabled = self.settings_manager.get_setting(enabled_setting, True)
            
            # Update indicator
            color = "green" if enabled else "gray"
            text = "Enabled" if enabled else "Disabled"
            
            widget_info["indicator"].configure(foreground=color)
            widget_info["label"].configure(text=text)
    
    # Action handlers
    def _start_server(self):
        """Start the server"""
        success = self.app.start_server()
        if success:
            self.status_message_var.set("Server started successfully")
        else:
            self.status_message_var.set("Failed to start server")
        
        # Clear message after 3 seconds
        self.root.after(3000, lambda: self.status_message_var.set(""))
    
    def _stop_server(self):
        """Stop the server"""
        self.app.stop_server()
        self.status_message_var.set("Server stopped")
        self.root.after(3000, lambda: self.status_message_var.set(""))
    
    def _restart_server(self):
        """Restart the server"""
        success = self.app.restart_server()
        if success:
            self.status_message_var.set("Server restarted successfully")
        else:
            self.status_message_var.set("Failed to restart server")
        
        self.root.after(3000, lambda: self.status_message_var.set(""))
    
    def _open_browser(self):
        """Open server URL in browser"""
        port = self.settings_manager.get_setting('port', 1482)
        webbrowser.open(f'http://127.0.0.1:{port}/')
    
    def _toggle_token_visibility(self):
        """Toggle token field visibility"""
        current_show = self.token_var._tk.globalgetvar(self.token_var._name)
        # This is a simplified approach - full implementation would track show state
        pass
    
    def _browse_svv_path(self):
        """Browse for SVV executable"""
        filename = filedialog.askopenfilename(
            title="Select SoundVolumeView/svcl.exe",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.svv_path_var.set(filename)
    
    def _browse_fan_exe(self):
        """Browse for FanControl executable"""
        filename = filedialog.askopenfilename(
            title="Select FanControl.exe",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.fan_exe_var.set(filename)
    
    def _browse_fan_config(self):
        """Browse for fan config directory"""
        dirname = filedialog.askdirectory(
            title="Select Fan Configuration Directory"
        )
        if dirname:
            self.fan_config_var.set(dirname)
    
    def _add_device_mapping(self):
        """Add new device mapping row"""
        self._add_device_mapping_row()
    
    def _refresh_fan_configs(self):
        """Refresh fan configuration list"""
        try:
            configs = self.settings_manager.parse_fan_configs()
            self.fan_config_combo['values'] = configs
            
            # Select current config if set
            current = self.settings_manager.get_setting('fan.selected_config', '')
            if current in configs:
                self.fan_config_combo.set(current)
            elif configs:
                self.fan_config_combo.set(configs[0])
                self.settings_manager.set_setting('fan.selected_config', configs[0])
                
        except Exception as e:
            logger.error(f"Error refreshing fan configs: {e}")
            messagebox.showerror("Error", f"Failed to refresh fan configs: {str(e)}")
    
    def _auto_detect_appletv(self):
        """Auto-detect Apple TV moniker"""
        try:
            detected = self.settings_manager.find_apple_tv_moniker()
            self.apple_tv_moniker_var.set(detected)
        except Exception as e:
            logger.debug(f"Auto-detection failed: {e}")
    
    def _reset_settings(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Confirm Reset", 
                              "Are you sure you want to reset all settings to defaults?"):
            self.settings_manager.reset_to_defaults()
            self._load_settings()
            messagebox.showinfo("Reset Complete", "Settings have been reset to defaults")
    
    def _export_settings(self):
        """Export settings to file"""
        filename = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            success = self.settings_manager.export_settings(filename)
            if success:
                messagebox.showinfo("Export Success", f"Settings exported to {filename}")
            else:
                messagebox.showerror("Export Error", "Failed to export settings")
    
    def _import_settings(self):
        """Import settings from file"""
        filename = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            success = self.settings_manager.import_settings(filename)
            if success:
                self._load_settings()
                messagebox.showinfo("Import Success", "Settings imported successfully")
            else:
                messagebox.showerror("Import Error", "Failed to import settings")
    
    def _test_endpoint(self, endpoint_info):
        """Test an endpoint"""
        if not self.app.is_server_running():
            endpoint_info["result_text"].delete(1.0, tk.END)
            endpoint_info["result_text"].insert(1.0, "Error: Server is not running")
            return
        
        try:
            # Build URL
            port = self.settings_manager.get_setting('port', 1482)
            token = self.settings_manager.get_setting('token', 'changeme')
            base_url = f"http://127.0.0.1:{port}"
            
            # Build params
            params = {"token": token}
            test_params = endpoint_info.get("test_params", "")
            if test_params:
                for param_pair in test_params.split("&"):
                    if "=" in param_pair:
                        key, value = param_pair.split("=", 1)
                        params[key] = value
            
            # Make request
            url = base_url + endpoint_info["path"]
            response = requests.get(url, params=params, timeout=10)
            
            # Display result
            result_text = f"Status: {response.status_code}\n"
            try:
                result_json = response.json()
                result_text += json.dumps(result_json, indent=2)
            except:
                result_text += response.text
                
            endpoint_info["result_text"].delete(1.0, tk.END)
            endpoint_info["result_text"].insert(1.0, result_text)
            
        except Exception as e:
            endpoint_info["result_text"].delete(1.0, tk.END)
            endpoint_info["result_text"].insert(1.0, f"Error: {str(e)}")
    
    def _copy_curl(self, endpoint_info):
        """Copy cURL command to clipboard"""
        try:
            host = self.settings_manager.get_setting('host', '127.0.0.1')
            port = self.settings_manager.get_setting('port', 1482)
            token = self.settings_manager.get_setting('token', 'changeme')
            
            # Show actual accessible URL in cURL
            if host == '0.0.0.0':
                # Get local IP for network access
                try:
                    import socket
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.connect(("8.8.8.8", 80))
                        display_host = s.getsockname()[0]
                except:
                    display_host = "YOUR_IP_ADDRESS"
            else:
                display_host = host
                
            base_url = f"http://{display_host}:{port}"
            
            # Build params
            params = [f"token={token}"]
            test_params = endpoint_info.get("test_params", "")
            if test_params:
                for param_pair in test_params.split("&"):
                    if "=" in param_pair:
                        params.append(param_pair)
            
            param_string = "&".join(params)
            curl_cmd = f"curl \"{base_url}{endpoint_info['path']}?{param_string}\""
            
            # Copy to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(curl_cmd)
            
            self.status_message_var.set("cURL command copied to clipboard")
            self.root.after(2000, lambda: self.status_message_var.set(""))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy cURL: {str(e)}")
    
    def update_server_status(self):
        """Update server status display"""
        if self.app.is_server_running():
            self.server_status_var.set("Running")
            self.status_label.configure(foreground="green")
            
            # Update buttons
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.restart_button.configure(state="normal")
            
            self.bottom_start_btn.configure(state="disabled")
            self.bottom_stop_btn.configure(state="normal")
            self.bottom_restart_btn.configure(state="normal")
        else:
            self.server_status_var.set("Stopped")
            self.status_label.configure(foreground="red")
            
            # Update buttons
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled") 
            self.restart_button.configure(state="disabled")
            
            self.bottom_start_btn.configure(state="normal")
            self.bottom_stop_btn.configure(state="disabled")
            self.bottom_restart_btn.configure(state="disabled")
    
    def _update_status_timer(self):
        """Timer callback to update status"""
        self.update_server_status()
        # Schedule next update
        self.root.after(2000, self._update_status_timer)
    
    def _on_window_close(self):
        """Handle window close - minimize to tray instead of quit"""
        self.root.withdraw()  # Hide window instead of destroying