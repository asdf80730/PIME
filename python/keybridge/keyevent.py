"""The key event, in the shape the PIME backend expects.

Pure Python: no Win32, so it can be reasoned about and tested anywhere.

Architecture and design by asdf80730.  Implementation generated with AI
assistance from omp (MiniMax-M3.1-Flash).
SPDX-License-Identifier: LGPL-2.1-or-later
"""


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
        return ("KeyEvent(vk=0x%02X, char=%r, %s)" %
                (self.vk, chr(self.char_code) if self.char_code else "",
                 "up" if self.key_up else "down"))
