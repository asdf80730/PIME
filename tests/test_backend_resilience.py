import contextlib
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
PYTHON_DIR = os.path.join(ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)


class CinCountTests(unittest.TestCase):
    def make_cin(self, temp_dir, count_data):
        spec = importlib.util.spec_from_file_location("cin_module_for_test", os.path.join(PYTHON_DIR, "cinbase", "cin.py"))
        cin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cin_module)
        Cin = cin_module.Cin

        cin = Cin.__new__(Cin)
        cin.keynames = {}
        cin.cincount = {}
        cin.chardefs = {}
        cin.privateuse = {}
        cin.dupchardefs = {}
        cin._count_dirty = False
        cin._last_count_save_time = 0.0
        cin.getCountFile = lambda name="cincount.json": os.path.join(temp_dir, name)
        with open(cin.getCountFile(), "w", encoding="utf-8") as f:
            json.dump(count_data, f)
        return cin

    def test_load_count_file_ignores_malformed_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cin = self.make_cin(temp_dir, {
                "abc": {"A": 3},
                "bad": ["not", "a", "dict"],
                "also_bad": 2,
            })

            cin.loadCountFile()

            self.assertEqual(cin.cincount, {
                "abc": {"A": {"count": 3, "last": 0, "prev": {}}}
            })

    def test_add_and_sort_count_tolerate_bad_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cin = self.make_cin(temp_dir, {})
            cin.cincount = {"abc": "bad"}

            cin.addCount("abc", "A")
            cin.addCount(None, "B")

            self.assertEqual(cin.cincount["abc"]["A"]["count"], 1)
            self.assertEqual(cin.cincount["abc"]["A"]["prev"], {})
            self.assertEqual(cin.sortByCount("abc", ["B", "A"]), ["A", "B"])
            self.assertEqual(cin.sortByCount("missing", ["B", "A"]), ["B", "A"])

    def test_recent_and_context_scores_can_be_disabled_independently(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cin = self.make_cin(temp_dir, {
                "abc": {
                    "A": {"count": 1, "last": 100.0, "prev": {"文": 4}},
                    "B": {"count": 2, "last": 200.0, "prev": {}},
                }
            })
            cin.loadCountFile()

            with mock.patch("time.time", return_value=200.0):
                self.assertEqual(cin.sortByCount("abc", ["B", "A"], "文"), ["A", "B"])
                self.assertEqual(cin.sortByCount("abc", ["B", "A"], "文", useContext=False), ["B", "A"])

    def test_context_counts_are_capped(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cin = self.make_cin(temp_dir, {})

            for i in range(40):
                cin.addCount("abc", "A", "prev{0:02d}".format(i))

            prev = cin.cincount["abc"]["A"]["prev"]
            self.assertEqual(len(prev), cin.MAX_CONTEXT_ENTRIES)
            self.assertIn("prev39", prev)

    def test_save_count_file_is_throttled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cin = self.make_cin(temp_dir, {})
            cin.cincount = {"abc": {"A": {"count": 1, "last": 0, "prev": {}}}}
            cin._count_dirty = True
            cin._last_count_save_time = 100.0

            with mock.patch("time.time", return_value=110.0):
                cin.saveCountFile()
            with open(cin.getCountFile(), "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), {})

            with mock.patch("time.time", return_value=111.0):
                cin.saveCountFile(force=True)
            with open(cin.getCountFile(), "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), cin.cincount)


class ServerResilienceTests(unittest.TestCase):
    def import_server(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return importlib.import_module("server")

    def input_then_eof(self, lines):
        iterator = iter(lines)

        def fake_input():
            try:
                return next(iterator)
            except StopIteration:
                raise EOFError

        return fake_input

    def test_server_continues_after_client_exception(self):
        server_mod = self.import_server()
        server = server_mod.Server(PYTHON_DIR)

        class FailingClient:
            service = None

            def handleRequest(self, msg):
                raise RuntimeError("boom")

        server.clients["client-1"] = FailingClient()

        with mock.patch("builtins.input", side_effect=self.input_then_eof(['client-1|{"method":"onKeyDown"}'])), \
                mock.patch.object(server_mod, "append_error_log"), \
                contextlib.redirect_stdout(io.StringIO()) as stdout, \
                contextlib.redirect_stderr(io.StringIO()):
            server.run()

        replies = [line for line in stdout.getvalue().splitlines() if line.startswith("PIME_MSG|client-1|")]
        self.assertEqual(len(replies), 1)
        self.assertEqual(json.loads(replies[0][len("PIME_MSG|client-1|"):]), {"success": False})

    def test_server_ignores_malformed_request_line(self):
        server_mod = self.import_server()
        server = server_mod.Server(PYTHON_DIR)

        with mock.patch("builtins.input", side_effect=self.input_then_eof(["malformed-request"])), \
                mock.patch.object(server_mod, "append_error_log") as append_error_log, \
                contextlib.redirect_stdout(io.StringIO()) as stdout, \
                contextlib.redirect_stderr(io.StringIO()):
            server.run()

        self.assertEqual(stdout.getvalue(), "")
        append_error_log.assert_called_once()

    # --- bounded retention on the real start path (#445) -----------------
    def test_protocol_errors_leave_a_bounded_log(self):
        server_mod = self.import_server()
        server = server_mod.Server(PYTHON_DIR)
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": temp_dir}), \
                    mock.patch("builtins.input", side_effect=self.input_then_eof(
                        ["malformed-%d" % index for index in range(6)])), \
                    contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                server.run()

            log_dir = os.path.join(temp_dir, "PIME", "Logs")
            files = sorted(os.listdir(log_dir))
            # Six short lines stay far under the 1 MB rollover, so the chain is
            # the single active file: the cap in LOG_BACKUP_COUNT only ever
            # shows up once a rollover has happened.
            self.assertEqual(["python_backend.log"], files)
            with open(os.path.join(log_dir, "python_backend.log"),
                      encoding="utf-8") as handle:
                self.assertTrue(handle.read().startswith("ERROR: malformed request"))

    def test_backend_start_prunes_the_rime_directories_once(self):
        rime_librime = self.load_rime_bindings()
        if rime_librime is None:
            self.skipTest("librime bindings are not available")
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, "logs")
            os.makedirs(log_dir)
            for index in range(rime_librime.RIME_LOG_MAX_FILES + 4):
                with open(os.path.join(log_dir, "Rime.PIME.log.INFO.%d" % index),
                          "w", encoding="utf-8") as handle:
                    handle.write("x")
            before = len(os.listdir(log_dir))

            calls = []
            shared_dir = os.path.join(PYTHON_DIR, "input_methods", "rime", "data")
            # The guard is what the two calls below are for, so start from a
            # known side of it: other modules' rimeInit may have run first.
            started_before = rime_librime._rime_started
            rime_librime._rime_started = False
            with mock.patch.object(rime_librime, "prune_rime_user_data",
                                   side_effect=lambda *a, **kw: calls.append(1)) as prune, \
                    mock.patch.object(rime_librime, "rime",
                                      mock.MagicMock()) as api:
                rime_librime.rimeInit(datadir=shared_dir, userdir=temp_dir,
                                      fullcheck=False, appname="PIME", appver="0.01")
                rime_librime.rimeInit(datadir=shared_dir, userdir=temp_dir,
                                      fullcheck=False, appname="PIME", appver="0.01")

            # One retention pass per start call, and the engine keeps running.
            self.assertEqual(len(calls), 2)
            prune.assert_called()
            # The engine itself starts once: the _rime_started guard is what
            # keeps the second call from re-setting up, and a repeated
            # RimeSetup aborts on glog's "Could not create logging file".
            self.assertEqual(1, api.setup.call_count,
                             "the second rimeInit re-set up the engine")
            self.assertEqual(1, api.initialize.call_count,
                             "the second rimeInit re-initialized the engine")
            self.assertTrue(rime_librime._rime_started)
            # Leave the module-level guard as this process found it: a later
            # module's rimeInit has to make the real RimeSetup, and the flag is
            # the only thing telling it that it already did.
            rime_librime._rime_started = started_before
            self.assertEqual(before, rime_librime.RIME_LOG_MAX_FILES + 4)
            # The real pass is idempotent, so a second start changes nothing.
            report = rime_librime.prune_rime_user_data(
                temp_dir, app_name="PIME", log_dir=log_dir)
            self.assertEqual(report["log_before"], before)
            self.assertEqual(report["log_after"], rime_librime.RIME_LOG_MAX_FILES)
            again = rime_librime.prune_rime_user_data(
                temp_dir, app_name="PIME", log_dir=log_dir)
            self.assertEqual(again["log_before"], rime_librime.RIME_LOG_MAX_FILES)
            self.assertEqual(again["log_after"], rime_librime.RIME_LOG_MAX_FILES)

    def load_rime_bindings(self):
        try:
            return importlib.import_module("input_methods.rime.librime")
        except Exception:
            return None


if __name__ == "__main__":
    unittest.main()
