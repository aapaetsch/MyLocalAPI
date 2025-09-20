# src/win_dpi_mixin.py
import os
import ctypes
from ctypes import wintypes

# ---- Safe type shims (older Python builds may lack some wintypes) ----
try:
    LRESULT = wintypes.LRESULT
except AttributeError:
    LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long

HWND   = getattr(wintypes, "HWND", ctypes.c_void_p)
UINT   = getattr(wintypes, "UINT", ctypes.c_uint)
WPARAM = getattr(wintypes, "WPARAM", ctypes.c_size_t)
LPARAM = getattr(wintypes, "LPARAM", ctypes.c_ssize_t)

# RECT structure for WM_DPICHANGED suggested bounds
class RECT(ctypes.Structure):
    _fields_ = [
        ("left",   ctypes.c_long),
        ("top",    ctypes.c_long),
        ("right",  ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

# ---- Win32 constants ----
WM_ENTERSIZEMOVE = 0x0231
WM_EXITSIZEMOVE  = 0x0232
WM_DPICHANGED    = 0x02E0
GWL_WNDPROC      = -4

# ---- User32 prototypes (argtypes/restype set explicitly) ----
_user32 = ctypes.windll.user32

if ctypes.sizeof(ctypes.c_void_p) == 8:
    _SetWindowLongPtr = _user32.SetWindowLongPtrW
    _GetWindowLongPtr = _user32.GetWindowLongPtrW
else:
    _SetWindowLongPtr = _user32.SetWindowLongW
    _GetWindowLongPtr = _user32.GetWindowLongW
_CallWindowProc = _user32.CallWindowProcW

_SetWindowLongPtr.argtypes = [HWND, ctypes.c_int, ctypes.c_void_p]
_SetWindowLongPtr.restype  = ctypes.c_void_p
_GetWindowLongPtr.argtypes = [HWND, ctypes.c_int]
_GetWindowLongPtr.restype  = ctypes.c_void_p
_CallWindowProc.argtypes   = [ctypes.c_void_p, HWND, UINT, WPARAM, LPARAM]
_CallWindowProc.restype    = LRESULT

# WNDPROC signature
WNDPROCTYPE = ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)


class SmoothMoveMixin:
    """
    Windows-only mixin to prevent laggy redraws when dragging across monitors:
      • Freeze heavy containers while dragging (WM_ENTERSIZEMOVE)
      • Run a single relayout after drag ends (WM_EXITSIZEMOVE)
      • Handle DPI transitions cleanly (WM_DPICHANGED) using the suggested rect

    Host needs:
      - self.root                : Tk/CTk root
      - self._heavy_containers   : [optional] list of frames to freeze/thaw
      - self._update_status_timer: [optional] timer method (we pause/resume)
      - _heavy_relayout(dpi)     : [optional] override to swap cached fonts/images
    """

    _old_wndproc = None
    _wndproc_ref = None
    _relayout_job = None
    _pending_dpi = None
    _dragging = False
    _status_timer_job = None

    def _install_winmsg_hook(self, defer=True):
        """Install the WndProc subclass. Call once after self.root exists.
        Set defer=True (default) to wait until the HWND is definitely created.
        """
        if os.name != "nt":
            return

        def _install():
            hwnd = self.root.winfo_id()
            if not hwnd:
                # Try again shortly if HWND isn't ready yet
                self.root.after(50, _install)
                return

            @WNDPROCTYPE
            def _wndproc(hWnd, msg, wParam, lParam):
                if msg == WM_ENTERSIZEMOVE:
                    self._on_enter_drag()
                elif msg == WM_EXITSIZEMOVE:
                    self._on_exit_drag()
                elif msg == WM_DPICHANGED:
                    try:
                        x_dpi = int(wParam) & 0xFFFF  # LOWORD
                    except Exception:
                        x_dpi = None
                    try:
                        rect = ctypes.cast(lParam, ctypes.POINTER(RECT)).contents
                        width  = rect.right - rect.left
                        height = rect.bottom - rect.top
                        # Use Windows' suggested size/pos to avoid flicker/jumps
                        self.root.geometry(f"{width}x{height}+{rect.left}+{rect.top}")
                    except Exception:
                        pass
                    self._schedule_relayout(x_dpi)

                return _CallWindowProc(self._old_wndproc, hWnd, msg, wParam, lParam)

            # Subclass and keep a strong ref so the callback isn't GC'd
            self._old_wndproc = _GetWindowLongPtr(hwnd, GWL_WNDPROC)
            _SetWindowLongPtr(hwnd, GWL_WNDPROC, ctypes.cast(_wndproc, ctypes.c_void_p))
            self._wndproc_ref = _wndproc

        if defer:
            # Defer to ensure CTk/Tk has actually created the native window
            self.root.after(50, _install)
        else:
            _install()

    # ---- Drag gating / debounce ----
    def _on_enter_drag(self):
        self._dragging = True
        self._freeze_layout()

    def _on_exit_drag(self):
        self._dragging = False
        self._schedule_relayout(None)

    def _schedule_relayout(self, dpi):
        if self._relayout_job:
            try:
                self.root.after_cancel(self._relayout_job)
            except Exception:
                pass
        self._pending_dpi = dpi
        self._relayout_job = self.root.after(10, self._run_relayout_once)

    def _run_relayout_once(self):
        self._relayout_job = None
        self._thaw_layout()
        dpi = self._pending_dpi

        if dpi:
            # Apply Tk scaling once for this DPI (helps CTk/Tk pick crisp sizes)
            try:
                self.root.tk.call("tk", "scaling", float(dpi) / 96.0)
            except Exception:
                pass

        try:
            self._heavy_relayout(dpi)
        except AttributeError:
            pass

    # ---- Freeze/thaw helpers (never hide widgets) ----
    def _freeze_layout(self):
        if getattr(self, "_status_timer_job", None):
            try:
                self.root.after_cancel(self._status_timer_job)
            except Exception:
                pass
            self._status_timer_job = None

        for f in (getattr(self, "_heavy_containers", None) or []):
            try:
                f.pack_propagate(False)
                f.grid_propagate(False)
            except Exception:
                pass

    def _thaw_layout(self):
        for f in (getattr(self, "_heavy_containers", None) or []):
            try:
                f.pack_propagate(True)
                f.grid_propagate(True)
            except Exception:
                pass

        if hasattr(self, "_update_status_timer") and not self._status_timer_job:
            self._status_timer_job = self.root.after(2000, self._update_status_timer)

    # ---- Override in your MainWindow if you want to rescale assets ----
    def _heavy_relayout(self, dpi):
        pass
