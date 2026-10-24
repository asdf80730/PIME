"""Smoke coverage for the Python input methods on Linux.

Each service is instantiated with Windows API shims, activated, and fed key
events through its real subclass. This catches load-time and dispatch crashes
without a Windows desktop. Services whose native library is unavailable are
reported as skipped rather than failed.
"""

# Generated with assistance from DeepSeek V4.1 Flash.

import ctypes
import errno
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
PYTHON_DIR = os.path.join(ROOT, "python")
RUNNER = os.path.join(ROOT, "tests", "ime_smoke_runner.py")

# The runner is a script next to this test, not part of the product package.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ime_smoke_runner  # noqa: E402 - located after ROOT is known

# Every service that must run: the cinbase family plus the standalone meow
# service. chewing/rime/braille are discovered too, but their native bindings
# may not match the system libraries.
EXPECTED_SERVICES = {
    "chearray", "checj", "chedayi", "cheeng", "cheez", "cheliu",
    "chephonetic", "chepinyin", "chesimplex", "meow",
}


def opencc_available():
    try:
        ctypes.CDLL("libopencc.so")
        return True
    except OSError:
        return False


@unittest.skipIf(sys.platform == "win32",
                 "the shims exist for Linux; run chewing_test.py on Windows instead")
@unittest.skipUnless(opencc_available(),
                     "libopencc.so not installed (Debian: apt install libopencc-dev)")
class InputMethodSmokeTests(unittest.TestCase):
    def test_services_activate_and_dispatch_key_events(self):
        with tempfile.TemporaryDirectory(prefix="pime-ime-smoke-") as work_dir:
            results_file = os.path.join(work_dir, "results.json")
            env = os.environ.copy()
            env["PYTHONPATH"] = PYTHON_DIR + (
                os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
            )
            env["PYTHONIOENCODING"] = "utf-8"

            completed = subprocess.run(
                [sys.executable, RUNNER, results_file],
                cwd=work_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=180,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with open(results_file, encoding="utf-8") as results_handle:
                results = {row["service"]: row for row in json.load(results_handle)}

        self.assertTrue(results, "runner reported no services")

        errors = {name: row["detail"] for name, row in results.items() if row["status"] == "error"}
        self.assertEqual(errors, {})

        exercised = {name for name, row in results.items() if row["status"] == "ok"}
        self.assertTrue(EXPECTED_SERVICES <= exercised,
                        f"not exercised: {sorted(EXPECTED_SERVICES - exercised)}")


class ImportRetryTests(unittest.TestCase):
    """The runner retries only the importer's own EBADF, never a real failure."""

    def test_ebadf_from_the_importer_is_retried(self):
        calls = []

        def import_module(name):
            calls.append(name)
            if len(calls) == 1:
                raise OSError(errno.EBADF, "Bad file descriptor", name)
            return object()

        with mock.patch.object(ime_smoke_runner.importlib, "import_module", import_module):
            module = ime_smoke_runner.import_service("input_methods.meow.ime_meow")
        self.assertIsNotNone(module)
        self.assertEqual(calls, ["input_methods.meow.ime_meow"] * 2)

    def test_a_non_ebadf_oserror_is_not_retried(self):
        calls = []

        def import_module(name):
            calls.append(name)
            raise OSError(errno.EACCES, "Permission denied", name)

        with mock.patch.object(ime_smoke_runner.importlib, "import_module", import_module):
            with self.assertRaises(OSError):
                ime_smoke_runner.import_service("input_methods.meow.ime_meow")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
