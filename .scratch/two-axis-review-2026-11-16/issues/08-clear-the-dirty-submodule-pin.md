# 08: Land the `McBopomofoWeb` pin without a dirty submodule

**What to build:** `git submodule status` answers a plain SHA for `McBopomofoWeb`,
so the integration ref's tree is reproducible.

Status: resolved
Category: bug
Blocked by: None

- [x] `git submodule status` prints no dirty marker for `McBopomofoWeb`
- [x] The submodule's own commit is identified by one SHA and the superproject pin matches
      that SHA exactly
- [x] `python/python3/python.exe tests/run_worktree_tests.py tests/test_js_ime_options.py .`
      stays green on the committed bytes

## Answer

`cbdc31f` carries the pin and `a9b63ab` the patch record. Settled 2026-11-16 in the main
checkout, after the object was fetched into `McBopomofoWeb`'s own object store from the
`tax-08` worktree's module store:

- `git submodule status` → ` c0c99b2c1e14e0991b09d138c4a280b1d7798204 McBopomofoWeb (c0c99b2)`
  — no `+`/`-` prefix, and `git status --short` lists no `McBopomofoWeb` entry.
- `git -C McBopomofoWeb status --short` → empty.
- `git -C McBopomofoWeb log --oneline -2` → `c0c99b2 fix(options): loose compare for the
  numeric preselect and the beep_on_error key` on top of `271e4e9`.
- `python/python3/python.exe tests/run_worktree_tests.py tests/test_js_ime_options.py .`
  → `Ran 5 tests ... OK`.

Two notes for the next reader: the object arrived with a *mixed* index (`MM` on
`output/pime/js/options.js`) because the working bytes already matched `c0c99b2`;
`git -C McBopomofoWeb reset` (no `--hard`) refreshed the index against the new HEAD without
touching the files. And `git rev-parse --short a b c` is not accepted — one revision per call.

## Comments

`docs/agents/verification.md` records the layout: the payload sits in
`<submodule>/output/pime/` with `index.js` rebuilt by `build.bat`.

- Push to `openvanilla/McBopomofoWeb.git` was refused (403, no credentials), so
  the submodule commit `c0c99b2c1e14e0991b09d138c4a280b1d7798204` (answered by
  `git -C McBopomofoWeb rev-parse HEAD` in `tax-08`; the superproject pin of
  `omp/tax-08` matches it) travels as
  `.scratch/mcbopomofoweb-pin-c0c99b2c1e14e0991b09d138c4a280b1d7798204.patch`
  until upstream can take it.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
