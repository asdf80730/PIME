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

"""Base class and shared holder for CIN table state containers.

One holder concept for the whole cinbase family: ``CinTableBase`` keeps the
single ``future`` slot as the only state, and ``TableHolder`` deepens it with
the load policy — ``ensure``/``wait_until_ready``/``reset`` — that every
cinbase-family Service crosses. The 筆畫 module
``python/input_methods/chebihua/table_loaders.py`` instantiates this same
class for its three 碼表 (docs/adr/0003-table-load-policy-lives-with-the-service.md).
"""

import concurrent.futures
import threading
import time
from typing import Optional


class CinTableBase:
    """Base class for CIN table state containers.

    Encapsulates table loading state (cin, loading) and provides
    asynchronous Future-backed synchronization, dynamic loading state,
    and non-blocking table access.
    """

    def __init__(self):
        self.future = None

    @property
    def loading(self):
        """Returns True if a background loading task is currently in progress."""
        if self.future is not None:
            return not self.future.done()
        return False

    @property
    def cin(self):
        """Returns the loaded table instance if ready, or None if still loading."""
        if self.future is not None and self.future.done():
            return self.future.result()
        return None

    def wait(self, timeout: Optional[float] = None):
        """Waits for background loading to complete and returns the table object.

        Args:
            timeout: Maximum seconds to wait. None means wait indefinitely.

        Returns:
            The loaded table instance, or None if no loading task was scheduled.
        """
        if self.future is not None:
            return self.future.result(timeout=timeout)
        return None


class TableLoadError(RuntimeError):
    """A table did not become usable."""


class TableHolder(CinTableBase):
    """One table shared by every instance of the Service, plus the policy
    that fills it.

    The field names below are not ours to rename: cinbase reads them through
    the objects handed to filterKeyDown/onKeyDown/checkConfigChange
    (python/cinbase/__init__.py:359, 505, 3317-3353). ``future`` is the single
    truth, exactly as in ``CinTableBase`` above; ``loading``, ``cin`` and
    ``wait`` are derived from it here too, so nothing has to remember to clear
    a flag. ``kind`` names the table kind (``"cin"``, ``"rcin"`` or
    ``"hcin"``) and ``files`` lists the JSON file names that kind can hold,
    in ``selCinType`` order — both are data, not per-kind subclasses.
    """

    SPAWNED = "spawned"  # we started the one loader; it writes service.cin itself
    LOADED = "loaded"    # the table was there already, or the join brought it
    FAILED = "failed"    # the join ended with no table; service.cin stays None

    def __init__(self, kind, files):
        super().__init__()
        self.kind = kind
        self.files = list(files)
        # fields cinbase reads; see the class docstring for who writes them.
        # ``future``/``loading``/``cin`` follow the #1004 loader surface
        # (the CinTableBase slot above): the single Future slot is the truth
        # and the other two are read off it, so a holder cannot disagree with
        # its own loader.
        self.future = None
        # the flag a Thread-shaped loader sets in its own ``run``; the Future
        # slot wins whenever it exists (see ``_pending``).
        self._loading = False
        self.curCinType = None
        self.userExtendTable = None
        self.priorityExtendTable = None
        self.ignorePrivateUseArea = None
        # The policy's own state: the loader last started through ensure(),
        # and how many ensure() has ever started. load_count pins "one
        # loader per table across back-to-back instantiations"; it is not a
        # claim that production raced before. checkConfigChange spawns
        # loaders of its own straight past this module, and those stay
        # upstream's business.
        self.load_count = 0
        self._loader = None
        self._lock = threading.Lock()

    @property
    def loading(self):
        """True while something is still filling this holder.

        Derived, so it cannot drift from the loader: the #1004 Future slot
        wins, and a Thread-shaped loader's own flag is the fallback.
        """
        return self._pending() or self._loading

    @loading.setter
    def loading(self, value):
        self._loading = bool(value)

    def _pending(self):
        """True while the remembered load has not finished, either shape."""
        if self.future is not None:
            return not self.future.done()
        loader = self._loader
        if loader is None:
            return False
        alive = getattr(loader, "is_alive", None)
        return bool(alive()) if callable(alive) else False

    def _wait(self, timeout):
        """Bounded wait on whoever is loading; True when it timed out.

        Both loader shapes are covered: the #1004 ``Future`` (the
        ``CinTableBase.wait`` above) and a Thread-shaped ``join``. A load
        that finished with an exception is not a timeout — upstream's
        done-callback swallows the reason
        (python/cinbase/__init__.py:3470-3471), and the caller reads the
        absence of a table instead.
        """
        if self.future is not None:
            try:
                self.future.result(timeout)
            except concurrent.futures.TimeoutError:
                return True
            except Exception:
                pass
            return False
        loader = self._loader
        if loader is None:
            return False
        join = getattr(loader, "join", None)
        if callable(join):
            join(timeout)
        return self._pending()

    @property
    def cin(self):
        """The loaded table once its future is done, else None.

        A failed load has no table: upstream's done-callback swallows the
        reason (python/cinbase/__init__.py:3470-3471) but the Future still
        holds it, so ``result()`` is read inside a try and the observable
        fact stays ``cin is None``.
        """
        if self.future is not None and self.future.done():
            try:
                return self.future.result()
            except Exception:
                return None
        return None

    def wait(self, timeout=None):
        """Block for the scheduled load and return the table, or None."""
        if self.future is not None:
            try:
                return self.future.result(timeout=timeout)
            except Exception:
                return None
        return None

    def _label(self):
        """The name this holder answers with: its file list, kind-tagged."""
        return "%s[%s]" % (self.kind, ",".join(self.files))

    def ensure(self, service, loader_factory, timeout=10.0):
        """Start the load if this table is not what the Service wants and
        nothing is loading; otherwise join whoever is. Returns the outcome —
        SPAWNED, LOADED or FAILED — never None, and never raises.

        The spawn branch touches nothing on the Service: upstream's loader
        writes ``cbTS.cin`` itself (python/cinbase/__init__.py:3463-3469).
        The join branch blocks up to ``timeout`` seconds for the remembered
        loader and then adopts the table (``service.cin = holder.cin``) or,
        on FAILED, leaves ``service.cin`` as it is — None for a fresh
        Service — which is today's product behaviour: cinbase sees the
        absent table and shows the loading message instead of the session
        dying. Nothing on the constructor's path may raise; use
        wait_until_ready() to ask with an exception.
        """
        with self._lock:
            stale = self.curCinType != service.cfg.selCinType
            if stale and not self.loading:
                loader = loader_factory(service, self)
                self._loader = loader
                self.load_count += 1
                # ``start()`` schedules the load on the shared executor and
                # stores the Future on this holder
                # (``LoadCinTable.start``, python/cinbase/__init__.py:3439-3477);
                # the returned object is the same Future, so the holder stays
                # the single source of the load state either way.
                future = loader.start()
                if future is not None:
                    self.future = future
                return self.SPAWNED
        if self._join(timeout) is not None:
            return self.FAILED
        service.cin = self.cin
        return self.LOADED

    def wait_until_ready(self, timeout=10.0):
        """Block until the remembered loader finishes; raise TableLoadError
        naming the table with the reason when it is still absent. This is
        the raise seam for tests and explicit queries — the Service
        constructor crosses ensure(), which cannot raise.
        """
        reason = self._join(timeout)
        if reason is not None:
            raise TableLoadError("%s: %s" % (self._label(), reason))

    def reset(self, timeout=10.0):
        """Forget the table and the loader — the test seam that replaces
        writing module globals from a test.

        Waits the remembered loader out first, and is pristine only when no
        loader is left running: if one does not finish within ``timeout``,
        raises TableLoadError and clears nothing. An unfinished upstream
        loader still owns its handle to this holder
        (python/cinbase/__init__.py:3457-3461 write the mirror fields, and
        :3463-3469 the Service's ``cin``, through it), so clearing anyway
        would let the next caller adopt the previous test's table — bound to
        the previous APPDATA — which is the exact leak this seam exists to
        close.

        Clearing ``future`` is what clears ``loading`` and ``cin`` — both read
        off it — and the ``_loading`` fallback goes with it, so a reset holder
        is pristine by construction once the wait above has come back.
        """
        if self._wait(timeout):
            raise TableLoadError(
                "%s: refusing to reset, its loader is still running "
                "after %g seconds" % (self._label(), timeout))
        with self._lock:
            self.future = None
            self._loading = False
            self.curCinType = None
            self.userExtendTable = None
            self.priorityExtendTable = None
            self.ignorePrivateUseArea = None
            self.load_count = 0
            self._loader = None

    def _join(self, timeout):
        """Bounded wait for whoever is loading: None once the table is
        usable, otherwise the reason it is not. Bounded on every path —
        that is the point of the rewrite; the constructor used to do
        ``while CinTable.loading: continue``, no sleep and no way out if a
        loader ever failed to clear the flag.
        """
        deadline = time.monotonic() + timeout
        if self._wait(timeout):
            return "still loading after %g seconds" % timeout
        # A load scheduled straight past ensure() — checkConfigChange spawns
        # its own (python/cinbase/__init__.py:3317-3353) — owns only the
        # holder's own state, so wait on the derived flag too, bounded and
        # with the sleep the old busy-spin should have had anyway.
        while self.loading and time.monotonic() < deadline:
            time.sleep(0.005)
        if self.loading:
            return "still loading after %g seconds" % timeout
        if self.cin is None:
            return ("did not become usable: no table after the join "
                    "(upstream's loader swallows the reason, "
                    "python/cinbase/__init__.py:3470-3471)")
        return None


__all__ = ["CinTableBase", "TableHolder", "TableLoadError"]
