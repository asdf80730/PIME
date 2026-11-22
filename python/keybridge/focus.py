"""Pure-Python focus and foreground-change bookkeeping for the key bridge.

Kept free of Win32 imports so the state transitions can be tested anywhere.

Architecture and design by asdf80730.  Implementation generated with AI
assistance from Sider.
SPDX-License-Identifier: LGPL-2.1-or-later
"""


class FocusTracker:
    """Tracks whether the target window currently holds focus.

    When focus leaves a target window after keys were handled there, any
    in-flight composition must be terminated and local state cleared.
    """

    def __init__(self, in_target=True):
        self.in_target = bool(in_target)

    def mark_in_target(self):
        """Record that a key was just handled for a target window."""
        self.in_target = True

    def check_left(self, currently_in_target):
        """Return True on the transition from target to non-target."""
        if self.in_target and not currently_in_target:
            self.in_target = False
            return True
        return False


class ForegroundChangeTracker:
    """Reports foreground window metadata only when it changes."""

    def __init__(self):
        self._last = None

    def observe(self, process, class_name, title):
        """Return `(process, class_name, title)` if changed, else None."""
        current = (process or "", class_name or "", title or "")
        if current == self._last:
            return None
        self._last = current
        return current
