"""Smoke coverage for the Python input methods on Linux.

Each service is instantiated with Windows API shims, activated, and fed key
events through its real subclass. This catches load-time and dispatch crashes
without a Windows desktop. Services whose native library is unavailable are
reported as skipped rather than failed.
"""

# Generated with assistance from DeepSeek V4.1 Flash.

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
PYTHON_DIR = os.path.join(ROOT, "python")
RUNNER = os.path.join(ROOT, "tests", "ime_smoke_runner.py")

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


if __name__ == "__main__":
    unittest.main()
