"""Unit tests for the pure-Python parts of the PIME key bridge.

The key event is the shape the C++ client sends to the backend, and the
composition echo is the bookkeeping that keeps the composition visible in the
control being typed into. Neither needs Windows.
"""

# Generated with assistance from omp (MiniMax-M3.1-Flash).

import os
import sys
import time
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
PYTHON_DIR = os.path.join(ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

from keybridge.echo import CompositionEcho, EchoWriter
from keybridge.keyevent import KeyEvent, Swallowed
from keybridge.mode import (CHINESE, ENGLISH, is_toggle, mode_command_id,
                            mode_from_reply)


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


class EchoWriterTest(unittest.TestCase):
    """The composition, typed into the control by the writer thread."""

    def setUp(self):
        self.typed = []
        self.erased = []
        self.writer = EchoWriter(self.typed.append, self.erased.append)

    def _wait_for(self, count):
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if len(self.typed) + len(self.erased) >= count:
                return
            time.sleep(0.01)

    def test_the_composition_is_typed_into_the_control(self):
        self.writer.show("ㄨ")
        self._wait_for(1)
        self.assertEqual(self.typed, ["ㄨ"])

    def test_the_commands_keep_their_order(self):
        self.writer.show("ㄨ")
        self.writer.commit("桌")
        self._wait_for(2)
        self.assertEqual(self.typed, ["ㄨ", "桌"])
        self.assertEqual(self.erased, [0, 1])

    def test_a_cleared_composition_leaves_nothing_behind(self):
        self.writer.show("ㄨ")
        self.writer.clear()
        self._wait_for(2)
        self.assertEqual(self.erased, [0, 1])
        self.assertEqual(self.typed, ["ㄨ"])


class SwallowedTest(unittest.TestCase):
    """The presses the bridge took, and their releases."""

    def setUp(self):
        self.swallowed = Swallowed()

    def test_a_release_of_a_key_the_bridge_took_is_taken_too(self):
        self.swallowed.take(0x41)
        self.assertTrue(self.swallowed.release(0x41))

    def test_a_release_of_a_key_the_application_had_is_not_taken(self):
        self.assertFalse(self.swallowed.release(0x41))

    def test_a_press_is_taken_once(self):
        self.swallowed.take(0x41)
        self.assertTrue(self.swallowed.release(0x41))
        self.assertFalse(self.swallowed.release(0x41))

    def test_the_keys_are_told_apart(self):
        self.swallowed.take(0x41)
        self.assertFalse(self.swallowed.release(0x42))
        self.assertTrue(self.swallowed.release(0x41))

    def test_a_lost_focus_forgets_the_presses(self):
        self.swallowed.take(0x41)
        self.swallowed.clear()
        self.assertFalse(self.swallowed.release(0x41))


class ModeTest(unittest.TestCase):
    """The switch between the input languages, and the backend's answer."""

    def test_ctrl_space_is_the_toggle(self):
        states = [0] * 256
        states[0x11] = 0x80  # the control key is down
        self.assertTrue(is_toggle(KeyEvent(0x20, 0, False, False, 0x20, states)))

    def test_the_right_control_key_toggles_too(self):
        states = [0] * 256
        states[0xA2] = 0x80
        self.assertTrue(is_toggle(KeyEvent(0x20, 0, False, False, 0x20, states)))

    def test_space_without_the_control_key_is_not_the_toggle(self):
        self.assertFalse(is_toggle(KeyEvent(0x20, 0, False, False, 0x20,
                                             [0] * 256)))

    def test_another_key_with_the_control_key_is_not_the_toggle(self):
        states = [0] * 256
        states[0x11] = 0x80
        self.assertFalse(is_toggle(KeyEvent(0x41, 0, False, False, 0x41, states)))

    def test_the_release_of_the_space_is_not_the_toggle(self):
        states = [0] * 256
        states[0x11] = 0x80
        self.assertFalse(is_toggle(KeyEvent(0x20, 0, False, True, 0, states)))

    def test_the_mode_command_comes_from_the_backend_s_own_buttons(self):
        reply = {"addButton": [{"id": "windows-mode-icon", "commandId": 4}]}
        self.assertEqual(mode_command_id(reply), 4)

    def test_a_backend_without_a_mode_button_has_no_command(self):
        reply = {"addButton": [{"id": "switch-lang", "commandId": 1}]}
        self.assertIsNone(mode_command_id(reply))
        self.assertIsNone(mode_command_id({}))

    def test_the_icon_of_the_button_says_which_mode_the_backend_is_in(self):
        reply = {"changeButton": [{"id": "windows-mode-icon",
                                   "icon": "C:\\icons\\eng.ico"}]}
        self.assertEqual(mode_from_reply(reply), ENGLISH)

    def test_the_chinese_icon_says_chinese(self):
        reply = {"changeButton": [{"id": "windows-mode-icon",
                                   "icon": "C:\\icons\\simC.ico"}]}
        self.assertEqual(mode_from_reply(reply), CHINESE)

    def test_caps_lock_is_still_chinese(self):
        reply = {"changeButton": [{"id": "windows-mode-icon",
                                   "icon": "C:\\icons\\capsEng.ico"}]}
        self.assertEqual(mode_from_reply(reply), CHINESE)

    def test_a_reply_without_an_icon_names_no_mode(self):
        self.assertIsNone(mode_from_reply({}))
        self.assertIsNone(mode_from_reply(
            {"changeButton": [{"id": "windows-mode-icon"}]}))


if __name__ == "__main__":
    unittest.main()
