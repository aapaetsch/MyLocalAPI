#!/usr/bin/env python3
"""
Tkinter GUI for MyLocalAPI
Main window with settings management and server control

Author: Aidan Paetsch
Date: 2025-09-15
License: MIT (see LICENSE)
Disclaimer: Use at your own risk. See LICENSE for details.
"""

import os
import sys
import tempfile
import tkinter as tk  # Keep for some dialog compatibility
from tkinter import messagebox, filedialog
import tkinter.font as tkfont
import customtkinter as ctk
CTK_AVAILABLE = True
import webbrowser
import requests
import json
import logging

from utils import AutostartManager, validate_executable, open_file_location
from settings import SettingsManager

logger = logging.getLogger(__name__)


class MainWindow:
    # Class-level default palette (can be overridden per-instance)
    APP_BG = "#1E1F2B"
    ALT_BG = "#282A3A"
    INPUT_BG = "#3B3D4B"
    FIELD_BG = INPUT_BG
    SUCCESS = "#BBD760"
    DANGER = "#FC6A6A"
    FG = "#E6EEF3"
    MUTED = "#9AA7B2"
    ACCENT = SUCCESS
    ACCENT_HOVER = "#A8C44A"
    DISABLED_BTN_BG = "#6b6b6b"
    DISABLED_BTN_FG = "#BFC7CF"

    def __init__(self, root: tk.Tk, app):
        self.root = root
        self.app = app  # Reference to main app
        self.settings_manager = app.settings_manager
        self._alt_bg = self.ALT_BG
        self._input_bg = self.INPUT_BG
        self._field_bg = self.FIELD_BG
        self._success = self.SUCCESS
        self._danger = self.DANGER
        self._fg = self.FG
        self._muted = self.MUTED
        self._accent = self.ACCENT
        self._accent_hover = self.ACCENT_HOVER
        self._disabled_btn_bg = self.DISABLED_BTN_BG
        self._disabled_btn_fg = self.DISABLED_BTN_FG
        
        # GUI state variables
        self.port_var = tk.StringVar()
        self.token_var = tk.StringVar()
        self.server_status_var = tk.StringVar()
        # Token visibility flag
        self._token_visible = False
        
        # Settings variables
        self.audio_enabled_var = tk.BooleanVar()
        self.svv_path_var = tk.StringVar()
        # Whether to use a custom SoundVolumeView install (show/hide SVV path input)
        self.use_custom_svv_var = tk.BooleanVar()
        self.fan_enabled_var = tk.BooleanVar()
        self.fan_exe_var = tk.StringVar()
        self.fan_config_var = tk.StringVar()
        self.fan_apply_var = tk.BooleanVar()
        # New: apply on game launch
        self.fan_apply_game_var = tk.BooleanVar()
        self.streaming_enabled_var = tk.BooleanVar()
        self.apple_tv_moniker_var = tk.StringVar()
        
        # Gaming settings variables
        self.gaming_enabled_var = tk.BooleanVar()
        
        self.autostart_var = tk.BooleanVar()
        
        self._setup_window()
        self._create_widgets()
        self._load_settings()
        self._setup_bindings()
        
        # Start status update timer
        self.root.after(1000, self._update_status_timer)

    # Helper factory methods to reduce repeated CTk fallbacks
    def _frame(self, parent, **pack_kwargs):
        # Use CustomTkinter frame (CTk will be bundled)
        return ctk.CTkFrame(parent)

    def _label(self, parent, text=None, textvariable=None, text_color=None, font=None, **kwargs):
        # Use CTkLabel exclusively (CTk will be bundled)
        return ctk.CTkLabel(parent, text=text, textvariable=textvariable, text_color=text_color, font=font)

    def _button(self, parent, text, command=None, fg_color=None, text_color=None, width=None, hover_color=None):
        # Build kwargs only for values provided to avoid passing None to CTk internals
        kwargs = {}
        if fg_color is not None:
            kwargs['fg_color'] = fg_color
        if text_color is not None:
            kwargs['text_color'] = text_color
        if width is not None:
            kwargs['width'] = width
        if hover_color is not None:
            kwargs['hover_color'] = hover_color
        return ctk.CTkButton(parent, text=text, command=command, **kwargs)

    def _entry(self, parent, textvariable=None, width=None, show=None):
        kwargs = {}
        if textvariable is not None:
            kwargs['textvariable'] = textvariable
        if width is not None:
            kwargs['width'] = width
        if show is not None:
            kwargs['show'] = show
        return ctk.CTkEntry(parent, **kwargs)

    def _switch(self, parent, text, variable, command=None):
        return ctk.CTkSwitch(parent, text=text, variable=variable, command=command)
    
    def _setup_window(self):
        """Setup main window properties"""
        self.root.title("MyLocalAPI - Settings")
        self.root.geometry("700x900")
        self.root.minsize(600, 900)
        self._apply_steel_blue_theme()

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
            TRAY_ICON_SIZE = (64, 64)

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
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # Schedule a deferred ensure of taskbar icon on Windows. Some backends
        # require the window to be mapped before window styles and WM_SETICON can be applied.
        try:
            if os.name == 'nt':
                # run shortly after the main loop starts / window is created
                self.root.after(100, lambda: self._ensure_taskbar_icon())
                # Secondary attempt after a longer delay to handle slow window mapping
                try:
                    self.root.after(500, lambda: self._ensure_taskbar_icon())
                except Exception:
                    pass
        except Exception:
            pass
    
    def _apply_steel_blue_theme(self):
        """Apply a steel-blue dark theme to the Tkinter/ttk UI"""
        # Apply a simple CTk appearance and store palette values for custom widgets
        try:
            if CTK_AVAILABLE:
                try:
                    ctk.set_appearance_mode('dark')
                    # Try to nudge CTk's theme; if a dict is accepted it will be used,
                    # otherwise the call will be ignored.
                    try:
                        ctk.set_default_color_theme('dark-blue')
                    except Exception:
                        pass
                except Exception:
                    pass

            # Use the user's requested palette
            app_bg = "#1E1F2B"                 # General app background
            alt_bg = "#282A3A"                 # Alternate lighter background
            input_bg = "#3B3D4B"               # Input background
            # field_bg used by titlebar/controls; choose a slightly lighter input background
            field_bg = input_bg
            success_green = "#BBD760"          # Green success
            danger_red = "#FC6A6A"             # Reds
            fg = "#E6EEF3"                     # Foreground (text)
            muted = "#9AA7B2"                  # Muted text
            accent = success_green
            accent_hover = "#A8C44A"

            self._app_bg = app_bg
            self._field_bg = field_bg
            self._accent = accent
            self._accent_hover = accent_hover
            self._fg = fg
            self._muted = muted

            # Persist some additional color names for code paths that used the old names
            self._alt_bg = alt_bg
            self._input_bg = input_bg
            self._success = success_green
            self._danger = danger_red

            try:
                self.root.configure(bg=app_bg)
            except Exception:
                pass

            # No ttk styling needed when using CTk

            try:
                if CTK_AVAILABLE:
                    try:
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                        theme_path = os.path.join(base_dir, 'ctk_steel_blue_theme.json')
                        if os.path.exists(theme_path):
                            try:
                                ctk.set_default_color_theme(theme_path)
                            except Exception:
                                raise
                        else:
                            raise FileNotFoundError
                    except Exception:
                        try:
                            theme_obj = {
                                'color_primary': accent,
                                'color_secondary': alt_bg,
                                'color_tertiary': input_bg,
                                'color_success': success_green,
                                'color_warning': danger_red,
                                'color_background': app_bg,
                                'color_surface': alt_bg,
                                'text': fg
                            }
                            try:
                                ctk.set_default_color_theme(theme_obj)
                            except Exception:
                                pass
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"Could not apply CTk theme: {e}")

    def _ensure_taskbar_icon(self):
        """Ensure the window shows a proper taskbar icon on Windows.

        This is separated so callers (for example `show_main_window`) can
        reapply styles and WM_SETICON after the window is mapped.
        """
        if os.name != 'nt':
            return

        try:
            # original taskbar/icon handling continues here
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
            # If the widget is disabled, don't change cursor
            try:
                is_disabled = False
                try:
                    is_disabled = (widget.cget('state') == 'disabled')
                except Exception:
                    try:
                        # Some widgets expose 'instate'
                        is_disabled = widget.instate(['disabled'])
                    except Exception:
                        is_disabled = False
                if not is_disabled:
                    try:
                        widget.configure(cursor='hand2')
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

    def _on_button_leave(self, event):
        """Class-level leave handler for Buttons to restore style and cursor."""
        try:
            widget = event.widget
            try:
                widget.configure(cursor='')
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
        # Use CTkFrame as main container
        main_frame = ctk.CTkFrame(self.root)
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
        status_frame = ctk.CTkFrame(parent)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        # Status display
        status_display_frame = self._frame(status_frame)
        status_display_frame.pack(fill=tk.X, padx=10, pady=5)

        self._label(status_display_frame, text="Status:").pack(side=tk.LEFT)
        self.status_label = self._label(status_display_frame, textvariable=self.server_status_var, text_color="red")
        self.status_label.pack(side=tk.LEFT, padx=(5, 0))

        # Control buttons
        button_frame = ctk.CTkFrame(status_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.start_button = ctk.CTkButton(button_frame, text="▶ Start", fg_color=getattr(self, '_success', '#BBD760'), text_color=getattr(self, '_app_bg', '#1E1F2B'), width=100, command=self._start_server)
            
        self.stop_button = ctk.CTkButton(button_frame, text="■ Stop", fg_color=getattr(self, '_danger', '#FC6A6A'), text_color=getattr(self, '_fg', '#E6EEF3'), width=100, command=self._stop_server)
        self.restart_button = ctk.CTkButton(button_frame, text="↻ Restart", text_color=getattr(self, '_fg', '#E6EEF3'), width=100, command=self._restart_server)
        ctk.CTkButton(button_frame, text="Open Browser", command=self._open_browser).pack(side=tk.RIGHT)

        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        self.restart_button.pack(side=tk.LEFT, padx=(0, 5))
    
    def _create_connection_section(self, parent):
        """Create connection settings section"""
        conn_frame = ctk.CTkFrame(parent)
        conn_frame.pack(fill=tk.X, pady=(0, 10))

        # Port setting
        port_frame = self._frame(conn_frame)
        port_frame.pack(fill=tk.X, padx=10, pady=5)

        self._label(port_frame, text="Port:").pack(side=tk.LEFT, padx=(0, 15))
        port_entry = self._entry(port_frame, textvariable=self.port_var, width=80)
        port_entry.pack(side=tk.LEFT, padx=(5, 8))

        # Error label for port (hidden until needed)
        self.port_error_label = ctk.CTkLabel(port_frame, text="", text_color=self._danger, font=("TkDefaultFont", 8))
        # Place error label below the entry; make it span the full width
        self.port_error_label.pack(fill=tk.X, padx=(5, 8))

        # Token setting
        token_frame = self._frame(conn_frame)
        token_frame.pack(fill=tk.X, padx=10, pady=5)

        self._label(token_frame, text="Token:").pack(side=tk.LEFT)
        token_entry = self._entry(token_frame, textvariable=self.token_var, width=300, show="*")
        # Create a Show/Hide button and keep a reference so we can change its label
        show_btn = self._button(token_frame, text="Show", command=self._toggle_token_visibility)
        show_btn.pack(side=tk.RIGHT, padx=(8,0))
        self.token_show_button = show_btn

        token_entry.pack(side=tk.LEFT, padx=(5, 8), fill=tk.X, expand=True)

        # Error label for token (hidden until needed)
        self.token_error_label = ctk.CTkLabel(token_frame, text="", text_color=self._danger, font=("TkDefaultFont", 8))
        self.token_error_label.pack(fill=tk.X, padx=(5, 8))

        # Keep references for validation
        self.port_entry = port_entry
        self.token_entry = token_entry
    
    def _create_tabbed_interface(self, parent):
        """Create tabbed interface"""
        self.notebook = ctk.CTkTabview(parent)
        # Pack notebook to fill available space; remove extra bottom padding so tab content reaches controls
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.notebook.add("Settings")
        self.notebook.add("Endpoints")

        self.settings_frame = self.notebook.tab("Settings")
        self.endpoints_frame = self.notebook.tab("Endpoints")

        self._create_settings_tab()
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
        try:
            widget.bind('<Enter>', _bind_all)
            widget.bind('<Leave>', _unbind_all)
            canvas.bind('<Enter>', _bind_all)
            canvas.bind('<Leave>', _unbind_all)
        except Exception:
            pass
    
    def _create_settings_tab(self):
        """Create settings tab content"""
        # Create a CTkScrollableFrame for the settings tab
        scrollable = ctk.CTkScrollableFrame(self.settings_frame)
        scrollable.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Audio section
        self._create_audio_section(scrollable)

        # Fan section
        self._create_fan_section(scrollable)

        # Streaming section
        self._create_streaming_section(scrollable)

        # Gaming section
        self._create_gaming_section(scrollable)

        # System section
        self._create_system_section(scrollable)
    
    def _create_audio_section(self, parent):
        """Create audio control section"""
        # Use a card container for the whole section to provide a border/background
        audio_frame = ctk.CTkFrame(parent, fg_color=self._shade_color(self._app_bg, 6), corner_radius=6)
        audio_frame.pack(fill=tk.X, padx=10, pady=8)
        # Keep reference so we can show/hide inner settings when toggled
        self.audio_frame = audio_frame

        # Section title (larger and underlined)
        title_font = ("TkDefaultFont", 14, "bold")
        ctk.CTkLabel(audio_frame, text="Audio", font=title_font, text_color=self._fg).pack(anchor=tk.W, padx=10, pady=(8, 2))
        # Underline using a separator line
        sep = ctk.CTkFrame(audio_frame, fg_color=self._shade_color(self._input_bg, -10), height=2)
        sep.pack(fill=tk.X, padx=10, pady=(0, 8))

        # Enable switch
        self.audio_enable_switch = self._switch(audio_frame, text="Enable audio control endpoints", variable=self.audio_enabled_var, command=self._on_audio_enabled_changed)
        self.audio_enable_switch.pack(anchor=tk.W, padx=10, pady=5)

        # Option to use a custom SoundVolumeView install; toggling this shows/hides the SVV path input
        self.use_custom_svv_switch = ctk.CTkSwitch(audio_frame, text="Use Custom SoundVolumeView Install",
                  variable=self.use_custom_svv_var,
                  command=self._on_use_custom_svv_changed)
        self.use_custom_svv_switch.pack(anchor=tk.W, padx=10, pady=5)

        # SVV path (hidden unless use_custom_svv_var is True)
        svv_frame = ctk.CTkFrame(audio_frame)
        svv_frame.pack(fill=tk.X, padx=10, pady=5)
        # Keep references so we can hide/show when audio is toggled
        self.audio_svv_frame = svv_frame

        ctk.CTkLabel(svv_frame, text="SoundVolumeView Path:").pack(anchor=tk.W, padx=(5,0))
        path_frame = ctk.CTkFrame(svv_frame)
        path_frame.pack(fill=tk.X, pady=(2, 0))

        self.svv_entry = self._entry(path_frame, textvariable=self.svv_path_var)
        self.svv_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 5))
        self._button(path_frame, text="Browse", command=self._browse_svv_path).pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        self._label(svv_frame, text="Optional: svcl.exe/SoundVolumeView will be bundled; only fill this to use a local installation.", text_color="gray", font=("TkDefaultFont", 12)).pack(anchor=tk.W, padx=(12,0),pady=(2, 0))

        # Device mappings - put into a card with rounded corners and slightly darker background
        card_bg = self._shade_color(self._input_bg, -6)
        mapping_card = ctk.CTkFrame(audio_frame, fg_color=card_bg, corner_radius=8)
        mapping_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        # Keep reference to mappings card for hide/show
        self.audio_mapping_card = mapping_card

        # Title for the device mapping card (larger title)
        ctk.CTkLabel(mapping_card, text="Device Mappings", font=("TkDefaultFont", 12, "bold"), text_color=self._fg).pack(anchor=tk.W, padx=10, pady=(8, 2))

        # Mappings table (single grid so headers align with inputs/dropdowns)
        self.mappings_table = self._frame(mapping_card)
        self.mappings_table.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        self._label(self.mappings_table, text="Label").grid(row=0, column=0, sticky="w", padx=(10, 10))
        self._label(self.mappings_table, text="Device ID").grid(row=0, column=1, sticky="w", padx=(6, 10))
        # Make these headers compact since switches are small - center headers above the small switches
        self._label(self.mappings_table, text="Stream", font=None).grid(row=0, column=2, sticky="w", padx=(10,0))
        self._label(self.mappings_table, text="Game", font=None).grid(row=0, column=3, sticky="w")
        # Add button: green with plus icon and not too wide (use dark text for contrast)
        self._button(self.mappings_table, text="➕ Add", command=self._add_device_mapping, fg_color=self._success, text_color=self._app_bg, width=65, hover_color=self._accent_hover).grid(row=0, column=4, sticky="e", padx=(0,5), pady=(5,5))

        self.mappings_table.columnconfigure(1, weight=1)

        self.mapping_rows = []
    
    def _create_fan_section(self, parent):
        """Create fan control section"""
        # Fan section card
        fan_frame = ctk.CTkFrame(parent, fg_color=self._shade_color(self._app_bg, 6), corner_radius=6)
        fan_frame.pack(fill=tk.X, padx=10, pady=8)

        # Section title (larger and underlined)
        ctk.CTkLabel(fan_frame, text="Fan Control", font=("TkDefaultFont", 14, "bold"), text_color=self._fg).pack(anchor=tk.W, padx=10, pady=(8, 2))
        sep = ctk.CTkFrame(fan_frame, fg_color=self._shade_color(self._input_bg, -10), height=2)
        sep.pack(fill=tk.X, padx=10, pady=(0, 8))

        # Enable switch
        ctk.CTkSwitch(fan_frame, text="Enable fan control endpoints",
                  variable=self.fan_enabled_var,
                  command=self._on_fan_enabled_changed).pack(anchor=tk.W, padx=10, pady=5)

        # Fan exe path
        exe_frame = ctk.CTkFrame(fan_frame)
        exe_frame.pack(fill=tk.X, padx=10, pady=5)
        # store reference so we can show/hide the entire block
        self.fan_exe_frame = exe_frame

        ctk.CTkLabel(exe_frame, text="FanControl.exe Path:").pack(anchor=tk.W, padx=(5,0))
        exe_path_frame = ctk.CTkFrame(exe_frame)
        exe_path_frame.pack(fill=tk.X, pady=(2, 0), padx=(10,0))

        self.fan_exe_entry = ctk.CTkEntry(exe_path_frame, textvariable=self.fan_exe_var)
        self.fan_exe_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ctk.CTkButton(exe_path_frame, text="Browse", command=self._browse_fan_exe).pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))


        # Fan config path
        config_frame = ctk.CTkFrame(fan_frame)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        # store reference so we can show/hide
        self.fan_config_frame = config_frame

        ctk.CTkLabel(config_frame, text="Fan Config Directory:").pack(anchor=tk.W, padx=(5,0))
        config_path_frame = ctk.CTkFrame(config_frame)
        config_path_frame.pack(fill=tk.X, pady=(2, 0), padx=(10,0))

        # Fan config entry
        self.fan_config_entry = ctk.CTkEntry(config_path_frame, textvariable=self.fan_config_var)
        self.fan_config_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ctk.CTkButton(config_path_frame, text="Browse", command=self._browse_fan_config).pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        # Apply on stream launch
        apply_frame = ctk.CTkFrame(fan_frame)
        apply_frame.pack(fill=tk.X, padx=10, pady=5)
        self.fan_apply_frame = apply_frame

        # Stream apply switch, immediately followed by its selector row
        self.fan_apply_switch = ctk.CTkSwitch(apply_frame, text="Apply fan config on stream launch", variable=self.fan_apply_var, command=self._on_fan_apply_changed)
        self.fan_apply_switch.pack(anchor=tk.W, padx=(5, 0))

        self.fan_stream_config_frame = ctk.CTkFrame(apply_frame)
        ctk.CTkLabel(self.fan_stream_config_frame, text="Selected Config (Stream):").pack(anchor=tk.W, pady=(5, 2), padx=(5,0))
        stream_select_inner = ctk.CTkFrame(self.fan_stream_config_frame)
        stream_select_inner.pack(fill=tk.X, padx=(10,0))

        def _on_fan_config_stream_selected(val):
            try:
                self.settings_manager.set_setting('fan.selected_config_stream', val)
                try:
                    self.settings_manager.set_setting('fan.selected_config', val)
                except Exception:
                    pass
            except Exception:
                pass

        # Create stream combo
        if hasattr(ctk, 'CTkComboBox'):
            try:
                self.fan_stream_combo = ctk.CTkComboBox(stream_select_inner, state="readonly", values=[], command=_on_fan_config_stream_selected)
            except Exception:
                self.fan_stream_combo = ctk.CTkComboBox(stream_select_inner, state="readonly", values=[])
                try:
                    self.fan_stream_combo.configure(command=_on_fan_config_stream_selected)
                except Exception:
                    pass
        else:
            try:
                self.fan_stream_combo = ctk.CTkOptionMenu(stream_select_inner, values=[], command=_on_fan_config_stream_selected)
            except Exception:
                self.fan_stream_combo = ctk.CTkOptionMenu(stream_select_inner, values=[])
                try:
                    self.fan_stream_combo.configure(command=_on_fan_config_stream_selected)
                except Exception:
                    pass

        self.fan_stream_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ctk.CTkButton(stream_select_inner, text="Refresh", command=self._refresh_fan_configs).pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        # Game apply switch, immediately followed by its selector row
        self.fan_apply_game_switch = ctk.CTkSwitch(apply_frame, text="Apply fan config on game launch", variable=self.fan_apply_game_var, command=self._on_fan_apply_game_changed)
        self.fan_apply_game_switch.pack(anchor=tk.W, padx=(5, 0), pady=(6,0))

        self.fan_game_config_frame = ctk.CTkFrame(apply_frame)
        ctk.CTkLabel(self.fan_game_config_frame, text="Selected Config (Game):").pack(anchor=tk.W, pady=(5, 2), padx=(5,0))
        game_select_inner = ctk.CTkFrame(self.fan_game_config_frame)
        game_select_inner.pack(fill=tk.X, padx=(10,0))

        def _on_fan_config_game_selected(val):
            try:
                self.settings_manager.set_setting('fan.selected_config_game', val)
            except Exception:
                pass

        # Create game combo
        if hasattr(ctk, 'CTkComboBox'):
            try:
                self.fan_game_combo = ctk.CTkComboBox(game_select_inner, state="readonly", values=[], command=_on_fan_config_game_selected)
            except Exception:
                self.fan_game_combo = ctk.CTkComboBox(game_select_inner, state="readonly", values=[])
                try:
                    self.fan_game_combo.configure(command=_on_fan_config_game_selected)
                except Exception:
                    pass
        else:
            try:
                self.fan_game_combo = ctk.CTkOptionMenu(game_select_inner, values=[], command=_on_fan_config_game_selected)
            except Exception:
                self.fan_game_combo = ctk.CTkOptionMenu(game_select_inner, values=[])
                try:
                    self.fan_game_combo.configure(command=_on_fan_config_game_selected)
                except Exception:
                    pass

        self.fan_game_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ctk.CTkButton(game_select_inner, text="Refresh", command=self._refresh_fan_configs).pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))
    
    def _create_streaming_section(self, parent):
        """Create streaming section"""
        # Streaming section card
        # Streaming section
        streaming_frame = ctk.CTkFrame(parent, fg_color=self._shade_color(self._app_bg, 6), corner_radius=6)
        streaming_frame.pack(fill=tk.X, padx=10, pady=8)
        ctk.CTkLabel(streaming_frame, text="Streaming", font=("TkDefaultFont", 14, "bold"), text_color=self._fg).pack(anchor=tk.W, padx=10, pady=(8, 2))
        sep = ctk.CTkFrame(streaming_frame, fg_color=self._shade_color(self._input_bg, -10), height=2)
        sep.pack(fill=tk.X, padx=10, pady=(0, 8))

        # Enable streaming endpoint (switch)
        ctk.CTkSwitch(streaming_frame, text="Launch streaming service by endpoint", variable=self.streaming_enabled_var, command=self._on_streaming_enabled_changed).pack(anchor=tk.W, padx=10, pady=5)

        # Apple TV moniker
        appletv_frame = ctk.CTkFrame(streaming_frame)
        appletv_frame.pack(fill=tk.X, padx=10, pady=5)
        # Keep a reference so we can show/hide the entire moniker block
        self.appletv_frame = appletv_frame
        ctk.CTkLabel(appletv_frame, text="Apple TV App Moniker:").pack(anchor=tk.W, padx=(5,0))
        moniker_frame = ctk.CTkFrame(appletv_frame)
        moniker_frame.pack(fill=tk.X, pady=(2, 0), padx=(10,0))
        self.appletv_entry = ctk.CTkEntry(moniker_frame, textvariable=self.apple_tv_moniker_var)
        self.appletv_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ctk.CTkButton(moniker_frame, text="Auto-detect", command=self._auto_detect_appletv).pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))
    
    def _create_gaming_section(self, parent):
        """Create gaming section"""
        # Gaming section card
        gaming_frame = ctk.CTkFrame(parent, fg_color=self._shade_color(self._app_bg, 6), corner_radius=6)
        gaming_frame.pack(fill=tk.X, padx=10, pady=8)
        # Keep reference so we can show/hide inner settings when toggled
        self.gaming_frame = gaming_frame

        # Section title (larger and underlined)
        title_font = ("TkDefaultFont", 14, "bold")
        ctk.CTkLabel(gaming_frame, text="Gaming", font=title_font, text_color=self._fg).pack(anchor=tk.W, padx=10, pady=(8, 2))
        # Underline using a separator line
        sep = ctk.CTkFrame(gaming_frame, fg_color=self._shade_color(self._input_bg, -10), height=2)
        sep.pack(fill=tk.X, padx=10, pady=(0, 8))

        # Enable switch
        self.gaming_enable_switch = self._switch(gaming_frame, text="Enable gaming launch endpoints", variable=self.gaming_enabled_var, command=self._on_gaming_enabled_changed)
        self.gaming_enable_switch.pack(anchor=tk.W, padx=10, pady=5)

        # Gaming mappings - put into a card with rounded corners and slightly darker background
        card_bg = self._shade_color(self._input_bg, -6)
        gaming_mapping_card = ctk.CTkFrame(gaming_frame, fg_color=card_bg, corner_radius=8)
        gaming_mapping_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        # Keep reference to mappings card for hide/show
        self.gaming_mapping_card = gaming_mapping_card

        # Title for the game mapping card (larger title)
        ctk.CTkLabel(gaming_mapping_card, text="Game Mappings", font=("TkDefaultFont", 12, "bold"), text_color=self._fg).pack(anchor=tk.W, padx=10, pady=(8, 2))

        # Gaming mappings table (single grid so headers align with inputs/dropdowns)
        self.gaming_mappings_table = self._frame(gaming_mapping_card)
        self.gaming_mappings_table.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        self._label(self.gaming_mappings_table, text="Label").grid(row=0, column=0, sticky="w", padx=(10, 10))
        self._label(self.gaming_mappings_table, text="Steam App ID").grid(row=0, column=1, sticky="w", padx=(6, 10))
        self._label(self.gaming_mappings_table, text="Path to Exe").grid(row=0, column=2, sticky="w", padx=(6, 10))
        # Add button: green with plus icon and not too wide (use dark text for contrast)
        self._button(self.gaming_mappings_table, text="➕ Add", command=self._add_gaming_mapping, fg_color=self._success, text_color=self._app_bg, width=65, hover_color=self._accent_hover).grid(row=0, column=3, sticky="e", padx=(0,5), pady=(5,5))

        self.gaming_mappings_table.columnconfigure(1, weight=1)
        self.gaming_mappings_table.columnconfigure(2, weight=1)

        self.gaming_mapping_rows = []
    
    def _create_system_section(self, parent):
        """Create system section"""
        # System section card
        system_frame = ctk.CTkFrame(parent, fg_color=self._shade_color(self._app_bg, 6), corner_radius=6)
        system_frame.pack(fill=tk.X, padx=10, pady=8)
        ctk.CTkLabel(system_frame, text="System", font=("TkDefaultFont", 14, "bold"), text_color=self._fg).pack(anchor=tk.W, padx=10, pady=(8, 2))
        sep = ctk.CTkFrame(system_frame, fg_color=self._shade_color(self._input_bg, -10), height=2)
        sep.pack(fill=tk.X, padx=10, pady=(0, 8))

        # Autostart
        ctk.CTkSwitch(system_frame, text="Launch on system startup",
                      variable=self.autostart_var,
                      command=self._on_autostart_changed).pack(anchor=tk.W, padx=10, pady=5)

        # Settings management
        settings_frame = ctk.CTkFrame(system_frame)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        ctk.CTkButton(settings_frame, text="Reset to Defaults", command=self._reset_settings).pack(side=tk.LEFT, padx=(0, 5))
        ctk.CTkButton(settings_frame, text="Export Settings", command=self._export_settings).pack(side=tk.LEFT, padx=(0, 5))
        ctk.CTkButton(settings_frame, text="Import Settings", command=self._import_settings).pack(side=tk.LEFT)
    
    def _create_endpoints_tab(self):
        self.endpoints_result_text = ctk.CTkTextbox(self.endpoints_frame, width=1, height=120)
        endpoints_container = ctk.CTkScrollableFrame(self.endpoints_frame)
        endpoints_container.pack(fill=tk.BOTH, expand=True)

        # Endpoint definitions - load from endpoints.json only (no fallback)
        endpoints = []
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            endpoints_path = os.path.join(base_dir, "endpoints.json")
            with open(endpoints_path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
                if isinstance(loaded, list):
                    endpoints = loaded
                else:
                    logger.debug("endpoints.json did not contain a list; using empty endpoints")
        except Exception as e:
            logger.debug(f"Could not load endpoints.json: {e}")

        self.endpoint_widgets = []

        for group_info in endpoints:
            # Create a bordered card container for the group
            group_frame = ctk.CTkFrame(endpoints_container, fg_color=self._shade_color(self._app_bg, 6), corner_radius=6, height=200)
            group_frame.pack(fill=tk.X, padx=5, pady=(14, 10))

            # Group title with status indicator on the left: larger, bold and underlined
            title_font = ("TkDefaultFont", 12, "bold")
            title_row = ctk.CTkFrame(group_frame)
            title_row.pack(fill=tk.X, padx=10, pady=(6, 2))

            # Status dot to the left of the title
            status_indicator = ctk.CTkLabel(title_row, text="●", font=("TkDefaultFont", 14, "bold"), text_color=getattr(self, '_success', '#BBD760'))
            # Add extra left padding so the indicator isn't flush to the card edge
            status_indicator.pack(side=tk.LEFT, padx=(10, 8))

            ctk.CTkLabel(title_row, text=group_info.get("group", ""), font=title_font, text_color=self._fg).pack(side=tk.LEFT, anchor='w')

            sep = ctk.CTkFrame(group_frame, fg_color=self._shade_color(self._input_bg, -10), height=2)
            sep.pack(fill=tk.X, padx=10, pady=(0, 8))

            # Store for updating (indicator + endpoint frames)
            self.endpoint_widgets.append({
                "group": group_info["group"],
                "enabled_setting": group_info["enabled_setting"],
                "indicator": status_indicator,
                "endpoints": []
            })
            
            # Endpoints
            for endpoint in group_info["endpoints"]:
                # Endpoint row card for visual separation
                ep_frame = ctk.CTkFrame(group_frame, fg_color=self._shade_color(self._app_bg, 4), corner_radius=8)
                # Increase left padding so endpoint cards align with group title indicator spacing
                ep_frame.pack(fill=tk.X, padx=(24, 20), pady=(8, 10))
                # Remember this endpoint frame so we can hide/show it when the group is toggled
                self.endpoint_widgets[-1]["endpoints"].append(ep_frame)

                # Create a left content area and a right actions column so buttons are stacked on the right
                content_container = ctk.CTkFrame(ep_frame)
                content_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

                actions_container = ctk.CTkFrame(ep_frame)
                actions_container.pack(side=tk.RIGHT, padx=(6, 10), anchor=tk.N)

                # Endpoint info (larger text) goes into the content container
                info_frame = ctk.CTkFrame(content_container)
                info_frame.pack(fill=tk.X, padx=10, pady=4)

                # Title row with enabled indicator on the left
                # Determine enabled state for this group (used for per-endpoint indicator)
                if group_info.get("enabled_setting") is None:
                    endpoint_enabled = True
                else:
                    endpoint_enabled = self.settings_manager.get_setting(group_info.get("enabled_setting"), True)
                dot_color = getattr(self, '_success', '#BBD760') if endpoint_enabled else getattr(self, '_danger', '#FC6A6A')

                title_row = ctk.CTkFrame(info_frame)
                title_row.pack(anchor=tk.W, fill=tk.X)

                ind = ctk.CTkLabel(title_row, text="●", font=("TkDefaultFont", 14, "bold"), text_color=dot_color)
                # Add more left spacing for per-endpoint indicator
                ind.pack(side=tk.LEFT, padx=(12, 8))

                ctk.CTkLabel(title_row, text=f"{endpoint['method']} {endpoint['path']}", font=("TkDefaultFont", 12, "bold"), text_color=self._fg).pack(side=tk.LEFT)
                ctk.CTkLabel(info_frame, text=endpoint["description"], text_color="gray", font=("TkDefaultFont", 12)).pack(anchor=tk.W, padx=(5, 0))
                if endpoint["params"]:
                    ctk.CTkLabel(info_frame, text=f"Parameters: {endpoint['params']}", font=("TkDefaultFont", 11), text_color=self._muted).pack(anchor=tk.W, padx=(5, 0))

                # Create stacked action buttons in the right actions column
                test_button = ctk.CTkButton(actions_container, text="Test", width=110, command=lambda ep=endpoint: self._test_endpoint(ep), fg_color=self._accent, text_color=self._app_bg)
                test_button.pack(pady=(4, 6), padx=(5,5))
                curl_button = ctk.CTkButton(actions_container, text="Copy cURL", width=110, command=lambda ep=endpoint: self._copy_curl(ep))
                curl_button.pack(pady=(0, 4), padx=(5,5))

                # All endpoints share the same result textbox (created above)
                endpoint["test_button"] = test_button
                endpoint["result_text"] = self.endpoints_result_text

        self.endpoints_result_text.pack(fill=tk.X, padx=(10, 20), pady=(2, 0))
        
        
    # If we used a CTkScrollableFrame, it's already packed by construction; nothing to do here
    
    def _create_bottom_controls(self, parent):
        """Create bottom control buttons"""
        # Prefer CustomTkinter frames/buttons/labels when available;
        bottom_frame = ctk.CTkFrame(parent)
        bottom_frame.pack(fill=tk.X, pady=(8, 0))

        # Status message (right side)
        self.status_message_var = tk.StringVar()
        self.status_message_label = ctk.CTkLabel(bottom_frame, textvariable=self.status_message_var, text_color="gray")
        self.status_message_label.pack(side=tk.BOTTOM)
    
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
        # Custom SVV install setting
        self.use_custom_svv_var.set(self.settings_manager.get_setting('audio.use_custom_svv', False))
        
        # Fan settings
        self.fan_enabled_var.set(self.settings_manager.get_setting('fan.enabled', False))
        self.fan_exe_var.set(self.settings_manager.get_setting('fan.fan_exe_path', ''))
        self.fan_config_var.set(self.settings_manager.get_setting('fan.fan_config_path', ''))
        self.fan_apply_var.set(self.settings_manager.get_setting('fan.apply_on_stream_launch', False))
        # New: load apply on game launch setting
        try:
            self.fan_apply_game_var.set(self.settings_manager.get_setting('fan.apply_on_game_launch', False))
        except Exception:
            self.fan_apply_game_var.set(False)
        # Refresh fan configs into dropdowns so selected_config values are visible
        try:
            self._refresh_fan_configs()
        except Exception:
            pass
        
        # Streaming settings
        self.streaming_enabled_var.set(self.settings_manager.get_setting('streaming.launch_streaming_by_endpoint', True))
        self.apple_tv_moniker_var.set(self.settings_manager.get_setting('streaming.appleTVMoniker', ''))
        
        # Gaming settings
        self.gaming_enabled_var.set(self.settings_manager.get_setting('gaming.enabled', True))
        
        # System settings
        self.autostart_var.set(AutostartManager.is_enabled())
        
        # Load device mappings
        self._load_device_mappings()
        
        # Load gaming mappings
        self._load_gaming_mappings()
        
        # Update UI state
        self._update_audio_ui_state()
        self._update_fan_ui_state()
        self._update_endpoints_status()
        self._update_streaming_ui_state()
        self._update_gaming_ui_state()
        
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

        # Populate rows
        for mapping in mappings:
            label = mapping.get('label', '')
            device_id = mapping.get('device_id', '')
            use_for_streaming = mapping.get('use_for_streaming', False)
            use_for_game = mapping.get('is_game', False)
            self._add_device_mapping_row(label=label, device_id=device_id, use_for_streaming=use_for_streaming, use_for_game=use_for_game)

        # Add one empty row if no mappings exist
        if not mappings:
            self._add_device_mapping_row()
    
    def _load_gaming_mappings(self):
        """Load gaming mappings into UI"""
        # Clear existing rows
        for row_data in self.gaming_mapping_rows:
            for widget in row_data["widgets"]:
                widget.destroy()
        self.gaming_mapping_rows.clear()
        
        # Load mappings from settings
        mappings = self.settings_manager.get_gaming_mappings()

        # Populate rows
        for mapping in mappings:
            label = mapping.get('label', '')
            steam_appid = mapping.get('steam_appid', '')
            exe_path = mapping.get('exe_path', '')
            self._add_gaming_mapping_row(label=label, steam_appid=steam_appid, exe_path=exe_path)

        # Add one empty row if no mappings exist
        if not mappings:
            self._add_gaming_mapping_row()
    
    def _add_device_mapping_row(self, label="", device_id="", use_for_streaming=False, use_for_game=False):
        """Add a device mapping row (grid-aligned to the header)."""
        row_parent = getattr(self, 'mappings_table', None) or self.mappings_table
        row_index = len(self.mapping_rows) + 1  # header is row 0

        label_var = tk.StringVar(value=label)
        device_id_var = tk.StringVar(value=device_id)
        streaming_var = tk.BooleanVar(value=use_for_streaming)
        game_var = tk.BooleanVar(value=use_for_game)

        # fetch device options (same logic as before)
        def _fetch_device_options():
            options = []
            try:
                ac = None
                if getattr(self.app, 'flask_server', None) and getattr(self.app.flask_server, 'audio_controller', None):
                    ac = self.app.flask_server.audio_controller
                else:
                    try:
                        from audio_control import AudioController
                        svv = self.settings_manager.get_setting('audio.svv_path', '')
                        ac = AudioController(svv if svv else None)
                    except Exception:
                        ac = None

                if ac:
                    devs = ac.get_playback_devices()
                    if isinstance(devs, dict) and devs.get('ok') and 'devices' in devs:
                        for d in devs['devices']:
                            did = d.get('device_id', '')
                            name = d.get('device_name') or d.get('name') or ''
                            if did:
                                display = f"{name} — {did}" if name else did
                                options.append((display, did))
            except Exception:
                pass

            if not options:
                try:
                    for m in self.settings_manager.get_audio_mappings():
                        did = m.get('device_id', '').strip()
                        label = m.get('label', '').strip()
                        if did:
                            display = f"{label} — {did}" if label else did
                            options.append((display, did))
                except Exception:
                    pass

            return options

        options = _fetch_device_options()
        display_to_id = {d: i for d, i in options}
        display_values = [d for d, _ in options]

        label_entry = ctk.CTkEntry(row_parent, textvariable=label_var, width=120)
        label_entry.grid(row=row_index, column=0, sticky="ew", padx=(5, 5), pady=2)

        if display_values:
            if hasattr(ctk, 'CTkComboBox'):
                device_entry = ctk.CTkComboBox(row_parent, values=display_values)
                if device_id:
                    for disp, did in options:
                        if did == device_id:
                            try:
                                device_entry.set(disp)
                            except Exception:
                                pass
                            break
                device_entry.grid(row=row_index, column=1, sticky="ew", padx=(5, 5), pady=2)

                def _on_ctk_select(val):
                    try:
                        device_id_var.set(display_to_id.get(val, val))
                        self._save_device_mappings()
                    except Exception:
                        pass

                try:
                    device_entry.configure(command=_on_ctk_select)
                except Exception:
                    pass
            else:
                device_entry = ctk.CTkOptionMenu(row_parent, values=display_values, command=lambda v: device_id_var.set(display_to_id.get(v, v)))
                if device_id:
                    for disp, did in options:
                        if did == device_id:
                            try:
                                device_entry.set(disp)
                            except Exception:
                                pass
                            break
                device_entry.grid(row=row_index, column=1, sticky="ew", padx=(5, 5), pady=2)
        else:
            device_entry = ctk.CTkEntry(row_parent, textvariable=device_id_var)
            device_entry.grid(row=row_index, column=1, sticky="ew", padx=(5, 5), pady=2)

        streaming_cb = ctk.CTkSwitch(row_parent, text="", variable=streaming_var, command=lambda: self._on_streaming_checkbox_changed(streaming_var))
        # Center the streaming toggle in its column (no extra left-offset)
        streaming_cb.grid(row=row_index, column=2, padx=0, pady=2)

        # Game switch - ensure single selection across rows
        game_cb = ctk.CTkSwitch(row_parent, text="", variable=game_var, command=lambda gv=game_var: self._on_game_checkbox_changed(gv))
        game_cb.grid(row=row_index, column=3, padx=0, pady=2)

        delete_btn = ctk.CTkButton(row_parent, text="🗑 Delete", width=60, fg_color=getattr(self, '_danger', '#FC6A6A'), text_color=getattr(self, '_app_bg', '#1E1F2B'), hover_color=self._shade_color(getattr(self, '_danger', '#FC6A6A'), -10), command=lambda: None)
        delete_btn.grid(row=row_index, column=4, padx=(5, 5), pady=3)

        # Ensure the middle column stretches
        try:
            self.mappings_table.columnconfigure(1, weight=1)
            self.mappings_table.columnconfigure(2, minsize=8)
            self.mappings_table.columnconfigure(3, minsize=8)
        except Exception:
            pass

        row_data = {
            "row": row_index,
            "widgets": [label_entry, device_entry, streaming_cb, game_cb, delete_btn],
            "vars": {"label": label_var, "device_id": device_id_var, "streaming": streaming_var, "is_game": game_var}
        }

        # Setup change handlers
        label_var.trace_add("write", lambda *args: self._save_device_mappings())
        device_id_var.trace_add("write", lambda *args: self._save_device_mappings())
        streaming_var.trace_add("write", lambda *args: self._save_device_mappings())
        game_var.trace_add("write", lambda *args: self._save_device_mappings())

        # Now that row_data exists, set the delete button's command to reference it
        try:
            delete_btn.configure(command=lambda rd=row_data: self._delete_device_mapping_row(rd))
        except Exception:
            pass

        self.mapping_rows.append(row_data)

        return row_data
    
    def _add_gaming_mapping_row(self, label="", steam_appid="", exe_path=""):
        """Add a gaming mapping row (grid-aligned to the header)."""
        row_parent = getattr(self, 'gaming_mappings_table', None) or self.gaming_mappings_table
        row_index = len(self.gaming_mapping_rows) + 1  # header is row 0

        label_var = tk.StringVar(value=label)
        steam_appid_var = tk.StringVar(value=steam_appid)
        exe_path_var = tk.StringVar(value=exe_path)

        label_entry = ctk.CTkEntry(row_parent, textvariable=label_var, width=120)
        label_entry.grid(row=row_index, column=0, sticky="ew", padx=(5, 5), pady=2)

        steam_appid_entry = ctk.CTkEntry(row_parent, textvariable=steam_appid_var, width=120)
        steam_appid_entry.grid(row=row_index, column=1, sticky="ew", padx=(5, 5), pady=2)

        exe_path_entry = ctk.CTkEntry(row_parent, textvariable=exe_path_var, width=200)
        exe_path_entry.grid(row=row_index, column=2, sticky="ew", padx=(5, 5), pady=2)

        delete_btn = ctk.CTkButton(row_parent, text="🗑 Delete", width=60, fg_color=getattr(self, '_danger', '#FC6A6A'), text_color=getattr(self, '_app_bg', '#1E1F2B'), hover_color=self._shade_color(getattr(self, '_danger', '#FC6A6A'), -10), command=lambda: None)
        delete_btn.grid(row=row_index, column=3, padx=(5, 5), pady=3)

        # Create error labels for Steam App ID and exe path
        steam_appid_error = ctk.CTkLabel(row_parent, text="", text_color=self._danger, font=("TkDefaultFont", 8))
        exe_path_error = ctk.CTkLabel(row_parent, text="", text_color=self._danger, font=("TkDefaultFont", 8))

        # Position error labels beneath their respective fields (use next row)
        error_row = row_index + 1
        steam_appid_error.grid(row=error_row, column=1, sticky="ew", padx=(5, 5))
        exe_path_error.grid(row=error_row, column=2, sticky="ew", padx=(5, 5))

        # Ensure the columns stretch appropriately
        try:
            self.gaming_mappings_table.columnconfigure(1, weight=1)
            self.gaming_mappings_table.columnconfigure(2, weight=1)
        except Exception:
            pass

        row_data = {
            "row": row_index,
            "widgets": [label_entry, steam_appid_entry, exe_path_entry, delete_btn, steam_appid_error, exe_path_error],
            "vars": {"label": label_var, "steam_appid": steam_appid_var, "exe_path": exe_path_var},
            "error_labels": {"steam_appid": steam_appid_error, "exe_path": exe_path_error}
        }

        # Setup change handlers
        label_var.trace_add("write", lambda *args: self._save_gaming_mappings())
        steam_appid_var.trace_add("write", lambda *args, rd=row_data: self._validate_gaming_row(rd))
        exe_path_var.trace_add("write", lambda *args, rd=row_data: self._validate_gaming_row(rd))

        # Now that row_data exists, set the delete button's command to reference it
        try:
            delete_btn.configure(command=lambda rd=row_data: self._delete_gaming_mapping_row(rd))
        except Exception:
            pass

        self.gaming_mapping_rows.append(row_data)

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
            is_game = row_data["vars"]["is_game"].get()
            
            if label or device_id:  # Only save non-empty rows
                mappings.append({
                    "label": label,
                    "device_id": device_id,
                    "use_for_streaming": streaming
                    ,"is_game": is_game
                })
        
        self.settings_manager.set_audio_mappings(mappings)

    def _on_game_checkbox_changed(self, changed_var):
        """Ensure only one mapping is marked as Game at a time."""
        if changed_var.get():
            for row_data in self.mapping_rows:
                gv = row_data["vars"].get("is_game")
                if gv is not None and gv != changed_var:
                    gv.set(False)
        self._save_device_mappings()
    
    def _validate_gaming_row(self, row_data):
        """Validate a gaming mapping row - show error if both steam_appid and exe_path are filled"""
        steam_appid = row_data["vars"]["steam_appid"].get().strip()
        exe_path = row_data["vars"]["exe_path"].get().strip()
        
        steam_error_label = row_data["error_labels"]["steam_appid"]
        exe_error_label = row_data["error_labels"]["exe_path"]
        
        # Clear previous errors
        steam_error_label.configure(text="")
        exe_error_label.configure(text="")
        
        if steam_appid and exe_path:
            # Both filled - show error
            error_msg = "Only fill Steam App ID OR Path to Exe, not both"
            steam_error_label.configure(text=error_msg)
            exe_error_label.configure(text=error_msg)
        
        # Always save mappings (validation is done there too)
        self._save_gaming_mappings()
    
    def _save_gaming_mappings(self):
        """Save gaming mappings to settings"""
        mappings = []
        for row_data in self.gaming_mapping_rows:
            label = row_data["vars"]["label"].get().strip()
            steam_appid = row_data["vars"]["steam_appid"].get().strip()
            exe_path = row_data["vars"]["exe_path"].get().strip()
            
            if label or steam_appid or exe_path:  # Only save non-empty rows
                mappings.append({
                    "label": label,
                    "steam_appid": steam_appid,
                    "exe_path": exe_path
                })
        
        self.settings_manager.set_gaming_mappings(mappings)
    
    def _delete_gaming_mapping_row(self, row_data):
        """Delete a gaming mapping row"""
        if row_data in self.gaming_mapping_rows:
            self.gaming_mapping_rows.remove(row_data)
            for widget in row_data["widgets"]:
                widget.destroy()
            self._save_gaming_mappings()
    
    def _add_gaming_mapping(self):
        """Add new gaming mapping row"""
        self._add_gaming_mapping_row()
    
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
        # Clear any prior validation when user types
        try:
            self._clear_field_error(self.port_entry, self.port_error_label)
        except Exception:
            pass
    
    def _on_token_changed(self, *args):
        """Handle token change"""
        self.settings_manager.set_setting('token', self.token_var.get())
        # Clear any prior validation when user types
        try:
            self._clear_field_error(self.token_entry, self.token_error_label)
        except Exception:
            pass
    
    def _on_audio_enabled_changed(self):
        """Handle audio enabled change"""
        self.settings_manager.set_setting('audio.enabled', self.audio_enabled_var.get())
        self._update_audio_ui_state()
        self._update_endpoints_status()
    
    def _on_svv_path_changed(self, *args):
        """Handle SVV path change"""
        self.settings_manager.set_setting('audio.svv_path', self.svv_path_var.get())

    def _on_use_custom_svv_changed(self):
        """Handle toggling whether to use a custom SoundVolumeView install"""
        enabled = self.use_custom_svv_var.get()
        self.settings_manager.set_setting('audio.use_custom_svv', enabled)
        # Show or hide the SVV path frame based on both audio enabled and custom flag
        self._update_audio_ui_state()
    
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
        try:
            self.settings_manager.set_setting('fan.apply_on_stream_launch', enabled)
        except Exception:
            pass

        # Show/hide only the stream selector row
        try:
            if enabled:
                try:
                    self.fan_stream_config_frame.pack(fill=tk.X, pady=(5, 0))
                except Exception:
                    pass
                try:
                    self._refresh_fan_configs()
                except Exception:
                    pass
            else:
                try:
                    self.fan_stream_config_frame.pack_forget()
                except Exception:
                    pass
        except Exception:
            pass

    def _on_fan_apply_game_changed(self):
        """Handle fan apply on game launch change"""
        enabled = self.fan_apply_game_var.get()
        try:
            self.settings_manager.set_setting('fan.apply_on_game_launch', enabled)
        except Exception:
            pass

        # Show/hide only the game selector row
        try:
            if enabled:
                try:
                    self.fan_game_config_frame.pack(fill=tk.X, pady=(5, 0))
                except Exception:
                    pass
                try:
                    self._refresh_fan_configs()
                except Exception:
                    pass
            else:
                try:
                    self.fan_game_config_frame.pack_forget()
                except Exception:
                    pass
        except Exception:
            pass
    
    def _on_streaming_enabled_changed(self):
        """Handle streaming enabled change"""
        self.settings_manager.set_setting('streaming.launch_streaming_by_endpoint', 
                                         self.streaming_enabled_var.get())
        self._update_endpoints_status()
        self._update_streaming_ui_state()

    def _on_gaming_enabled_changed(self):
        """Handle gaming enabled change"""
        self.settings_manager.set_setting('gaming.enabled', self.gaming_enabled_var.get())
        self._update_gaming_ui_state()
        self._update_endpoints_status()

    def _update_streaming_ui_state(self):
        """Show or hide the Apple TV moniker field depending on streaming endpoint toggle"""
        try:
            enabled = self.streaming_enabled_var.get()
            if getattr(self, 'appletv_frame', None):
                if enabled:
                    try:
                        self.appletv_frame.pack(fill=tk.X, padx=10, pady=5)
                    except Exception:
                        pass
                else:
                    try:
                        self.appletv_frame.pack_forget()
                    except Exception:
                        pass
        except Exception:
            pass
    
    def _update_gaming_ui_state(self):
        """Update gaming UI state based on enabled setting"""
        enabled = self.gaming_enabled_var.get()
        
        # Show or hide the gaming mappings card depending on gaming enabled state
        try:
            gaming_mapping_card = getattr(self, 'gaming_mapping_card', None)
            if gaming_mapping_card:
                if enabled:
                    try:
                        # Use the original pack options used during creation
                        gaming_mapping_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                    except Exception:
                        pass
                else:
                    try:
                        gaming_mapping_card.pack_forget()
                    except Exception:
                        pass
        except Exception:
            pass

        # Enable/disable gaming-related widgets
        widgets = []
        for row in getattr(self, 'gaming_mapping_rows', []):
            widgets.extend(row["widgets"])
        
        state = "normal" if enabled else "disabled"
        for widget in widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass  # Some widgets don't support state
    
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
        
        # Show or hide the SVV path frame depending on whether audio is enabled and the custom flag
        try:
            if enabled and getattr(self, 'use_custom_svv_var', None) and self.use_custom_svv_var.get():
                try:
                    mapping_card = getattr(self, 'audio_mapping_card', None)
                    if mapping_card:
                        # Insert the SVV frame before the mappings card so it stays in the original position
                        self.audio_svv_frame.pack(fill=tk.X, padx=10, pady=5, before=mapping_card)
                    else:
                        self.audio_svv_frame.pack(fill=tk.X, padx=10, pady=5)
                except Exception:
                    pass
            else:
                try:
                    self.audio_svv_frame.pack_forget()
                except Exception:
                    pass
        except Exception:
            pass

        # Show or hide the device mappings card depending on audio enabled state
        try:
            mapping_card = getattr(self, 'audio_mapping_card', None)
            if mapping_card:
                if enabled:
                    try:
                        # Use the original pack options used during creation
                        mapping_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                    except Exception:
                        pass
                else:
                    try:
                        mapping_card.pack_forget()
                    except Exception:
                        pass
        except Exception:
            pass

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

        # Show/hide the fan blocks depending on enabled
        try:
            if getattr(self, 'fan_exe_frame', None):
                if enabled:
                    try:
                        self.fan_exe_frame.pack(fill=tk.X, padx=10, pady=5)
                    except Exception:
                        pass
                else:
                    try:
                        self.fan_exe_frame.pack_forget()
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            if getattr(self, 'fan_config_frame', None):
                if enabled:
                    try:
                        self.fan_config_frame.pack(fill=tk.X, padx=10, pady=5)
                    except Exception:
                        pass
                else:
                    try:
                        self.fan_config_frame.pack_forget()
                    except Exception:
                        pass
        except Exception:
            pass

        # Handle fan apply UI and enable/disable the apply switch based on fan enabled state
        try:
            if enabled:
                # Restore apply frame visibility if apply is set
                if self.fan_apply_var.get() or self.fan_apply_game_var.get():
                    try:
                        self.fan_stream_config_frame.pack(fill=tk.X, pady=(5, 0))
                    except Exception:
                        pass
                    try:
                        self.fan_game_config_frame.pack(fill=tk.X, pady=(5, 0))
                    except Exception:
                        pass
                # Ensure the apply switch is enabled
                try:
                    self.fan_apply_switch.configure(state="normal")
                except Exception:
                    pass
                try:
                    # Also enable the game-apply switch so both behave the same
                    self.fan_apply_game_switch.configure(state="normal")
                except Exception:
                    pass
            else:
                # When fan endpoints are disabled, force apply off and disable the switch
                try:
                    self.fan_apply_var.set(False)
                    self.fan_apply_game_var.set(False)
                    self.settings_manager.set_setting('fan.apply_on_stream_launch', False)
                    self.settings_manager.set_setting('fan.apply_on_game_launch', False)
                except Exception:
                    pass
                try:
                    self.fan_stream_config_frame.pack_forget()
                except Exception:
                    pass
                try:
                    self.fan_game_config_frame.pack_forget()
                except Exception:
                    pass
                try:
                    # Disable both apply switches when fan endpoints are disabled
                    self.fan_apply_switch.configure(state="disabled")
                except Exception:
                    pass
                try:
                    self.fan_apply_game_switch.configure(state="disabled")
                except Exception:
                    pass
        except Exception:
            pass
    
    def _update_endpoints_status(self):
        """Update endpoints status indicators"""
        for widget_info in self.endpoint_widgets:
            enabled_setting = widget_info["enabled_setting"]
            
            if enabled_setting is None:
                # Always enabled
                enabled = True
            else:
                enabled = self.settings_manager.get_setting(enabled_setting, True)
            
            # Update indicator (large dot) and label text
            color = getattr(self, '_success', '#BBD760') if enabled else getattr(self, '_danger', '#FC6A6A')
            text = "Enabled" if enabled else "Disabled"

            ind = widget_info.get("indicator")
            if not ind:
                continue

            # Update indicator color (CTkLabel uses text_color)
            try:
                ind.configure(text_color=color)
            except Exception:
                # Try older attribute names if needed
                try:
                    ind.configure(fg=color, bg=getattr(self, '_app_bg', '#1E1F2B'))
                except Exception:
                    try:
                        ind.configure(foreground=color)
                    except Exception:
                        pass

            # Show or hide the group's endpoint frames based on enabled state
            try:
                frames = widget_info.get('endpoints', [])
                if frames:
                    if enabled:
                        for f in frames:
                            try:
                                # Re-pack with original layout options
                                f.pack(fill=tk.X, padx=(24, 20), pady=(8, 10))
                            except Exception:
                                pass
                    else:
                        for f in frames:
                            try:
                                f.pack_forget()
                            except Exception:
                                pass
            except Exception:
                pass
    
    # Action handlers
    def _start_server(self):
        """Start the server"""
        # Validate required fields (port and token)
        valid = True
        port_val = self.port_var.get().strip()
        token_val = self.token_var.get().strip()

        if not port_val:
            self._set_field_error(self.port_entry, self.port_error_label, "Port is required")
            valid = False

        if not token_val:
            self._set_field_error(self.token_entry, self.token_error_label, "Token is required")
            valid = False

        if not valid:
            # Focus first invalid field
            try:
                if not port_val:
                    self.port_entry.focus_set()
                else:
                    self.token_entry.focus_set()
            except Exception:
                pass
            return

        success = self.app.start_server()
        if success:
            self.status_message_var.set("Server started successfully")
        else:
            self.status_message_var.set("Failed to start server")
        
        # Clear message after 3 seconds
        self.root.after(3000, lambda: self.status_message_var.set(""))

    # Validation helpers
    def _set_field_error(self, widget, error_label, message: str):
        """Visually mark a widget as invalid and show an error message underneath.

        Works for CTk widgets. For CTkEntry we set border_color
        when available;
        """
        error_label.configure(text=message)
        error_label.configure(text=message)
        widget.configure(border_color=getattr(self, '_danger', '#FC6A6A'))

    def _clear_field_error(self, widget, error_label):
        """Clear validation visuals and hide error message."""
        try:
            try:
                error_label.configure(text="")
            except Exception:
                try:
                    error_label.configure(text="")
                except Exception:
                    pass

            try:
                widget.configure(border_color="")
            except Exception:
                pass

            try:
                widget.configure(highlightthickness=0)
            except Exception:
                pass
        except Exception:
            pass
    
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
        webbrowser.open(f'http://localhost:{port}/')
    
    def _toggle_token_visibility(self):
        """Toggle token field visibility"""
        try:
            # Flip visibility flag
            self._token_visible = not getattr(self, '_token_visible', False)

            if self._token_visible:
                # Show the token
                try:
                    self.token_entry.configure(show="")
                except Exception:
                    try:
                        self.token_entry.config(show="")
                    except Exception:
                        pass
                # Update button label
                try:
                    self.token_show_button.configure(text="Hide")
                except Exception:
                    try:
                        self.token_show_button.config(text="Hide")
                    except Exception:
                        pass
            else:
                # Mask the token
                try:
                    self.token_entry.configure(show="*")
                except Exception:
                    try:
                        self.token_entry.config(show="*")
                    except Exception:
                        pass
                # Update button label
                try:
                    self.token_show_button.configure(text="Show")
                except Exception:
                    try:
                        self.token_show_button.config(text="Show")
                    except Exception:
                        pass
        except Exception:
            # If anything goes wrong, do nothing silently to avoid crashing the UI
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
            configs = self.settings_manager.parse_fan_configs() or []

            # Try to update both stream and game combo widgets' values in a way that
            # works for CTkComboBox and CTkOptionMenu across CTk versions.
            updated = False
            for combo_name in ('fan_stream_combo', 'fan_game_combo'):
                combo = getattr(self, combo_name, None)
                if combo is None:
                    continue
                try:
                    # Preferred: configure(values=...)
                    combo.configure(values=configs)
                    updated = True
                    continue
                except Exception:
                    pass
                try:
                    # Fallback: dict-style assignment (works for some CTkComboBox builds)
                    combo['values'] = configs
                    updated = True
                except Exception:
                    pass

            # Select current config if set (try .set(), which works for both widgets)
            current = self.settings_manager.get_setting('fan.selected_config', '')
            # Load current selections for stream and game selectors
            current_stream = self.settings_manager.get_setting('fan.selected_config_stream', '')
            current_game = self.settings_manager.get_setting('fan.selected_config_game', '')
            try:
                if hasattr(self, 'fan_stream_combo'):
                    if current_stream and current_stream in configs:
                        try:
                            self.fan_stream_combo.set(current_stream)
                        except Exception:
                            pass
                    elif configs:
                        try:
                            self.fan_stream_combo.set(configs[0])
                            # persist default if none set
                            self.settings_manager.set_setting('fan.selected_config_stream', configs[0])
                            # maintain legacy key for backward compatibility
                            try:
                                self.settings_manager.set_setting('fan.selected_config', configs[0])
                            except Exception:
                                pass
                        except Exception:
                            pass

                if hasattr(self, 'fan_game_combo'):
                    if current_game and current_game in configs:
                        try:
                            self.fan_game_combo.set(current_game)
                        except Exception:
                            pass
                    elif configs:
                        try:
                            # If game has no saved value, default to first but do not overwrite stream
                            self.fan_game_combo.set(configs[0])
                            self.settings_manager.set_setting('fan.selected_config_game', configs[0])
                        except Exception:
                            pass
            except Exception:
                # If .set() isn't supported, ignore silently
                pass

            # Ensure the combo/menu is enabled for user interaction when configs exist
            try:
                # Enable/disable both combos based on whether configs exist
                if configs:
                    for combo in (getattr(self, 'fan_stream_combo', None), getattr(self, 'fan_game_combo', None)):
                        if combo is None:
                            continue
                        try:
                            combo.configure(state='readonly')
                        except Exception:
                            try:
                                combo.configure(state='normal')
                            except Exception:
                                pass
                else:
                    for combo in (getattr(self, 'fan_stream_combo', None), getattr(self, 'fan_game_combo', None)):
                        if combo is None:
                            continue
                        try:
                            combo.configure(state='disabled')
                        except Exception:
                            pass
            except Exception:
                pass
                
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
        target = getattr(self, 'endpoints_result_text', None)
        if not self.app.is_server_running():
            if target:
                try:
                    target.delete(1.0, tk.END)
                    target.insert(1.0, "Error: Server is not running")
                except Exception:
                    pass
            return
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
                
            if target:
                try:
                    target.delete(1.0, tk.END)
                    target.insert(1.0, result_text)
                except Exception:
                    pass
            
        except Exception as e:
            if target:
                try:
                    target.delete(1.0, tk.END)
                    target.insert(1.0, f"Error: {str(e)}")
                except Exception:
                    pass
    
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
        # Helper to enable/disable buttons with appropriate disabled styling
        def _set_button_enabled(btn, enabled, ctk_fg=None, ctk_text=None):
            state = "normal" if enabled else "disabled"
            btn.configure(state=state)
            if enabled:
                if ctk_fg is not None:
                    btn.configure(fg_color=ctk_fg)
                if ctk_text is not None:
                    btn.configure(text_color=ctk_text)
            else:
                btn.configure(fg_color=getattr(self, '_disabled_btn_bg', '#6b6b6b'))
                btn.configure(text_color=getattr(self, '_disabled_btn_fg', '#BFC7CF'))

        # Helper: set text color in a way that works for CTkLabel (text_color)
        def _set_widget_text_color(widget, color):
            try:
                widget.configure(text_color=color)
                return
            except Exception:
                pass
            try:
                widget.configure(foreground=color)
                return
            except Exception:
                pass

        if self.app.is_server_running():
            self.server_status_var.set("Running")
            _set_widget_text_color(self.status_label, "green")

            # Update buttons: when running, Start should be disabled
            _set_button_enabled(self.start_button, False, ctk_fg=getattr(self, '_success', '#BBD760'), ctk_text=getattr(self, '_app_bg', '#1E1F2B'))
            _set_button_enabled(self.stop_button, True, ctk_fg=getattr(self, '_danger', '#FC6A6A'), ctk_text=getattr(self, '_fg', '#E6EEF3'))
            _set_button_enabled(self.restart_button, True, ctk_text=getattr(self, '_fg', '#E6EEF3'))

        else:
            self.server_status_var.set("Stopped")
            _set_widget_text_color(self.status_label, "red")

            _set_button_enabled(self.start_button, True, ctk_fg=getattr(self, '_success', '#BBD760'), ctk_text=getattr(self, '_app_bg', '#1E1F2B'))
            _set_button_enabled(self.stop_button, False, ctk_fg=getattr(self, '_danger', '#FC6A6A'), ctk_text=getattr(self, '_fg', '#E6EEF3'))
            _set_button_enabled(self.restart_button, False, ctk_text=getattr(self, '_fg', '#E6EEF3'))

            # bottom buttons removed; nothing to update on the bottom side
    
    def _update_status_timer(self):
        """Timer callback to update status"""
        self.update_server_status()
        # Schedule next update
        self.root.after(2000, self._update_status_timer)
    
    def _on_window_close(self):
        """Handle window close - minimize to tray instead of quit"""
        self.root.withdraw()  # Hide window instead of destroying