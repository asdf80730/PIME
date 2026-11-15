# 01: Track `python/input_methods/rime/rime_ime.py` at HEAD

**What to build:** a clean checkout of `c635689` resolves both rime profiles. The
folder's `ime.json` declares `"moduleName": "rime_ime"` and all four readers
(`python/serviceManager.py` `loadFromJson`, `go-backend/server.go` `newClient`,
`node/loadServices.js` `loadServiceById`, `PIMETextService/PIMEImeModule.cpp`
`ImeModule::loadImeInfo`) resolve that name inside the folder, so the file has to
be a tracked object.

Status: ready-for-agent
Category: bug
Blocked by: None

- [ ] `git ls-tree -r HEAD --name-only python/input_methods/rime` lists `rime_ime.py`
- [ ] `python/python3/python.exe tests/run_worktree_tests.py tests/test_service_manager.py .`
      stays green, both `ShippedManifestImportTests` cases included
- [ ] The same run from a fresh `git worktree add` of `c635689` is green, which is the
      reading a clean clone gets

## Comments

The 15-line wrapper re-exports `rimebase.rime_service.RimeTextService`; the `rime-cn`
twin already carries its copy, so only the `zh-Hant` side is missing. Found on both
axes of the 2026-11-16 two-axis review.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
