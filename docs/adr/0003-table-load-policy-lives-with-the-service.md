# Table-load policy lives with the Service, not in the shared engine

Every cinbase-family Service constructor carried the same four lines: check
`CinTable.curCinType` against `cfg.selCinType`, spawn `LoadCinTable` if stale
and nobody is loading, else `while CinTable.loading: continue`, then adopt
`CinTable.cin`. The 筆畫 Service now keeps that policy in its own
`python/input_methods/chebihua/table_loaders.py` — a `TableHolder` per 碼表 plus
`ensure`/`wait_until_ready`/`reset` — and the shared engine is untouched. The
reason it is local and not shared: upstream PR #1004 is open on exactly that
code, and the review notes on the #917 rework that #1004 continues objected to
making `__init__` block until the table loads ("Use a `threading.Event` or keep
loading async"), with six design points still open
(`docs/research/upstream-issue-triage.md:321-343`) — so a local fork of shared
behaviour would both collide with that PR and pre-empt a decision the upstream
maintainers have not made.

## Considered options

- **Fix the loader in `python/cinbase/__init__.py`** — rejected: upstream-owned,
  open as #1004, which rewrites exactly this loader. Its `run()` raises `loading` itself (`:3285`), writes
  `CinTable.cin`/`curCinType` (`:3306-3307`) and ends in `except Exception:
  pass` (`:3321-3322`) with `finally: loading = False` (`:3324`), so a failed
  load is unobservable from outside without editing that file.
- **Generalise to all nine Services now** — rejected: eight still carry the
  identical busy-spin (e.g. `python/input_methods/checj/checj_ime.py:64`), none
  has a test that would notice a mistake, and one Service's test surface is not
  a reason to put eight shipped input methods at risk. Two adapters make a seam
  worth extracting; one does not.
- **Raise the load failure out of the constructor** — rejected as shipped
  behaviour: nothing on that path catches it (`python/serviceManager.py:87` into
  `python/server.py`, whose per-request `except` at `:141` is the only catcher),
  the connector still accepts the handshake, and the user gets a session where
  every key answers `success: False` with the reason only in
  `%LOCALAPPDATA%\PIME\Logs\python_backend.log`. Today at least shows
  「正在載入輸入法碼表，請稍候...」 (`python/cinbase/__init__.py:460-462`). So
  `ensure()` returns `SPAWNED`/`LOADED`/`FAILED` and never raises; the raising
  variant is `wait_until_ready()`, which tests and explicit queries call.
- **Use a `threading.Event` instead of joining the remembered loader** — not
  available: the flag belongs to upstream's `run()`, which sets and clears it in
  its own `finally`; we may not pass it an event we could set without editing
  `python/cinbase/**`. Joining the thread we started is the only bounded wait
  reachable from here.

## Consequences

- Until #1004 lands or dies, 筆畫 is the only cinbase Service without a
  busy-spin in its constructor, and the other eight keep spinning. A later
  architecture review will see the duplication and propose sharing it again:
  this ADR is the answer, and the generalisation becomes live only once #1004 is
  resolved.
- The old check-then-spawn could start a second loader in the window between
  `Thread.start()` and the child setting `loading`; that second loader's
  `self.cbTS.cin.__del__()` (`python/cinbase/__init__.py:3297`) can touch the
  first one's live table. `ensure()` closes the window by remembering the loader
  it started, and a gated test pins it — the test is the reason the guard is
  allowed to stay.
- `reset()` is a test seam only, and it raises rather than pretending: a loader
  it could not wait out would otherwise hand the next test the previous test's
  table, bound to the previous `APPDATA`.
- If #1004 lands with a shared fix, `table_loaders.py` is expected to be
  deleted, not grown; its `TableHolder` field names are already pinned by what
  the engine reads.
