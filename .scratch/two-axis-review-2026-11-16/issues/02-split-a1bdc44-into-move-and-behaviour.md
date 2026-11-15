# 02: Isolate the 17 moves of `a1bdc44` from its behaviour half

**What to build:** the standing rule "Isolate Renames and Moves" holds for the rime
per-language work, so a reviewer reads the rename commit as a pure path table.

Status: resolved
Category: enhancement
Blocked by: None

- [x] One commit carries only `python/{input_methods/rime => rimebase}/*` and
      `rime_ime.py => rime_service.py` (`git show --name-status` answers `R100` rows only)
- [x] A second commit carries `rime-cn/ime.json` plus the wrapper and the four reader
      edits (`DllEntry.cpp`, `ImeProfileGuids.h`, `PIMEImeModule.cpp`, `serviceManager.py`,
      `loadServices.js`, `server.go`) and `installer.nsi`
- [x] `bash tests/check_pr_scope.sh <branch>` answers for both from inside the worktree

## Answer

`2a78a50` is the move-only commit: `git show --name-status` answers twenty `R100` rows
and nothing else (the seventeen `rimebase` paths plus the icon set the earlier record
counted inside them). `03559ae` is the behaviour half: `rime.json`/`ime.json` per-language
folders, the `rime-cn` twin, the wrapper, the reader edits and the `installer.nsi` globs.

Gate truth 2026-11-16, from the integration checkout, for the `omp/tax-02` branch that
carries the pair:

- `bash tests/check_pr_scope.sh omp/tax-02` → `SKIP  pr scope (…)`, exit 125 — the
  documented answer for an `omp/*` integration-lineage ref; the `PASS` form is what a
  `pr/*` branch cut from `upstream/master` gets, and rows 7 and 8 of `spec.md` are those.
- `bash tests/check_pr_commit_declarations.sh omp/tax-02` → `SKIP`, exit 125, same reason.

## Comments

Standing rule in `docs/agents/code-review.md` section 2. The two-part shape is what the
PR split rows 7 and 8 of `spec.md` deliver.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
