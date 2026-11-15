# 01: Track `python/input_methods/rime/rime_ime.py` at HEAD

**What to build:** a clean checkout of `c635689` resolves both rime profiles. The
folder's `ime.json` declares `"moduleName": "rime_ime"` and all four readers
(`python/serviceManager.py` `loadFromJson`, `go-backend/server.go` `newClient`,
`node/loadServices.js` `loadServiceById`, `PIMETextService/PIMEImeModule.cpp`
`ImeModule::loadImeInfo`) resolve that name inside the folder, so the file has to
be a tracked object.

Status: resolved
Category: bug
Blocked by: None

- [x] `git ls-tree -r HEAD --name-only python/input_methods/rime` lists `rime_ime.py`
- [x] `python/python3/python.exe tests/run_worktree_tests.py tests/test_service_manager.py .`
      stays green, both `ShippedManifestImportTests` cases included
- [x] The same run from a fresh `git worktree add` of the tip is green, which is the
      reading a clean clone gets

## Answer

Two commits carry it: `0fdcb85` tracks the 15-line wrapper that `ime.json` names, and
`26e9e98` keeps it beside the engine module after the `a1bdc44` move (the `tax-02`
rename had deleted it as a pure move). Settled 2026-11-16 at the integration tip:

- `git ls-tree -r HEAD --name-only python/input_methods/rime` → `brise`, `ime.json`,
  `rime_ime.py`.
- `python/python3/python.exe tests/run_worktree_tests.py tests/test_service_manager.py .`
  → `OK`, including `ShippedManifestImportTests.test_module_file_lives_in_the_manifest_folder`
  and the `moduleName`-resolves case.
- The same suite from a fresh `git worktree add` of the tip → `Ran 14 tests ... OK`.

Both `python/rimebase/rime_service.py` (engine) and the folder-local wrapper are tracked,
so the `zh-Hant` side now matches the `rime-cn` twin.

## Comments

The 15-line wrapper re-exports `rimebase.rime_service.RimeTextService`; the `rime-cn`
twin already carries its copy, so only the `zh-Hant` side is missing. Found on both
axes of the 2026-11-16 two-axis review.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
