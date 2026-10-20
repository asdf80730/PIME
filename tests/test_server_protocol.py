"""Unit tests for the Python backend's stdin/stdout protocol loop.

The loop is pure Python: no Windows API is needed to exercise framing, client
session handling, error recovery, or reply serialization. Windows-only text
services are replaced with fakes.
"""

# Generated with assistance from DeepSeek V4.1 Flash.

import contextlib
import io
import json
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
PYTHON_DIR = os.path.join(ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

import server as server_module
from server import Client, Server

GUID = "{12345678-1234-1234-1234-123456789abc}"


class FakeService:
    def __init__(self, client, guid):
        self.client = client
        self.guid = guid
        self.currentReply = {}
        self.requests = []

    def handleRequest(self, msg):
        if msg.get("method") == "boom":
            raise RuntimeError("service failure")
        self.requests.append(msg)
        self.currentReply = {}
        return {
            "success": True,
            "seqNum": msg.get("seqNum", 0),
            "return": msg.get("echo"),
        }


class FakeServiceManager:
    def __init__(self):
        self.created = []

    def createService(self, client, guid):
        if guid == "{00000000-0000-0000-0000-000000000000}":
            return None
        service = FakeService(client, guid)
        self.created.append(service)
        return service


def make_server():
    server = Server.__new__(Server)
    server.clients = {}
    server.serviceMgr = FakeServiceManager()
    return server


def run_lines(server, lines):
    """Runs Server.run() over a fixed line sequence and captures both streams."""
    stdout = io.StringIO()
    stderr = io.StringIO()
    with mock.patch("builtins.input", side_effect=list(lines) + [EOFError()]), \
         contextlib.redirect_stdout(stdout), \
         contextlib.redirect_stderr(stderr), \
         mock.patch.object(server_module, "append_error_log", lambda message: None):
        server.run()
    return stdout.getvalue(), stderr.getvalue()


def frame(client_id, payload):
    return f"{client_id}|{json.dumps(payload)}"


def replies(output):
    result = []
    for line in output.splitlines():
        if line.startswith("PIME_MSG|"):
            _, client_id, payload = line.split("|", maxsplit=2)
            result.append((client_id, json.loads(payload)))
    return result


def init_payload(guid=GUID, seq_num=0):
    return {
        "method": "init",
        "id": guid,
        "seqNum": seq_num,
        "isWindows8Above": True,
        "isMetroApp": False,
        "isUiLess": False,
        "isConsole": False,
    }


class ServerProtocolTests(unittest.TestCase):
    def test_init_then_forward_request(self):
        server = make_server()
        output, _ = run_lines(server, [
            frame("c1", init_payload()),
            frame("c1", {"method": "filterKeyDown", "seqNum": 7, "echo": "ok"}),
        ])

        self.assertEqual(replies(output), [
            ("c1", {"success": True, "seqNum": 0}),
            ("c1", {"success": True, "seqNum": 7, "return": "ok"}),
        ])
        self.assertIsNotNone(server.clients["c1"].service)

    def test_request_before_init_fails_without_killing_the_loop(self):
        server = make_server()
        output, _ = run_lines(server, [
            frame("c1", {"method": "filterKeyDown", "seqNum": 5}),
            frame("c1", {"method": "close", "seqNum": 6}),
        ])

        self.assertEqual(replies(output), [
            ("c1", {"success": False, "seqNum": 5}),
            ("c1", {"success": True, "seqNum": 6}),
        ])

    def test_init_with_unknown_guid_reports_failure(self):
        server = make_server()
        output, _ = run_lines(server, [
            frame("c1", init_payload(guid="{00000000-0000-0000-0000-000000000000}")),
        ])

        self.assertEqual(replies(output), [("c1", {"success": False, "seqNum": 0})])
        self.assertIsNone(server.clients["c1"].service)

    def test_malformed_frame_is_ignored(self):
        server = make_server()
        output, stderr = run_lines(server, [
            "this is not a frame",
            frame("c1", {"method": "close"}),
        ])

        self.assertEqual(replies(output), [("c1", {"success": True})])
        self.assertIn("malformed request", stderr)

    def test_invalid_json_replies_with_failure_and_keeps_serving(self):
        server = make_server()
        output, _ = run_lines(server, [
            "c1|{not json",
            frame("c1", {"method": "close", "seqNum": 9}),
        ])

        self.assertEqual(replies(output), [
            ("c1", {"success": False}),
            ("c1", {"success": True, "seqNum": 9}),
        ])

    def test_service_exception_is_reported_and_loop_continues(self):
        server = make_server()
        output, _ = run_lines(server, [
            frame("c1", init_payload()),
            frame("c1", {"method": "boom", "seqNum": 4}),
            frame("c1", {"method": "filterKeyDown", "seqNum": 5, "echo": "still-alive"}),
        ])

        self.assertEqual(replies(output), [
            ("c1", {"success": True, "seqNum": 0}),
            ("c1", {"success": False, "seqNum": 4}),
            ("c1", {"success": True, "seqNum": 5, "return": "still-alive"}),
        ])
        self.assertEqual(server.clients["c1"].service.currentReply, {})

    def test_close_removes_the_client_session(self):
        server = make_server()
        run_lines(server, [
            frame("c1", init_payload()),
            frame("c1", {"method": "close", "seqNum": 3}),
        ])

        self.assertNotIn("c1", server.clients)

    def test_clients_are_isolated(self):
        server = make_server()
        output, _ = run_lines(server, [
            frame("c1", init_payload()),
            frame("c2", init_payload()),
            frame("c1", {"method": "filterKeyDown", "seqNum": 1, "echo": "one"}),
            frame("c2", {"method": "filterKeyDown", "seqNum": 2, "echo": "two"}),
        ])

        self.assertEqual([client_id for client_id, _ in replies(output)], ["c1", "c2", "c1", "c2"])
        self.assertEqual(len(server.serviceMgr.created), 2)
        self.assertIsNot(server.clients["c1"].service, server.clients["c2"].service)

    def test_unicode_reply_is_written_as_utf8_without_ascii_escapes(self):
        server = make_server()
        output, _ = run_lines(server, [
            frame("c1", init_payload()),
            frame("c1", {"method": "filterKeyDown", "seqNum": 1, "echo": "中文"}),
        ])

        self.assertIn("中文", output)
        self.assertNotIn("\\u4e2d", output)
        self.assertEqual(replies(output)[1][1]["return"], "中文")

    def test_init_stores_client_flags(self):
        server = make_server()
        payload = init_payload()
        payload.update({"isWindows8Above": False, "isMetroApp": True, "isUiLess": True, "isConsole": True})
        run_lines(server, [frame("c1", payload)])

        client = server.clients["c1"]
        self.assertFalse(client.isWindows8Above)
        self.assertTrue(client.isMetroApp)
        self.assertTrue(client.isUiLess)
        self.assertTrue(client.isConsole)

    def test_client_dispatch_uses_manager_and_sequence_number_defaults(self):
        server = make_server()
        client = Client(server)

        init_reply = client.handleRequest(init_payload())
        self.assertEqual(init_reply, {"success": True, "seqNum": 0})

        service_reply = client.handleRequest({"method": "filterKeyDown", "echo": "x"})
        self.assertEqual(service_reply, {"success": True, "seqNum": 0, "return": "x"})


if __name__ == "__main__":
    unittest.main()
