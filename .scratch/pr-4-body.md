refactor(cinbase): one TableHolder for the three table kinds

No separate issue; lands on top of #1004, whose table manager this deepens.

`CinTableBase` carried three empty subclasses per kind and swallowed the
load result, so a failed load left the Service with no way to tell spawned,
loaded and failed apart.

- `TableHolder(kind, files)` in `python/cinbase/cintablebase.py` keeps the
  future slot as the only state; loading/cin/wait derive from it,
  `ensure()` reports spawned/loaded/failed, `wait_until_ready()` is the
  raising seam and `reset()` the second seam.
- The three empty subclasses in `python/cinbase/service.py` collapse into
  `makeTableHolders` instances carrying kind + file list; each thin binding
  passes its file list in and reads cinFileList back off the holder.
- The shared `loadMainTable` becomes the same `ensure(self, LoadCinTable)`
  call the Stroke Service already crossed, closing the ADR-0003
  second-loader window for all nine Services with the bounded 10 s join.
- `table_loaders.py` keeps its module identity per ADR-0003 (deleted, not
  grown, when #1004 resolves) and instantiates the shared class; the loader
  trio in `python/cinbase/__init__.py` stays untouched.

Validation:

- `python/python3/python.exe` `-m unittest discover -s tests -p "test_cintablebase.py"`
  on the integration tree carrying this diff: `Ran 10 tests ... OK` — the
  three ensure() outcome cases plus the wait and reset seams answer as the
  shared class defines them.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
