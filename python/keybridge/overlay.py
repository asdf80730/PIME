"""The composition overlay: a small always-on-top window of the bridge's own.

The XAML island that hosts the taskbar search box draws nothing of the
composition, and the bridge cannot underline text inside it, so the
composition and the candidate list are drawn in this window instead.  The
window never takes the focus and lets the mouse through.

Architecture and design by asdf80730.  Implementation generated with AI
assistance from omp (MiniMax-M3.1-Flash).
SPDX-License-Identifier: LGPL-2.1-or-later
"""

import ctypes
from ctypes import wintypes
import threading

from . import win32

WM_APP_UPDATE = 0x8001
WM_PAINT = 0x000F
WM_NCHITTEST = 0x0084
WM_DESTROY = 0x0002

WS_POPUP = 0x80000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000

SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

HTRANSPARENT = -1
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

TRANSPARENT = 1
DT_CALCRECT = 0x0400
DT_LEFT = 0x0000
DT_SINGLELINE = 0x0020
DT_WORDBREAK = 0x0010

WHITE = 0x00FFFFFF
BLACK = 0x00000000
RED = 0x000000FF

WNDPROC = ctypes.WINFUNCTYPE(win32.LRESULT, wintypes.HWND, wintypes.UINT,
                              wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR)]


class PAINTSTRUCT(ctypes.Structure):
    """The paint record of a window; ctypes.wintypes has no layout for it."""

    _fields_ = [("hdc", wintypes.HDC),
                ("fErase", wintypes.BOOL),
                ("rcPaint", wintypes.RECT),
                ("fRestore", wintypes.BOOL),
                ("fIncUpdate", wintypes.BOOL),
                ("rgbReserved", wintypes.BYTE * 32)]


class MONITORINFO(ctypes.Structure):
    """The geometry of a monitor; ctypes.wintypes has no layout for it."""

    _fields_ = [("cbSize", wintypes.DWORD),
                ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD)]


MONITOR_DEFAULTTONEAREST = 0x00000002


win32.user32.RegisterClassW.argtypes = (ctypes.POINTER(WNDCLASSW),)
win32.user32.RegisterClassW.restype = wintypes.ATOM
win32.user32.CreateWindowExW.restype = wintypes.HWND
win32.user32.CreateWindowExW.argtypes = (
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND,
    wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p)
win32.user32.DefWindowProcW.restype = win32.LRESULT
win32.user32.DefWindowProcW.argtypes = (wintypes.HWND, wintypes.UINT,
                                         wintypes.WPARAM, wintypes.LPARAM)
win32.user32.BeginPaint.restype = wintypes.HDC
win32.user32.EndPaint.argtypes = (wintypes.HWND, ctypes.POINTER(PAINTSTRUCT))
win32.user32.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
win32.user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
win32.user32.FillRect.argtypes = (wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                                   wintypes.HBRUSH)
win32.user32.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                       ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                       wintypes.UINT)
win32.user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
win32.user32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                       wintypes.LPARAM)
win32.user32.InvalidateRect.argtypes = (wintypes.HWND, ctypes.c_void_p, wintypes.BOOL)
win32.user32.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
win32.user32.MonitorFromWindow.restype = wintypes.HANDLE
win32.user32.GetMonitorInfoW.argtypes = (wintypes.HANDLE,
                                          ctypes.POINTER(MONITORINFO))
win32.user32.GetMonitorInfoW.restype = wintypes.BOOL
win32.gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
win32.gdi32.CreateFontW.restype = wintypes.HGDIOBJ
win32.gdi32.SelectObject.restype = wintypes.HGDIOBJ
win32.gdi32.DeleteObject.argtypes = (wintypes.HGDIOBJ,)
win32.gdi32.SetBkMode.argtypes = (wintypes.HDC, ctypes.c_int)
win32.gdi32.SetTextColor.argtypes = (wintypes.HDC, wintypes.DWORD)
win32.gdi32.GetTextExtentPoint32W.argtypes = (wintypes.HDC, wintypes.LPCWSTR,
                                               ctypes.c_int,
                                               ctypes.POINTER(wintypes.SIZE))
win32.user32.DrawTextW.argtypes = (wintypes.HDC, wintypes.LPWSTR, ctypes.c_int,
                                   ctypes.POINTER(wintypes.RECT), wintypes.UINT)


class CandidateOverlay:
    """The window that shows the composition and the candidate list."""

    CLASS_NAME = "PIMEKeyBridgeOverlay"

    def __init__(self, font_name="MingLiu", font_size=17):
        self._font_name = font_name
        self._font_size = font_size
        self._lock = threading.Lock()
        self._composition = ""
        self._candidates = []
        self._cursor = 0
        self._visible = False
        self._hwnd = None
        self._geometry = None
        self._thread = None
        self._ready = threading.Event()
        self._error = None
        self._proc = WNDPROC(self._wnd_proc)

    # -- lifecycle ---------------------------------------------------------

    def start(self):
        """Create the window on its own thread."""
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="pime-keybridge-overlay")
        self._thread.start()
        self._ready.wait(5)
        if self._error is not None:
            raise OSError("cannot create the overlay window: %s" % self._error)
        return self

    def stop(self):
        if self._hwnd:
            win32.user32.PostMessageW(self._hwnd, WM_DESTROY, 0, 0)

    def _run(self):
        instance = win32.kernel32.GetModuleHandleW(None)
        window_class = WNDCLASSW()
        window_class.lpfnWndProc = self._proc
        window_class.hInstance = instance
        window_class.hCursor = win32.user32.LoadCursorW(None, ctypes.c_wchar_p(32512))
        window_class.lpszClassName = self.CLASS_NAME
        win32.user32.RegisterClassW(ctypes.byref(window_class))
        hwnd = win32.user32.CreateWindowExW(
            WS_EX_TOOLWINDOW | WS_EX_TOPMOST | WS_EX_NOACTIVATE,
            self.CLASS_NAME, "PIME", WS_POPUP, 0, 0, 240, 60, None, None,
            instance, None)
        if not hwnd:
            self._error = ctypes.get_last_error()
            self._ready.set()
            return
        self._hwnd = hwnd
        self._ready.set()
        message = wintypes.MSG()
        while win32.user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            win32.user32.TranslateMessage(ctypes.byref(message))
            win32.user32.DispatchMessageW(ctypes.byref(message))

    # -- the state ---------------------------------------------------------

    def update(self, composition, candidates, cursor=0):
        """Show a composition and its candidate list."""
        with self._lock:
            self._composition = composition or ""
            self._candidates = list(candidates or [])
            self._cursor = cursor
            self._visible = True
        self._post(WM_APP_UPDATE)

    def hide(self):
        """Show nothing."""
        with self._lock:
            self._visible = False
            self._composition = ""
            self._candidates = []
        self._post(WM_APP_UPDATE)

    def _post(self, message):
        if self._hwnd:
            win32.user32.PostMessageW(self._hwnd, message, 0, 0)

    # -- the window --------------------------------------------------------

    def _wnd_proc(self, hwnd, message, w_param, l_param):
        if message == WM_APP_UPDATE:
            self._refresh()
            return 0
        if message == WM_PAINT:
            self._paint(hwnd)
            return 0
        if message == WM_NCHITTEST:
            return HTRANSPARENT  # the mouse belongs to the app below
        return win32.user32.DefWindowProcW(hwnd, message, w_param, l_param)

    def _refresh(self):
        """Show or hide the window, then repaint it."""
        with self._lock:
            visible = self._visible
        if visible:
            self._place()
            # Hide and show again: a window that was already on screen keeps
            # its place in the z-order, and the shell's search flyout is
            # always above a window that was there before it opened.
            win32.user32.ShowWindow(self._hwnd, SW_HIDE)
            win32.user32.ShowWindow(self._hwnd, SW_SHOWNOACTIVATE)
        else:
            win32.user32.ShowWindow(self._hwnd, SW_HIDE)
        win32.user32.InvalidateRect(self._hwnd, None, True)

    def _lines(self):
        """The text to draw, and which part of it is the selected candidate."""
        with self._lock:
            composition = self._composition
            candidates = list(self._candidates)
            cursor = self._cursor
        lines = []
        if composition:
            lines.append((composition, False))
        if candidates:
            items = []
            for index, candidate in enumerate(candidates):
                items.append("%d. %s" % (index + 1, candidate))
            lines.append(("  ".join(items), True))
        return lines, cursor

    def _place(self):
        """Put the window under the foreground window, or above it.

        The taskbar search box sits at the bottom of the screen, so there is
        no room below it; the candidate window goes above the window instead,
        the way an IME candidate window does.
        """
        foreground = win32.user32.GetForegroundWindow()
        rect = wintypes.RECT()
        if foreground:
            win32.user32.GetWindowRect(foreground, ctypes.byref(rect))
        else:
            rect.left, rect.top, rect.right, rect.bottom = 0, 0, 0, 0
        width, height = self._size()
        work = self._work_area(foreground)
        x = rect.left
        y = rect.bottom + 4
        if y + height > work.bottom:
            # No room below the window: the taskbar search box lives at the
            # bottom of the screen, so the overlay sits on the bottom of the
            # work area, right above it.
            y = work.bottom - height
        if y < work.top:
            y = work.top
        if x + width > work.right:
            x = max(work.left, work.right - width)
        self._geometry = (x, y, width, height)
        self._raise()

    def _raise(self):
        """Put the window above every other topmost window.

        The shell's search flyout is a topmost window too, and it is raised
        again every time it takes the text the bridge injects, which is
        after the bridge put this window there.  A window that is already
        topmost keeps its place in the band, so taking the window out of
        the band and putting it back is what puts it above the flyout.
        """
        if not self._geometry:
            return
        x, y, width, height = self._geometry
        win32.user32.SetWindowPos(self._hwnd, HWND_NOTOPMOST, x, y, width, height,
                                   SWP_NOACTIVATE | SWP_NOMOVE | SWP_NOSIZE)
        win32.user32.SetWindowPos(self._hwnd, HWND_TOPMOST, x, y, width, height,
                                   SWP_NOACTIVATE | SWP_SHOWWINDOW)

    def _work_area(self, hwnd):
        """The part of the screen a window may use."""
        monitor = win32.user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if monitor and win32.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return info.rcWork
        return wintypes.RECT(0, 0, 1920, 1080)

    def _size(self):
        """The size the window needs for the current text."""
        lines, _cursor = self._lines()
        hdc = win32.user32.GetDC(None)
        try:
            font = self._create_font()
            old = win32.gdi32.SelectObject(hdc, font)
            try:
                width = 0
                for text, _is_candidates in lines:
                    size = wintypes.SIZE()
                    win32.gdi32.GetTextExtentPoint32W(hdc, text, len(text),
                                                      ctypes.byref(size))
                    width = max(width, size.cx)
            finally:
                win32.gdi32.SelectObject(hdc, old)
                win32.gdi32.DeleteObject(font)
        finally:
            win32.user32.ReleaseDC(None, hdc)
        line_height = int(self._font_size * 1.6)
        return max(width + 16, 120), max(line_height * max(len(lines), 1) + 8, 24)

    def _create_font(self):
        return win32.gdi32.CreateFontW(-self._font_size, 0, 0, 0, 400, 0, 0, 0,
                                       134, 0, 0, 0, 0, self._font_name)

    def _paint(self, hwnd):
        lines, cursor = self._lines()
        paint = PAINTSTRUCT()
        hdc = win32.user32.BeginPaint(hwnd, ctypes.byref(paint))
        if not hdc:
            return
        try:
            rect = wintypes.RECT()
            win32.user32.GetClientRect(hwnd, ctypes.byref(rect))
            brush = win32.gdi32.CreateSolidBrush(WHITE)
            win32.user32.FillRect(hdc, ctypes.byref(rect), brush)
            win32.gdi32.DeleteObject(brush)
            font = self._create_font()
            old = win32.gdi32.SelectObject(hdc, font)
            win32.gdi32.SetBkMode(hdc, TRANSPARENT)
            try:
                y = 4
                line_height = int(self._font_size * 1.6)
                for text, is_candidates in lines:
                    win32.gdi32.SetTextColor(hdc, BLACK)
                    line_rect = wintypes.RECT(4, y, rect.right - 4,
                                              y + line_height)
                    win32.user32.DrawTextW(hdc, text, len(text),
                                          ctypes.byref(line_rect),
                                          DT_LEFT | DT_SINGLELINE)
                    if is_candidates and 0 <= cursor < len(self._candidates):
                        self._paint_cursor(hdc, text, cursor, y, line_height)
                    y += line_height
            finally:
                win32.gdi32.SelectObject(hdc, old)
                win32.gdi32.DeleteObject(font)
        finally:
            win32.user32.EndPaint(hwnd, ctypes.byref(paint))

    def _paint_cursor(self, hdc, text, cursor, y, line_height):
        """Draw the selected candidate in red."""
        prefix = "  ".join("%d. %s" % (index + 1, candidate)
                           for index, candidate in enumerate(self._candidates)
                           if index < cursor)
        offset = len(prefix) + len("%d. " % (cursor + 1))
        size = wintypes.SIZE()
        win32.gdi32.GetTextExtentPoint32W(hdc, text[:offset], offset,
                                          ctypes.byref(size))
        win32.gdi32.SetTextColor(hdc, RED)
        item = "%d. %s" % (cursor + 1, self._candidates[cursor])
        item_rect = wintypes.RECT(4 + size.cx, y, 2000, y + line_height)
        win32.user32.DrawTextW(hdc, item, len(item), ctypes.byref(item_rect),
                              DT_LEFT | DT_SINGLELINE)
        win32.gdi32.SetTextColor(hdc, BLACK)
