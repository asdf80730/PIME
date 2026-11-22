"""The input mode, and the command that switches it.

The mode belongs to the backend.  The bridge asks the backend to switch it,
the way the language bar button of the C++ client does, and the backend's
own answer to every key then says whether the key is its own or the
application's.  The bridge keeps no mode of its own, so the two can never
disagree about what a key means.

Pure Python: no Win32, so it can be reasoned about and tested anywhere.

Architecture and design by asdf80730.  Implementation generated with AI
assistance from omp (MiniMax-M3.1-Flash).
SPDX-License-Identifier: LGPL-2.1-or-later
"""

from .keyevent import VK_CONTROL, VK_LCONTROL, VK_RCONTROL, VK_SPACE

# The button the backend offers to switch between the input languages.
MODE_BUTTON = "windows-mode-icon"

# The modes the bridge reports.
CHINESE = "chinese"
ENGLISH = "english"

# The icons the mode button carries, and the mode each of them means.
# The chewing module draws the mode in the icon of its button.
CHINESE_ICONS = ("simc", "trac", "capseng")


def _is_down(key_states, code):
    return bool(key_states[code] & 0x80)


def is_toggle(event):
    """True for the hotkey that switches the input mode: Ctrl+Space."""
    if event.key_up or event.vk != VK_SPACE:
        return False
    return any(_is_down(event.key_states, code) for code in
               (VK_CONTROL, VK_LCONTROL, VK_RCONTROL))


def mode_command_id(reply):
    """The command that switches the mode, out of the backend's buttons.

    The backend names its buttons in the reply to `onActivate`; the mode
    button carries the command the C++ client sends when the user clicks
    it.  None when the backend offers no such button.
    """
    for button in reply.get("addButton") or []:
        if button.get("id") != MODE_BUTTON:
            continue
        command_id = button.get("commandId")
        if command_id is not None:
            return command_id
    return None


def mode_from_reply(reply):
    """The mode the backend reports, read from the icon of its button.

    The chewing module draws the mode in the icon of the mode button:
    `eng.ico` for English, the Chinese ones for Chinese.  None when the
    reply names no icon the bridge knows.
    """
    for button in reply.get("changeButton") or []:
        if button.get("id") != MODE_BUTTON:
            continue
        icon = (button.get("icon") or "").replace("\\", "/").rsplit("/", 1)[-1]
        name = icon.lower()
        if name.startswith("eng"):
            return ENGLISH
        if name.startswith(CHINESE_ICONS):
            return CHINESE
    return None
