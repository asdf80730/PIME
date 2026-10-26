import importlib
import importlib.util
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
PYTHON_DIR = os.path.join(ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

# `import cinbase` pulls in winsound and ctypes.windll at module scope. The
# smoke runner's shims stand in for them on Linux; the tests below never call
# a Win32 function.
import ime_smoke_runner  # noqa: E402 - located after ROOT is known
ime_smoke_runner.install_windows_shims()


@unittest.skipIf(ime_smoke_runner.under_wine(),
                 "Wine lacks propsys.dll.VariantToString, which importing cinbase reaches")
class CinbaseCandPerPageTests(unittest.TestCase):
    def setUp(self):
        import cinbase
        import cinbase.config
        self.config_mod = cinbase.config
        self.cinbase_mod = cinbase

    def test_sanitize_cand_per_page_empty_and_invalid(self):
        cfg = self.config_mod.CinBaseConfig
        for bad_val in ["", "0", 0, -1, "invalid", None]:
            cfg.candPerPage = bad_val
            cfg.candPerRow = bad_val
            cfg.fontSize = bad_val
            cfg.sanitize()
            self.assertEqual(cfg.candPerPage, 9, f"Failed for bad_val={bad_val!r}")
            self.assertEqual(cfg.candPerRow, 1, f"Failed for bad_val={bad_val!r}")
            self.assertEqual(cfg.fontSize, self.config_mod.DEF_FONT_SIZE)

    def test_sanitize_cand_per_page_valid_range(self):
        cfg = self.config_mod.CinBaseConfig
        cfg.candPerPage = 5
        cfg.candPerRow = 3
        cfg.sanitize()
        self.assertEqual(cfg.candPerPage, 5)
        self.assertEqual(cfg.candPerRow, 3)

        # Exceeds max range (10)
        cfg.candPerPage = 99
        cfg.sanitize()
        self.assertEqual(cfg.candPerPage, 9)

    def test_apply_config_sanitizes_attributes(self):
        from unittest.mock import MagicMock
        cinbase_inst = self.cinbase_mod.CinBase

        mock_cfg = MagicMock()
        mock_cfg.candPerPage = ""
        mock_cfg.candPerRow = ""
        mock_cfg.getVersion.return_value = (1.0, 0, 0, 0, 0, 0)

        ts = MagicMock()
        ts.cfg = mock_cfg
        ts.client.isUiLess = False

        cinbase_inst.applyConfig(ts)
        self.assertEqual(ts.candPerPage, 9)
        self.assertEqual(ts.candPerRow, 1)


if __name__ == "__main__":
    unittest.main()
