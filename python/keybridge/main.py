"""The PIME Key Bridge entry point.

The bridge watches the keyboard, forwards the keys of the windows it is told
about to the PIME backend, and puts the committed text back into the focused
control.

The backend decides what every key means, exactly as it does for a host the
C++ client owns: the bridge asks it, and the answer says whether the key
belongs to the backend or to the application.  The bridge therefore waits for
that answer before the key reaches the application.

Architecture and design by asdf80730.  Implementation generated with AI
assistance from omp (MiniMax-M3.1-Flash).
SPDX-License-Identifier: LGPL-2.1-or-later
"""

import argparse
import queue
import sys
import threading
import time

from . import overlay as overlay_module
from . import protocol
from . import win32
from .echo import EchoWriter
from .focus import FocusTracker, ForegroundChangeTracker
from .keyevent import KeyEvent, Swallowed
from .mode import is_toggle, mode_command_id, mode_from_reply

# The Windows 11 taskbar search flyout: the island itself lives in
# SearchHost.exe, the window that owns it in TextInputHost.exe.
DEFAULT_TARGETS = ("searchhost.exe", "textinputhost.exe")

# The virtual key codes of the characters the probe types.
PROBE_KEYS = {"j": 0x4A, "i": 0x49, "5": 0x35, " ": 0x20, "\r": 0x0D}

# How long the hook waits for the backend's answer to a key before it gives
# up on the backend and lets the keys of the target reach the application.
ANSWER_TIMEOUT = 1.0

# The clock the debug output counts from.
T0 = time.time()


def stamp():
    """The time since the bridge started, for the debug output."""
    return "[%7.3f]" % (time.time() - T0)


class Request:
    """One key on its way to the backend, and the answer that comes back.

    The hook cannot know whether a key belongs to the backend before the
    backend has seen it, so the hook waits here for the answer: the key
    reaches the application only after the hook returns.
    """

    def __init__(self, event, toggle=False):
        self.event = event
        self.toggle = toggle
        self.swallow = False
        self.done = threading.Event()


class ForegroundFilter:
    """Decides whether the keyboard hook should swallow a key.

    Only the keys of the target executables are forwarded; every other key
    goes to the application untouched.
    """

    def __init__(self, targets, debug=False):
        self._targets = set(target.lower() for target in targets)
        self._names = {}
        self._debug = debug
        self._changes = ForegroundChangeTracker()

    @property
    def targets(self):
        return sorted(self._targets)

    def matches(self):
        hwnd = win32.user32.GetForegroundWindow()
        if not hwnd:
            if self._debug:
                changed = self._changes.observe("", "", "")
                if changed is not None:
                    print(stamp() + " foreground: none matched=False",
                          flush=True)
            return False
        name = self._name_of(hwnd)
        matched = name is not None and name.lower() in self._targets
        if self._debug:
            process, class_name, title = win32.window_info(hwnd)
            changed = self._changes.observe(process or name or "", class_name,
                                            title)
            if changed is not None:
                print(stamp() +
                      " foreground: process=%s class=%s title=%r matched=%s" %
                      (changed[0], changed[1], changed[2], matched),
                      flush=True)
        return matched

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
        command_id = mode_command_id(pipe.activate())
        print("mode command: %s" % command_id, flush=True)
        for character in "ji5 \r":
            reply = pipe.key_down(synthetic_event(character))
            print("%r -> %s" % (character, "the backend's" if reply is not None
                               else "the application's"), flush=True)
            print("    %s" % reply, flush=True)
        if command_id is None:
            print("the backend offers no mode switch", flush=True)
            return 0
        reply = pipe.command(command_id)
        print("toggle -> %s" % mode_from_reply(reply), flush=True)
        print("    %s" % reply, flush=True)
        pipe.terminate_composition()
        after = pipe.key_down(synthetic_event("j"))
        print("'j' after the toggle -> %s" %
              ("the backend's" if after is not None else "the application's"),
              flush=True)
    return 0


def run(args):
    """Run the bridge until it is interrupted."""
    targets = args.target or list(DEFAULT_TARGETS)
    events = queue.Queue(maxsize=256)
    foreground = ForegroundFilter(targets, debug=args.debug)
    swallowed = Swallowed()
    broken = threading.Event()

    pipe = protocol.LauncherPipe().connect()
    pipe.handshake(args.profile)
    command_id = mode_command_id(pipe.activate())
    overlay = overlay_module.CandidateOverlay().start()
    echo = EchoWriter(win32.inject_text, win32.inject_backspaces)
    print("PIME key bridge: profile %s, targets %s" %
          (args.profile, ", ".join(foreground.targets)), flush=True)
    if command_id is None:
        print("PIME key bridge: the backend offers no mode switch; "
              "Ctrl+Space belongs to the application", flush=True)

    def handle_key(event):
        """Ask the backend about the key.

        Returns whether the backend takes the key, and the reply that
        carries the new composition when there is one.
        """
        start = time.time()
        if event.key_up:
            reply = pipe.key_up(event)
            # The release of a key the bridge took goes with the press.
            taken = swallowed.release(event.vk)
            if args.debug:
                print(stamp() + " backend: %s in %.1f ms" %
                      (event, (time.time() - start) * 1000), flush=True)
            return taken or reply is not None, None
        reply = pipe.key_down(event)
        if args.debug:
            print(stamp() + " backend: %s in %.1f ms" %
                  (event, (time.time() - start) * 1000), flush=True)
        if reply is None:
            return False, None  # the key belongs to the application
        swallowed.take(event.vk)
        return True, reply

    def handle_toggle(event):
        """Ask the backend to switch between the input languages."""
        swallowed.take(event.vk)
        pipe.terminate_composition()
        reply = pipe.command(command_id)
        print("PIME key bridge: %s mode" % (mode_from_reply(reply) or "switched"),
              flush=True)
        return True

    def on_key(event):
        """The hook's answer: True when the bridge takes the key."""
        if broken.is_set() or not foreground.matches():
            return False
        request = Request(event, toggle=is_toggle(event) and
                          command_id is not None)
        try:
            events.put_nowait(request)
        except queue.Full:
            return False
        start = time.time()
        if not request.done.wait(ANSWER_TIMEOUT):
            broken.set()
            print("PIME key bridge: the backend did not answer; the keys of "
                  "the target reach the application from now on", flush=True)
            return False
        if args.debug:
            print(stamp() + " hook: %s answered in %.1f ms" %
                  (event, (time.time() - start) * 1000), flush=True)
        return request.swallow

    hook = win32.KeyboardHook(on_key)
    hook.start()
    focus = FocusTracker(in_target=True)
    try:
        while True:
            try:
                request = events.get(timeout=0.5)
            except queue.Empty:
                request = None
            if request is None:
                # Nothing was typed: the focus may have left the target, and
                # a composition that outlives its focus has to end.
                if focus.check_left(foreground.matches()):
                    pipe.terminate_composition()
                    echo.clear()
                    overlay.hide()
                    swallowed.clear()
                continue
            focus.mark_in_target()
            reply = None
            try:
                if request.toggle:
                    request.swallow = handle_toggle(request.event)
                else:
                    request.swallow, reply = handle_key(request.event)
            finally:
                # The answer is in: the key may reach the application now.
                request.done.set()
            if request.toggle:
                # The composition ends with the mode switch.
                echo.clear()
                overlay.hide()
            elif reply is not None:
                # The composition goes into the control after the key: an
                # injection while the hook thread waits for an answer costs
                # the input system hundreds of milliseconds.
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
