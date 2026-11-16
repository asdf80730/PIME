fix(cinbase): checkConfigChange re-applies defaultEnglish and defaultFullSpace (#844)

Fixes #844 — same route, the second one-shot pair.

Both values were applied only where `initCinBaseContext` first builds a
context, so saving the options page left langMode and shapeMode stale until
the Service was rebuilt; the mode buttons kept the old glyph too.

- `checkConfigChange` in `python/cinbase/__init__.py` now sets langMode and
  shapeMode from the shared cfg and refreshes the buttons through
  `updateLangButtons`, the same route #844 settled for the other one-shot
  pair.

Validation:

- `python/python3/python.exe` `-m unittest discover -s tests -p "test_cinbase_config_keys.py"`
  on the integration tree carrying this diff: `Ran 12 tests ... OK` — every
  record, the two defaults included, projects onto the engine-read values.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
