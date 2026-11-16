Fixes #890 — no separate issue; see the review note on this branch.

`python/cinbase/config.py` rebinds the name `CinBaseConfig` to a single shared instance, and each cinbase input method built its settings by calling `CinBaseConfig.__init__()` and then `copy.deepcopy()`-ing that object — so constructing a service snapped the very singleton `configtool` reads back to the constructor defaults, and two input methods starting at the same time could race between the reset and the copy, picking up each other's values.

- Export the class from `python/cinbase/config.py` as `CinBaseConfigClass` before the name is rebound to the shared instance.
- Build a private config with `CinBaseConfigClass()` in all eight cinbase IMEs: no shared-object reset, no deepcopy, and the now-unused `import copy` is dropped.
- `CinTableBase` from #1004 is kept in the import block of every IME; the branch is rebased onto current `master`, so the import conflict resolves here rather than at merge time.

Each IME still sets `imeDirName` and `cinFileList` and calls `load()` on its own config; the removed deepcopy came from a just-reset object, so a fresh instance starts from the same defaults and behaviour is unchanged.

Validation:

- `python -m compileall python` clean on the bundled 32-bit interpreter.
- `python/python3/python.exe` `-m unittest discover -s tests -p "test_cinbase_config_isolation.py"`: `Ran 3 tests ... OK` — constructing one backend leaves the shared config object untouched.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
