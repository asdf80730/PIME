# 02: Isolate the 17 moves of `a1bdc44` from its behaviour half

**What to build:** the standing rule "Isolate Renames and Moves" holds for the rime
per-language work, so a reviewer reads the rename commit as a pure path table.

Status: ready-for-agent
Category: enhancement
Blocked by: None

- [ ] One commit carries only `python/{input_methods/rime => rimebase}/*` and
      `rime_ime.py => rime_service.py` (`git show --name-status` answers `R100` rows only)
- [ ] A second commit carries `rime-cn/ime.json` plus the wrapper and the four reader
      edits (`DllEntry.cpp`, `ImeProfileGuids.h`, `PIMEImeModule.cpp`, `serviceManager.py`,
      `loadServices.js`, `server.go`) and `installer.nsi`
- [ ] `bash tests/check_pr_scope.sh <branch>` prints `PASS` for both from inside the worktree

## Comments

Standing rule in `docs/agents/code-review.md` section 2. The two-part shape is what the
PR split rows 7 and 8 of `spec.md` deliver.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
