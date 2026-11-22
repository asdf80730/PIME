"""The key event, in the shape the PIME backend expects, and the presses the
bridge took.

Pure Python: no Win32, so it can be reasoned about and tested anywhere.

Architecture and design by asdf80730.  Implementation generated with AI
assistance from omp (MiniMax-M3.1-Flash).
SPDX-License-Identifier: LGPL-2.1-or-later
"""

# The virtual key codes the bridge and the backend read.
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_CAPITAL = 0x14
VK_SPACE = 0x20
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_NUMLOCK = 0x90
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5

# The physical modifier keys, and the logical key each one stands for.
# A driver may report a modifier under its logical code, so those are in
# the table as well.
MODIFIER_OF = {
    VK_LSHIFT: VK_SHIFT,
    VK_RSHIFT: VK_SHIFT,
    VK_LCONTROL: VK_CONTROL,
    VK_RCONTROL: VK_CONTROL,
    VK_LMENU: VK_MENU,
    VK_RMENU: VK_MENU,
    VK_SHIFT: VK_SHIFT,
    VK_CONTROL: VK_CONTROL,
    VK_MENU: VK_MENU,
}

# The keys the bridge keeps track of: the modifiers and the windows keys.
TRACKED_KEYS = frozenset(MODIFIER_OF) | {VK_LWIN, VK_RWIN}


class Swallowed:
    """The presses the bridge took, so their release goes with them.

    The application must never see the release of a key it never saw
    pressed: it would think a key went down on its own.  A key the backend
    takes is taken for good, the release included.
    """

    def __init__(self):
        self._keys = set()

    def take(self, vk):
        """Record that the bridge took the press of `vk`."""
        self._keys.add(vk)

    def release(self, vk):
        """Forget the press of `vk`; True when the bridge had taken it."""
        taken = vk in self._keys
        self._keys.discard(vk)
        return taken

    def clear(self):
        """Forget every press: the focus left the target."""
        self._keys.clear()


class KeyEvent:
    """One key event, as the C++ client sends it to the backend.

    The field names match the JSON of the wire protocol: `charCode`,
    `keyCode`, `scanCode`, `isExtended`, `repeatCount` and `keyStates`.
    """

    __slots__ = ("vk", "scan", "extended", "key_up", "char_code", "key_states")

    def __init__(self, vk, scan, extended, key_up, char_code, key_states):
        self.vk = vk
        self.scan = scan
        self.extended = extended
        self.key_up = key_up
        self.char_code = char_code
        self.key_states = key_states

    def to_request(self):
        """The JSON fields of this event, as the backend wants them."""
        return {"charCode": self.char_code,
                "keyCode": self.vk,
                "scanCode": self.scan,
                "isExtended": self.extended,
                "repeatCount": 1,
                "keyStates": self.key_states}

    def __repr__(self):
        return ("KeyEvent(vk=0x%02X, scan=0x%02X, char=%r, %s)" %
                (self.vk, self.scan,
                 chr(self.char_code) if self.char_code else "",
                 "up" if self.key_up else "down"))
