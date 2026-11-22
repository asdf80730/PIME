"""The composition echo: the composition, shown in the control being typed into.

A real IME shows its composition in the control it types into.  The search
box of the shell is a XAML island that no text service reaches, so the bridge
types the composition there itself and takes it back out when the
composition changes.

Pure Python: the typing and the erasing are given to it, so it can be
reasoned about and tested anywhere.

Architecture and design by asdf80730.  Implementation generated with AI
assistance from omp (MiniMax-M3.1-Flash).
SPDX-License-Identifier: LGPL-2.1-or-later
"""

import queue
import threading


class CompositionEcho:
    """Keeps the composition visible in the control that has the focus.

    The composition is always at the end of the control, so a new composition
    replaces the old one with as many backspaces as the old one had
    characters.
    """

    def __init__(self, type_text, erase_text):
        """Build the echo.

        `type_text(text)` types text into the focused control, and
        `erase_text(count)` takes `count` characters back out of it.
        """
        self._type_text = type_text
        self._erase_text = erase_text
        self._length = 0

    @property
    def length(self):
        """How many characters of composition are in the control now."""
        return self._length

    def show(self, composition):
        """Replace the composition in the control with a new one."""
        self._erase_text(self._length)
        self._length = len(composition)
        self._type_text(composition)

    def commit(self, text):
        """Replace the composition with the text the backend finished."""
        self._erase_text(self._length)
        self._length = 0
        self._type_text(text)

    def clear(self):
        """Take the composition out of the control."""
        self._erase_text(self._length)
        self._length = 0


class EchoWriter:
    """The composition, typed into the control by a thread of its own.

    The injection goes through the keyboard, and the input system waits for
    the keyboard hook while it runs.  A control that is slow to answer then
    holds up every key that follows it, and the keys wait for their answer,
    so the injection belongs on a thread of its own, away from the thread
    that answers for the keys.

    The commands are the ones of `CompositionEcho`: `show`, `commit` and
    `clear`.  They are applied in the order they are given.
    """

    def __init__(self, type_text, erase_text):
        self._echo = CompositionEcho(type_text, erase_text)
        self._commands = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="pime-keybridge-echo")
        self._thread.start()

    def show(self, composition):
        """Put the composition into the control."""
        self._commands.put(("show", composition))

    def commit(self, text):
        """Replace the composition with the text the backend finished."""
        self._commands.put(("commit", text))

    def clear(self):
        """Take the composition out of the control."""
        self._commands.put(("clear", ""))

    def _run(self):
        while True:
            command, text = self._commands.get()
            if command == "show":
                self._echo.show(text)
            elif command == "commit":
                self._echo.commit(text)
            else:
                self._echo.clear()
