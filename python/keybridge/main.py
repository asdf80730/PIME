"""The PIME Key Bridge entry point.

The bridge watches the keyboard, forwards the keys of the windows it is told
about to the PIME backend, and puts the committed text back into the focused
control.

Architecture and design by asdf80730.  Implementation generated with AI
assistance from omp (MiniMax-M3.1-Flash).
SPDX-License-Identifier: LGPL-2.1-or-later
"""

import argparse
import queue
import sys

from . import overlay as overlay_module
from . import protocol
from . import win32
from .echo import CompositionEcho
from .keyevent import KeyEvent

# The Windows 11 taskbar search flyout: the island itself lives in
# SearchHost.exe, the window that owns it in TextInputHost.exe.
DEFAULT_TARGETS = ("searchhost.exe", "textinputhost.exe")

# The virtual key codes of the characters the probe types.
PROBE_KEYS = {"j": 0x4A, "i": 0x49, "5": 0x35, " ": 0x20, "\r": 0x0D}


class ForegroundFilter:
    """Decides whether the keyboard hook should swallow a key.

    Only the keys of the target executables are forwarded; every other key
    goes to the application untouched.
    """

    def __init__(self, targets):
        self._targets = set(target.lower() for target in targets)
        self._names = {}

    @property
    def targets(self):
        return sorted(self._targets)

    def matches(self):
        hwnd = win32.user32.GetForegroundWindow()
        if not hwnd:
            return False
        name = self._name_of(hwnd)
        return name is not None and name.lower() in self._targets

    def _name_of(self, hwnd):
        """The executable that owns `hwnd`, cached per window."""
        name = self._names.get(hwnd)
        if name is None:
            name = win32.process_name_for_window(hwnd)
            if len(self._names) > 64:
                self._names.clear()
            self._names[hwnd] = name
        return name


def synthetic_event(character):
    """A key event for a character, as the hook would report it."""
    virtual_key = PROBE_KEYS[character]
    return KeyEvent(virtual_key, 0, False, False, ord(character),
                    win32.key_state_array(virtual_key))


def apply_reply(overlay, echo, reply, debug=False):
    """Show what the backend composed, and commit what it finished."""
    if debug:
        print("reply:", reply, flush=True)
    if "commitString" not in reply and "compositionString" not in reply:
        return  # a key release, or a reply that says nothing
    commit = reply.get("commitString")
    if commit:
        echo.commit(commit)
        overlay.hide()
        return
    composition = reply.get("compositionString") or ""
    candidates = reply.get("candidateList") or []
    cursor = reply.get("candidateCursor") or 0
    if composition or candidates:
        echo.show(composition)
        overlay.update(composition, candidates, cursor)
    else:
        echo.clear()
        overlay.hide()


def run_probe(args):
    """Type a syllable into the backend and print what it answers."""
    with protocol.LauncherPipe().connect() as pipe:
        pipe.handshake(args.profile)
        pipe.activate()
        for character in "ji5 \r":
            reply = pipe.key_down(synthetic_event(character))
            print("%r -> %s" % (character, reply), flush=True)
    return 0


def run(args):
    """Run the bridge until it is interrupted."""
    targets = args.target or list(DEFAULT_TARGETS)
    events = queue.Queue(maxsize=256)
    foreground = ForegroundFilter(targets)

    pipe = protocol.LauncherPipe().connect()
    pipe.handshake(args.profile)
    pipe.activate()
    overlay = overlay_module.CandidateOverlay().start()
    echo = CompositionEcho(win32.inject_text, win32.inject_backspaces)
    print("PIME key bridge: profile %s, targets %s" %
          (args.profile, ", ".join(foreground.targets)), flush=True)

    def on_key(event):
        if not foreground.matches():
            return False
        try:
            events.put_nowait(event)
        except queue.Full:
            return False
        if args.debug:
            print("key:", event, flush=True)
        return True

    hook = win32.KeyboardHook(on_key)
    hook.start()
    in_target = True
    try:
        while True:
            try:
                event = events.get(timeout=0.5)
            except queue.Empty:
                event = None
            if event is None:
                # Nothing was typed: the focus may have left the target, and
                # a composition that outlives its focus has to end.
                if in_target and not foreground.matches():
                    in_target = False
                    pipe.terminate_composition()
                    echo.clear()
                    overlay.hide()
                continue
            in_target = True
            if event.key_up:
                reply = pipe.key_up(event)
            else:
                reply = pipe.key_down(event)
            if reply is not None:
                apply_reply(overlay, echo, reply, args.debug)
    except KeyboardInterrupt:
        print("", flush=True)
    finally:
        hook.stop()
        overlay.stop()
        try:
            pipe.deactivate()
        except protocol.PipeError:
            pass
        pipe.close()
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="pime-keybridge",
        description="Forward the keys of a window TSF never reaches to the "
                    "PIME backend, and type the composed text back into it.")
    parser.add_argument("--profile", default=protocol.DEFAULT_PROFILE,
                        help="the language profile GUID of the backend "
                             "(default: the chewing module)")
    parser.add_argument("--target", action="append", default=[], metavar="EXE",
                        help="an executable whose keys are forwarded; "
                             "repeatable (default: %s)" %
                             ", ".join(DEFAULT_TARGETS))
    parser.add_argument("--debug", action="store_true",
                        help="print every key event and every reply")
    parser.add_argument("--probe", action="store_true",
                        help="send a synthetic key sequence to the backend and "
                             "print the replies, without touching the keyboard")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.probe:
        return run_probe(args)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
