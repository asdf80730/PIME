refactor(rime): move the shared engine files to python/rimebase

No separate issue; the move is the whole story.

The rime engine serves both Chinese Windows input languages from one set of
engine files, so they move out of the per-language folder to `python/rimebase`
and the two folders read one PIME.yaml and one icon set.

- `python/rimebase/librime.py`, `python/rimebase/rime_keyevent.py`,
  `python/rimebase/rime_service.py`, `python/rimebase/rime.dll`,
  `python/rimebase/data/PIME.yaml`, `python/rimebase/icon.ico` and
  `python/rimebase/icons/` carry the unchanged contents of the old
  `python/input_methods/rime/` engine files.
- The folder's own `python/input_methods/rime/rime_ime.py` keeps just the
  thin wrapper that re-exports `RimeTextService` from the shared package —
  the name the folder's ime.json declares as its moduleName; one rime.dll
  and one RimeTextService serve both profiles.

Validation:

- `python/python3/python.exe` `-m unittest discover -s tests -p "test_service_manager.py"`
  on the integration tree carrying this diff: `Ran 14 tests ... OK` — the
  dispatcher still resolves the rime manifest to the moved package.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
