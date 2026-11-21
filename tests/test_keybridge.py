"""Unit tests for the pure-Python parts of the PIME key bridge.

The key event is the shape the C++ client sends to the backend, and the
composition echo is the bookkeeping that keeps the composition visible in the
control being typed into. Neither needs Windows.
"""

# Generated with assistance from omp (MiniMax-M3.1-Flash).

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
PYTHON_DIR = os.path.join(ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

from keybridge.echo import CompositionEcho
from keybridge.keyevent import KeyEvent


class KeyEventTest(unittest.TestCase):
    """The wire shape of a key event."""

    def test_request_carries_the_fields_the_backend_reads(self):
        states = [0] * 256
        states[0x41] = 0x80
        event = KeyEvent(0x41, 0x1E, True, False, ord("A"), states)
        request = event.to_request()
        self.assertEqual(request["keyCode"], 0x41)
        self.assertEqual(request["charCode"], ord("A"))
        self.assertEqual(request["scanCode"], 0x1E)
        self.assertTrue(request["isExtended"])
        self.assertEqual(request["repeatCount"], 1)
        self.assertIs(request["keyStates"], states)

    def test_a_key_release_has_no_character(self):
        event = KeyEvent(0x41, 0x1E, False, True, 0, [0] * 256)
        self.assertTrue(event.key_up)
        self.assertEqual(event.to_request()["charCode"], 0)


class CompositionEchoTest(unittest.TestCase):
    """The composition in the control, and the erasing of the old one."""

    def setUp(self):
        self.typed = []
        self.erased = []
        self.echo = CompositionEcho(self.typed.append, self.erased.append)

    def test_the_first_composition_is_only_typed(self):
        self.echo.show("ㄨ")
        self.assertEqual(self.typed, ["ㄨ"])
        self.assertEqual(self.erased, [0])

    def test_a_new_composition_replaces_the_old_one(self):
        self.echo.show("ㄨ")
        self.echo.show("ㄨㄛ")
        self.assertEqual(self.typed, ["ㄨ", "ㄨㄛ"])
        self.assertEqual(self.erased, [0, 1])
        self.assertEqual(self.echo.length, 2)

    def test_a_commit_replaces_the_composition(self):
        self.echo.show("ㄨㄛ")
        self.echo.commit("桌")
        self.assertEqual(self.typed, ["ㄨㄛ", "桌"])
        self.assertEqual(self.erased, [0, 2])
        self.assertEqual(self.echo.length, 0)

    def test_clearing_takes_the_composition_out(self):
        self.echo.show("ㄨㄛ")
        self.echo.clear()
        self.assertEqual(self.erased, [0, 2])
        self.assertEqual(self.echo.length, 0)

    def test_a_commit_after_a_commit_types_only_the_text(self):
        self.echo.commit("桌")
        self.echo.commit("椅")
        self.assertEqual(self.typed, ["桌", "椅"])
        self.assertEqual(self.erased, [0, 0])


if __name__ == "__main__":
    unittest.main()
