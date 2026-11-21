"""The PIMELauncher pipe protocol, spoken from Python.

The launcher is a pass-through: every JSON line the client sends is forwarded
to the backend with the client id in front of it, and every line the backend
sends back is written to the pipe.  The first line is the handshake, which
names the language profile the backend should serve.

Architecture and design by asdf80730.  Implementation generated with AI
assistance from omp (MiniMax-M3.1-Flash).
SPDX-License-Identifier: LGPL-2.1-or-later
"""

import ctypes
from ctypes import wintypes
import json
import os

from . import win32

# The chewing module, the profile the bridge defaults to.
DEFAULT_PROFILE = "{f80736aa-28db-423a-92c9-5540f501c939}"

PIPE_TEMPLATE = r"\\.\pipe\{user}\PIME\Launcher"


class PipeError(RuntimeError):
    """The launcher pipe is gone, or answered something unusable."""


def launcher_pipe_name(user=None):
    """The pipe the launcher listens on, one per user."""
    user = user or os.environ.get("USERNAME") or os.environ.get("USER")
    if not user:
        raise PipeError("cannot tell the user name; set USERNAME")
    return PIPE_TEMPLATE.format(user=user)


class LauncherPipe:
    """A client connection to PIMELauncher."""

    def __init__(self, pipe_name=None):
        self.name = pipe_name or launcher_pipe_name()
        self._handle = None
        self._seq = 0
        self._buffer = b""

    # -- connection --------------------------------------------------------

    def connect(self):
        """Open the pipe."""
        handle = win32.kernel32.CreateFileW(
            self.name, win32.GENERIC_READ | win32.GENERIC_WRITE, 0, None,
            win32.OPEN_EXISTING, 0, None)
        if handle == win32.INVALID_HANDLE_VALUE:
            raise PipeError("cannot open %s (error %d)" %
                            (self.name, ctypes.get_last_error()))
        self._handle = handle
        return self

    def close(self):
        """Close the pipe."""
        if self._handle is not None:
            win32.kernel32.CloseHandle(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, *_exception):
        self.close()

    @property
    def connected(self):
        return self._handle is not None

    # -- the line protocol -------------------------------------------------

    def send(self, payload):
        """Write one JSON line."""
        data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        written = wintypes.DWORD()
        ok = win32.kernel32.WriteFile(self._handle, data, len(data),
                                      ctypes.byref(written), None)
        if not ok or written.value != len(data):
            raise PipeError("cannot write to the launcher (error %d)" %
                            ctypes.get_last_error())

    def receive(self):
        """Read one JSON line."""
        while b"\n" not in self._buffer:
            chunk = ctypes.create_string_buffer(8192)
            read = wintypes.DWORD()
            if not win32.kernel32.ReadFile(self._handle, chunk, 8192,
                                           ctypes.byref(read), None):
                raise PipeError("cannot read from the launcher (error %d)" %
                                ctypes.get_last_error())
            if read.value == 0:
                raise PipeError("the launcher closed the pipe")
            self._buffer += chunk.raw[:read.value]
        line, _, rest = self._buffer.partition(b"\n")
        self._buffer = rest
        return json.loads(line.decode("utf-8"))

    def request(self, method, **fields):
        """Send a request and wait for its reply."""
        if self._handle is None:
            raise PipeError("the pipe is not connected")
        self._seq += 1
        payload = {"method": method, "seqNum": self._seq}
        payload.update(fields)
        self.send(payload)
        return self.receive()

    # -- the handshake and the key flow ------------------------------------

    def handshake(self, profile_guid):
        """Name the language profile the backend should serve."""
        reply = self.request("init", id=profile_guid, isWindows8Above=True,
                              isMetroApp=False, isUiLess=False, isConsole=False)
        if not reply.get("success"):
            raise PipeError("the backend refused the profile %s" % profile_guid)
        return reply

    def activate(self, keyboard_open=False):
        """Tell the backend the client is active."""
        return self.request("onActivate", isKeyboardOpen=keyboard_open)

    def deactivate(self):
        """Tell the backend the client is gone."""
        return self.request("onDeactivate")

    def terminate_composition(self, forced=True):
        """Tell the backend the composition ended, as a lost focus does."""
        return self.request("onCompositionTerminated", forced=forced)

    def key_down(self, event):
        """Send a key press; the reply carries the new composition."""
        fields = event.to_request()
        if not self.request("filterKeyDown", **fields).get("return"):
            return None
        return self.request("onKeyDown", **fields)

    def key_up(self, event):
        """Send a key release."""
        fields = event.to_request()
        if not self.request("filterKeyUp", **fields).get("return"):
            return None
        return self.request("onKeyUp", **fields)
