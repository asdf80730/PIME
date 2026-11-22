"""The Win32 layer of the PIME Key Bridge.

Everything that touches the Win32 API lives here: the low-level keyboard
hook, the foreground window probe, the mapping from a hook event to the key
event shape the PIME backend expects, and the Unicode injection that puts the
committed text back into the focused control.

Architecture and design by asdf80730.  Implementation generated with AI
assistance from omp (MiniMax-M3.1-Flash).
SPDX-License-Identifier: LGPL-2.1-or-later
"""

import ctypes
from ctypes import wintypes
import os
import threading

from . import keyevent
from .keyevent import KeyEvent

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(
    LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

LLKHF_EXTENDED = 0x01
LLKHF_UP = 0x02
LLKHF_INJECTED = 0x10

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
US_LAYOUT = 0x0409

# The marker the bridge stamps on the text it injects, so that its own hook
# ignores the injection and does not send it to the backend a second time.
INJECT_MARKER = 0x50494D45  # 'PIME'

# The virtual key of a Unicode packet: the key Windows builds for injected
# text, and the key no person ever presses.
VK_PACKET = 0xE7

# The virtual key of the backspace key.
VK_BACK = 0x08

# The logical modifier keys the backend reads, and the physical ones.
VK_SHIFT = keyevent.VK_SHIFT
VK_CONTROL = keyevent.VK_CONTROL
VK_MENU = keyevent.VK_MENU
VK_LCONTROL = keyevent.VK_LCONTROL
VK_RCONTROL = keyevent.VK_RCONTROL

# The physical modifier keys, and the logical key each one stands for.
# A driver may report a modifier under its logical code, so those are in
# the table as well.
MODIFIER_OF = keyevent.MODIFIER_OF

# The keys that make a combination the application's own.
VK_LWIN = keyevent.VK_LWIN
VK_RWIN = keyevent.VK_RWIN

# The keys the bridge keeps track of: the modifiers and the windows keys.
TRACKED_KEYS = keyevent.TRACKED_KEYS

# The keys that have a toggled state of their own.
TOGGLE_KEYS = (keyevent.VK_CAPITAL, 0x90, 0x91)

# --- the prototypes that matter on a 64-bit build ---------------------------

user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND,
                                             ctypes.POINTER(wintypes.DWORD))
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
user32.GetClassNameW.restype = ctypes.c_int
user32.GetKeyboardState.argtypes = (ctypes.POINTER(wintypes.BYTE),)
user32.GetKeyboardState.restype = wintypes.BOOL
user32.GetKeyboardLayout.argtypes = (wintypes.DWORD,)
user32.GetKeyboardLayout.restype = wintypes.HKL
user32.GetKeyboardLayoutList.argtypes = (ctypes.c_int, ctypes.POINTER(wintypes.HKL))
user32.GetKeyboardLayoutList.restype = ctypes.c_int
user32.ToUnicodeEx.argtypes = (wintypes.UINT, wintypes.UINT,
                                ctypes.POINTER(wintypes.BYTE), wintypes.LPWSTR,
                                ctypes.c_int, wintypes.DWORD, wintypes.HKL)
user32.ToUnicodeEx.restype = ctypes.c_int
user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, wintypes.HINSTANCE,
                                      wintypes.DWORD)
user32.SetWindowsHookExW.restype = wintypes.HHOOK if hasattr(wintypes, "HHOOK") \
    else ctypes.c_void_p
user32.UnhookWindowsHookEx.argtypes = (ctypes.c_void_p,)
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.CallNextHookEx.argtypes = (ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM,
                                   wintypes.LPARAM)
user32.CallNextHookEx.restype = LRESULT
user32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM,
                                       wintypes.LPARAM)
user32.PostThreadMessageW.restype = wintypes.BOOL
user32.SendInput.argtypes = (wintypes.UINT, ctypes.c_void_p, ctypes.c_int)
user32.SendInput.restype = wintypes.UINT
kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD,
                                                wintypes.LPWSTR,
                                                ctypes.POINTER(wintypes.DWORD))
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetCurrentThreadId.restype = wintypes.DWORD


class KBDLLHOOKSTRUCT(ctypes.Structure):
    """The hook event the system hands to a low-level keyboard hook."""

    _fields_ = [("vkCode", wintypes.DWORD),
                ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT),
                ("hi", HARDWAREINPUT),
                ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    """One entry of the SendInput array."""

    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD),
                ("u", _INPUTUNION)]


_us_layout = None


def us_keyboard_layout():
    """The en-US keyboard layout, so the char codes stay ASCII.

    The backend maps a char code to a bopomofo key, so a Chinese layout would
    turn the letter `j` into a Chinese character.  The layout of the focused
    window is irrelevant here; the US layout is what the TSF client would
    report for a plain Latin keyboard.
    """
    global _us_layout
    if _us_layout is not None:
        return _us_layout
    count = user32.GetKeyboardLayoutList(0, None)
    layout = None
    if count > 0:
        layouts = (wintypes.HKL * count)()
        if user32.GetKeyboardLayoutList(count, layouts) == count:
            for candidate in layouts:
                if (candidate & 0xFFFF) == US_LAYOUT:
                    layout = candidate
                    break
    if layout is None:
        layout = user32.GetKeyboardLayout(0)
    _us_layout = layout
    return layout


def char_for_key(vk, scan, extended, modifiers=()):
    """The character a key press produces, or 0 when it produces none.

    The state is built from the modifiers that are down, the way the C++
    client builds it.  The control key is left out of it, so `Ctrl` and a
    letter still spell the letter: the backend sees the control key in the
    key states and decides what the combination means.
    """
    state = (wintypes.BYTE * 256)()
    for code in modifiers:
        if code in (VK_CONTROL, VK_LCONTROL, VK_RCONTROL):
            continue  # the control key does not change the character
        if 0 <= code < 256:
            state[code] |= 0x80
        logical = MODIFIER_OF.get(code)
        if logical is not None:
            state[logical] |= 0x80
    for toggle in TOGGLE_KEYS:
        if user32.GetKeyState(toggle) & 1:
            state[toggle] |= 0x01
    buffer = ctypes.create_unicode_buffer(8)
    flags = 1 if extended else 0
    count = user32.ToUnicodeEx(vk, scan, state, buffer, 8, flags,
                                us_keyboard_layout())
    if count <= 0:
        return 0
    if count > 1:
        # A dead key followed by its composed character: the composed one
        # is the second entry of the buffer.
        return ord(buffer[1]) if len(buffer) > 1 else 0
    return ord(buffer[0])


def key_state_array(pressed_vk=None, modifiers=()):
    """The 256-entry key state array, in the TSF convention.

    Bit 7 marks a key that is down, bit 0 a key that is toggled; the array is
    indexed by the virtual key code.

    The modifiers come from the hook's own event stream: `GetKeyboardState`
    and `GetAsyncKeyState` answer for the thread that asks, and the thread
    that owns the hook is not the one that receives the keys.
    """
    states = [0] * 256
    for code in modifiers:
        if 0 <= code < 256:
            states[code] |= 0x80
        logical = MODIFIER_OF.get(code)
        if logical is not None:
            states[logical] |= 0x80
    for toggle in TOGGLE_KEYS:
        if user32.GetKeyState(toggle) & 1:
            states[toggle] |= 0x01
    if pressed_vk is not None and 0 <= pressed_vk < 256:
        states[pressed_vk] |= 0x80
    return states


def process_name_for_window(hwnd):
    """The name of the executable that owns `hwnd`."""
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return None
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False,
                                   pid.value)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer,
                                                   ctypes.byref(size)):
            return None
        return os.path.basename(buffer.value)
    finally:
        kernel32.CloseHandle(handle)


def inject_text(text):
    """Type `text` into the focused control as Unicode input.

    The injected keys carry the INJECT_MARKER, so the bridge's own hook
    ignores them and the focused control receives them as ordinary text.
    """
    if not text:
        return 0
    marker = ctypes.c_ulong(INJECT_MARKER)
    extra = ctypes.pointer(marker)
    inputs = (INPUT * len(text))()
    for index, character in enumerate(text):
        inputs[index].type = INPUT_KEYBOARD
        inputs[index].ki = KEYBDINPUT(0, ord(character), KEYEVENTF_UNICODE, 0,
                                      extra)
    sent = user32.SendInput(len(text), inputs, ctypes.sizeof(INPUT))
    return sent


def inject_backspaces(count):
    """Press the backspace key `count` times in the focused control.

    The keys carry the INJECT_MARKER, so the bridge's own hook leaves them
    alone and the focused control takes them as ordinary backspaces.
    """
    if count <= 0:
        return 0
    marker = ctypes.c_ulong(INJECT_MARKER)
    extra = ctypes.pointer(marker)
    inputs = (INPUT * (2 * count))()
    for index in range(count):
        down = 2 * index
        inputs[down].type = INPUT_KEYBOARD
        inputs[down].ki = KEYBDINPUT(VK_BACK, 0, 0, 0, extra)
        inputs[down + 1].type = INPUT_KEYBOARD
        inputs[down + 1].ki = KEYBDINPUT(VK_BACK, 0, KEYEVENTF_KEYUP, 0, extra)
    sent = user32.SendInput(2 * count, inputs, ctypes.sizeof(INPUT))
    return sent


class KeyboardHook(threading.Thread):
    """A low-level keyboard hook that hands the captured keys to a handler.

    The handler is called on the hook thread, so it must be fast; the bridge
    only decides here whether to swallow the key and queues the event for the
    worker thread that talks to the backend.
    """

    def __init__(self, on_key):
        super().__init__(name="pime-keybridge-hook", daemon=True)
        self._on_key = on_key
        self._modifiers = set()
        self._ready = threading.Event()
        self._error = None
        self._hook = None
        self._proc = HOOKPROC(self._hook_proc)

    def start(self):
        super().start()
        self._ready.wait(5)
        if self._error is not None:
            raise OSError("cannot install the keyboard hook: %s" % self._error)
        return self

    def run(self):
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        if not self._hook:
            self._error = ctypes.get_last_error()
            self._ready.set()
            return
        self._ready.set()
        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None

    def stop(self):
        if self.is_alive():
            user32.PostThreadMessageW(self.native_id, 0x0012, 0, 0)  # WM_QUIT

    @property
    def native_id(self):
        return self.ident or 0

    def _hook_proc(self, n_code, w_param, l_param):
        if n_code >= 0:
            event = self._translate(w_param, l_param)
            if event is not None and self._on_key(event):
                return 1  # swallow the key
        return user32.CallNextHookEx(None, n_code, w_param, l_param)

    def _is_own_injection(self, struct):
        """True for the text the bridge injected itself.

        A Unicode packet (VK_PACKET) is always an injection, never a key a
        person pressed, so it never belongs to the backend.
        """
        if struct.vkCode == VK_PACKET:
            return True
        if struct.dwExtraInfo and struct.dwExtraInfo[0] == INJECT_MARKER:
            return True
        return False

    def _translate(self, w_param, l_param):
        """The hook event as a `KeyEvent`, or None when it is not a key."""
        if w_param not in (WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP):
            return None
        struct = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        if self._is_own_injection(struct):
            return None  # the text the bridge put into the control itself
        key_up = bool(w_param in (WM_KEYUP, WM_SYSKEYUP))
        extended = bool(struct.flags & LLKHF_EXTENDED)
        modifiers = self._modifiers_for(struct.vkCode, key_up)
        char_code = 0 if key_up else char_for_key(struct.vkCode, struct.scanCode,
                                                 extended, modifiers)
        states = key_state_array(None if key_up else struct.vkCode, modifiers)
        return KeyEvent(struct.vkCode, struct.scanCode, extended, key_up,
                        char_code, states)

    def _modifiers_for(self, vk, key_up):
        """The modifiers that are down, as the hook's own events report them.

        The hook sees every key the system delivers, so it is the only place
        that knows which modifiers are down: `GetKeyboardState` and
        `GetAsyncKeyState` answer for the thread that asks, and this thread
        receives no keyboard input of its own.
        """
        if vk in TRACKED_KEYS:
            if key_up:
                self._modifiers.discard(vk)
            else:
                self._modifiers.add(vk)
        return frozenset(self._modifiers)
