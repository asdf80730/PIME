# Copyright (C) 2026 Hong Jen Yee (PCMan) <pcman.tw@gmail.com>
#
# API design and architecture by Hong Jen Yee (PCMan).
# Implementation generated with AI assistance from Google Antigravity (Gemini 3.8 Flash).
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""Unit tests for CinTableBase."""

import concurrent.futures
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from cinbase import CinTableBase
from cinbase.cintablebase import TableHolder, TableLoadError


class _StubService:
    """The two fields ensure() crosses: cfg.selCinType and the cin slot."""

    class cfg:
        selCinType = 0

    def __init__(self):
        self.cin = None


class CinTableBaseTests(unittest.TestCase):
    def test_initial_state(self):
        """Verify initial attribute values and default properties."""
        tbl = CinTableBase()
        self.assertIsNone(tbl.future)
        self.assertFalse(tbl.loading)
        self.assertIsNone(tbl.cin)
        self.assertIsNone(tbl.wait(timeout=0.01))

    def test_future_lifecycle(self):
        """Verify dynamic loading and cin access through Future lifecycle."""
        tbl = CinTableBase()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        started = False

        def slow_task():
            nonlocal started
            started = True
            time.sleep(0.05)
            return "ready"

        fut = executor.submit(slow_task)
        tbl.future = fut

        self.assertIs(tbl.future, fut)
        self.assertTrue(tbl.loading)
        self.assertIsNone(tbl.cin)

        # wait() awaits completion
        res = tbl.wait(timeout=1.0)
        self.assertEqual(res, "ready")
        self.assertFalse(tbl.loading)
        self.assertEqual(tbl.cin, "ready")

        executor.shutdown(wait=False)

    def test_wait_timeout(self):
        """Verify wait() times out and raises TimeoutError when timeout expires."""
        tbl = CinTableBase()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        def very_slow_task():
            time.sleep(0.5)
            return "done"

        tbl.future = executor.submit(very_slow_task)
        with self.assertRaises(concurrent.futures.TimeoutError):
            tbl.wait(timeout=0.01)
        self.assertTrue(tbl.loading)

        executor.shutdown(wait=False)

    def test_wait_raises_task_exception(self):
        """Verify wait() and cin propagate exceptions raised inside the task."""
        tbl = CinTableBase()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        def failing_task():
            raise ValueError("Corrupt CIN table file")

        tbl.future = executor.submit(failing_task)
        with self.assertRaises(ValueError) as ctx:
            tbl.wait(timeout=1.0)
        self.assertIn("Corrupt CIN table file", str(ctx.exception))

        with self.assertRaises(ValueError):
            _ = tbl.cin

        executor.shutdown(wait=False)

    def test_no_setters(self):
        """Verify loading and cin properties cannot be assigned directly."""
        tbl = CinTableBase()
        with self.assertRaises(AttributeError):
            tbl.loading = True
        with self.assertRaises(AttributeError):
            tbl.cin = "custom"

    # The shared TableHolder: one class for the three table kinds, one
    # outcome per load, all crossed through ensure() only.

    def test_ensure_spawned_starts_one_loader(self):
        """ensure() spawns the one loader on a stale holder and reports
        SPAWNED; a second ensure() landing in flight does not double-spawn."""
        tbl = TableHolder("cin", ["table.json"])
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        service = _StubService()

        def task():
            time.sleep(0.05)
            return "table"

        class Loader:
            """The #1004 loader shape: start() schedules, sets curCinType
            and returns the Future, like LoadCinTable.start."""

            def __init__(self, cbTS, holder):
                self.cbTS = cbTS
                self.holder = holder

            def start(self):
                future = executor.submit(task)
                tbl.curCinType = service.cfg.selCinType
                return future

        self.assertEqual(TableHolder.SPAWNED, tbl.ensure(service, Loader))
        self.assertTrue(tbl.loading)
        self.assertEqual(TableHolder.LOADED, tbl.ensure(service, Loader))
        self.assertEqual(1, tbl.load_count)
        self.assertEqual("table", service.cin)
        executor.shutdown(wait=False)

    def test_ensure_loaded_adopts_the_present_table(self):
        """A holder whose table is already there joins and reports LOADED."""
        tbl = TableHolder("cin", ["table.json"])
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(lambda: "table")
        future.result(timeout=1)
        tbl.future = future
        tbl.curCinType = 0
        service = _StubService()

        def no_spawn(cbTS, holder):
            self.fail("ensure() spawned a loader the caller never asked for")

        self.assertEqual(TableHolder.LOADED, tbl.ensure(service, no_spawn))
        self.assertEqual("table", service.cin)
        executor.shutdown(wait=False)

    def test_ensure_failed_reports_no_table_without_raising(self):
        """A load whose json path is missing reads FAILED, never raises."""
        tbl = TableHolder("cin", ["missing.json"])
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        def load_missing():
            # the real missing-json shape: io.open raises inside the future
            with open(os.path.join(os.path.dirname(__file__), "missing.json")):
                pass

        future = executor.submit(load_missing)
        try:
            future.result(timeout=1)
        except FileNotFoundError:
            pass
        tbl.future = future
        tbl.curCinType = 0
        service = _StubService()

        def no_spawn(cbTS, holder):
            self.fail("ensure() spawned a loader the caller never asked for")

        self.assertEqual(TableHolder.FAILED, tbl.ensure(service, no_spawn))
        self.assertIsNone(tbl.cin)
        self.assertIsNone(service.cin)
        executor.shutdown(wait=False)

    def test_wait_until_ready_raises_on_failed_holder(self):
        """The asking seam raises TableLoadError naming the missing table."""
        tbl = TableHolder("cin", ["missing.json"])
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        def load_missing():
            with open(os.path.join(os.path.dirname(__file__), "missing.json")):
                pass

        future = executor.submit(load_missing)
        try:
            future.result(timeout=1)
        except FileNotFoundError:
            pass
        tbl.future = future
        tbl.curCinType = 0

        with self.assertRaises(TableLoadError) as ctx:
            tbl.wait_until_ready(timeout=1)
        self.assertIn("missing.json", str(ctx.exception))
        executor.shutdown(wait=False)

    def test_reset_is_the_test_seam(self):
        """reset() clears a settled holder; an unwaited loader blocks it."""
        tbl = TableHolder("cin", ["table.json"])
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(lambda: "table")
        future.result(timeout=1)
        tbl.future = future
        tbl.curCinType = 0
        tbl.load_count = 1

        tbl.reset()
        self.assertIsNone(tbl.future)
        self.assertFalse(tbl.loading)
        self.assertIsNone(tbl.cin)
        self.assertIsNone(tbl.curCinType)
        self.assertEqual(0, tbl.load_count)

        pending = concurrent.futures.Future()
        tbl.future = pending
        tbl.load_count = 1
        with self.assertRaises(TableLoadError):
            tbl.reset(timeout=0.05)
        self.assertIs(tbl.future, pending)
        self.assertEqual(1, tbl.load_count)
        pending.set_result("table")
        executor.shutdown(wait=False)


if __name__ == "__main__":
    unittest.main()
