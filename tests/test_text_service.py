"""Unit tests for the pure-Python parts of textService.py.

TextService.handleRequest is the dispatch layer every Python input method
inherits, and KeyEvent is pure bit/character logic. Neither needs Windows.
"""

# Generated with assistance from DeepSeek V4.1 Flash.

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
PYTHON_DIR = os.path.join(ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

import textService as ts


def make_key_event(**overrides):
    msg = {
        "charCode": 0,
        "keyCode": 0,
        "repeatCount": 1,
        "scanCode": 0,
        "isExtended": False,
        "keyStates": [0] * 256,
    }
    msg.update(overrides)
    return ts.KeyEvent(msg)


class KeyEventTests(unittest.TestCase):
    def test_fields_are_copied_from_the_request(self):
        key_states = [0] * 256
        event = make_key_event(charCode=65, keyCode=66, repeatCount=2, scanCode=3,
                               isExtended=True, keyStates=key_states)
        self.assertEqual((event.charCode, event.keyCode, event.repeatCount, event.scanCode),
                         (65, 66, 2, 3))
        self.assertTrue(event.isExtended)

    def test_is_key_down_uses_the_high_bit(self):
        key_states = [0] * 256
        key_states[65] = 0x80
        key_states[66] = 0x7F
        event = make_key_event(keyStates=key_states)
        self.assertTrue(event.isKeyDown(65))
        self.assertFalse(event.isKeyDown(66))

    def test_is_key_toggled_uses_the_low_bit(self):
        key_states = [0] * 256
        key_states[20] = 0x01
        key_states[21] = 0x80
        event = make_key_event(keyStates=key_states)
        self.assertTrue(event.isKeyToggled(20))
        self.assertFalse(event.isKeyToggled(21))

    def test_printable_character_boundaries(self):
        cases = [(0, False), (0x1F, False), (0x20, True), (0x41, True), (0x7E, True), (0x7F, False)]
        for char_code, expected in cases:
            with self.subTest(charCode=char_code):
                self.assertEqual(make_key_event(charCode=char_code).isPrintableChar(), expected)

    def test_symbol_keys(self):
        for char_code in (0x3D, 0x5B, 0x5C, 0x5D, 0x27):
            with self.subTest(charCode=char_code):
                self.assertTrue(make_key_event(charCode=char_code).isSymbols())
        for char_code in (0x41, 0x20, 0x30):
            with self.subTest(charCode=char_code):
                self.assertFalse(make_key_event(charCode=char_code).isSymbols())


class RecordingService(ts.TextService):
    def __init__(self):
        super().__init__(client=None)
        self.calls = []
        self.key_down_result = True
        self.key_up_result = False

    def checkConfigChange(self):
        self.calls.append(("checkConfigChange",))

    def updateStatus(self, msg):
        self.calls.append(("updateStatus", msg.get("method")))

    def onActivate(self):
        self.calls.append(("onActivate",))

    def onDeactivate(self):
        self.calls.append(("onDeactivate",))

    def filterKeyDown(self, key_event):
        self.calls.append(("filterKeyDown", key_event.charCode))
        return self.key_down_result

    def onKeyDown(self, key_event):
        self.calls.append(("onKeyDown", key_event.charCode))

    def filterKeyUp(self, key_event):
        self.calls.append(("filterKeyUp", key_event.charCode))
        return self.key_up_result

    def onKeyUp(self, key_event):
        self.calls.append(("onKeyUp", key_event.charCode))

    def onPreservedKey(self, guid):
        self.calls.append(("onPreservedKey", guid))
        return True

    def onCommand(self, command_id, command_type):
        self.calls.append(("onCommand", command_id, command_type))

    def onMenu(self, button_id):
        self.calls.append(("onMenu", button_id))
        return None

    def onCompartmentChanged(self, guid):
        self.calls.append(("onCompartmentChanged", guid))

    def onKeyboardStatusChanged(self, opened):
        self.calls.append(("onKeyboardStatusChanged", opened))

    def onCompositionTerminated(self, forced):
        super().onCompositionTerminated(forced)
        self.calls.append(("onCompositionTerminated", forced))


def key_request(method, **overrides):
    request = {
        "method": method,
        "seqNum": 11,
        "charCode": 65,
        "keyCode": 65,
        "repeatCount": 1,
        "scanCode": 30,
        "isExtended": False,
        "keyStates": [0] * 256,
    }
    request.update(overrides)
    return request


class TextServiceDispatchTests(unittest.TestCase):
    def setUp(self):
        self.service = RecordingService()

    def call(self, request):
        return self.service.handleRequest(request)

    def test_key_events_dispatch_to_the_matching_hook(self):
        self.assertEqual(self.call(key_request("filterKeyDown")),
                         {"success": True, "seqNum": 11, "return": True})
        self.assertIn(("filterKeyDown", 65), self.service.calls)

        reply = self.call(key_request("onKeyDown"))
        self.assertNotIn("return", reply)
        self.assertIn(("onKeyDown", 65), self.service.calls)

        self.assertEqual(self.call(key_request("filterKeyUp")),
                         {"success": True, "seqNum": 11, "return": False})
        self.assertIn(("filterKeyUp", 65), self.service.calls)

        self.call(key_request("onKeyUp"))
        self.assertIn(("onKeyUp", 65), self.service.calls)

    def test_guid_arguments_are_lowercased(self):
        self.call({"method": "onPreservedKey", "guid": "{ABC}", "seqNum": 1})
        self.call({"method": "onCompartmentChanged", "guid": "{DEF}", "seqNum": 2})
        self.assertIn(("onPreservedKey", "{abc}"), self.service.calls)
        self.assertIn(("onCompartmentChanged", "{def}"), self.service.calls)

    def test_command_menu_and_status_hooks(self):
        self.call({"method": "onCommand", "id": 3, "type": 1, "seqNum": 1})
        self.assertIn(("onCommand", 3, 1), self.service.calls)

        reply = self.call({"method": "onMenu", "id": 4, "seqNum": 2})
        self.assertEqual(reply, {"success": True, "seqNum": 2})
        self.assertIn(("onMenu", 4), self.service.calls)

        self.call({"method": "onKeyboardStatusChanged", "opened": True, "seqNum": 3})
        self.assertIn(("onKeyboardStatusChanged", True), self.service.calls)

    def test_activate_and_deactivate_update_state(self):
        reply = self.call({"method": "onActivate", "isKeyboardOpen": True, "seqNum": 1})
        self.assertEqual(reply, {"success": True, "seqNum": 1})
        self.assertTrue(self.service.isActivated)
        self.assertTrue(self.service.keyboardOpen)

        self.call({"method": "onDeactivate", "seqNum": 2})
        self.assertFalse(self.service.isActivated)

    def test_unknown_method_fails_but_echoes_sequence_number(self):
        reply = self.call({"method": "noSuchMethod", "seqNum": 42})
        self.assertEqual(reply, {"success": False, "seqNum": 42})

    def test_missing_sequence_number_defaults_to_zero(self):
        reply = self.call({"method": "noSuchMethod"})
        self.assertEqual(reply["seqNum"], 0)

    def test_reply_fields_accumulate_then_reset(self):
        def key_down(key_event):
            self.service.setCommitString("x")
            self.service.setCandidateList(["a", "b"])
            return False

        self.service.filterKeyDown = key_down
        reply = self.call(key_request("filterKeyDown"))
        self.assertEqual(reply["commitString"], "x")
        self.assertEqual(reply["candidateList"], ["a", "b"])
        self.assertEqual(reply["return"], False)

        next_reply = self.call(key_request("onKeyDown"))
        self.assertNotIn("commitString", next_reply)
        self.assertNotIn("candidateList", next_reply)

    def test_composition_termination_clears_state(self):
        self.service.compositionString = "abc"
        self.service.commitString = "x"
        reply = self.call({"method": "onCompositionTerminated", "forced": True, "seqNum": 5})

        self.assertEqual(reply, {"success": True, "seqNum": 5})
        self.assertEqual(self.service.compositionString, "")
        self.assertEqual(self.service.commitString, "")
        self.assertIn(("onCompositionTerminated", True), self.service.calls)

    def test_is_composing(self):
        self.assertFalse(self.service.isComposing())
        self.service.compositionString = "a"
        self.assertTrue(self.service.isComposing())
        self.service.compositionString = ""
        self.service.showCandidates = True
        self.assertTrue(self.service.isComposing())

    def test_reply_builders(self):
        self.service.addButton(1, text="A")
        self.service.changeButton(1, text="B")
        self.service.removeButton(2)
        self.service.addPreservedKey(65, 4, "{GUID}")
        self.service.removePreservedKey("{GUID}")
        self.service.setCompositionString("中")
        self.service.setCompositionCursor(1)
        self.service.setCommitString("文")
        self.service.setCandidateCursor(0)
        self.service.setShowCandidates(True)
        self.service.setSelKeys("1234")
        self.service.setKeyboardOpen(True)
        self.service.customizeUI(candPerRow=5)
        self.service.showMessage("hi", 2)
        self.service.hideMessage()

        reply = self.service.currentReply
        self.assertEqual(reply["addButton"], [{"text": "A", "id": 1}])
        self.assertEqual(reply["changeButton"], [{"text": "B", "id": 1}])
        self.assertEqual(reply["removeButton"], [2])
        self.assertEqual(reply["addPreservedKey"], [{"keyCode": 65, "modifiers": 4, "guid": "{guid}"}])
        self.assertEqual(reply["removePreservedKey"], ["{guid}"])
        self.assertEqual(reply["compositionString"], "中")
        self.assertEqual(reply["compositionCursor"], 1)
        self.assertEqual(reply["commitString"], "文")
        self.assertEqual(reply["candidateCursor"], 0)
        self.assertTrue(reply["showCandidates"])
        self.assertEqual(reply["setSelKeys"], "1234")
        self.assertTrue(reply["openKeyboard"])
        self.assertEqual(reply["customizeUI"], {"candPerRow": 5})
        self.assertEqual(reply["showMessage"], {"message": "hi", "duration": 2})
        self.assertTrue(reply["hideMessage"])
        self.assertEqual(self.service.compositionString, "中")
        self.assertEqual(self.service.commitString, "文")


if __name__ == "__main__":
    unittest.main()
