# 03: Split `26a7faf` and `45a770f` into one problem each

**What to build:** each harness commit states one problem, per "Granular, Incremental
Commits", so a red CI run names one step.

Status: resolved
Category: enhancement
Blocked by: None

- [x] `26a7faf` becomes: the new `tests/check_nsi_file_globs.sh` plus its self-test and
      its wiring, the `installer/installer.nsi` brise glob fix, then the doc records apart
- [x] `45a770f` becomes: the `tests/test_shipped_payload.py` pin, then the
      `tests/check_pr_scope_test.sh` and `tests/hooks/pre-commit` quieting apart
- [x] `bash tests/run_local_tests.sh` still reports `0 FAIL` after the rewrite

## Answer

Four commits, each with its own tree and its own file list, read at the integration tip:

| commit | subject | `git diff --name-status <c>^ <c>` |
| --- | --- | --- |
| `a263973` | `tests: gate the installer File globs` | `installer/installer.nsi`, `tests/check_nsi_file_globs.sh` (A), `tests/check_nsi_file_globs_test.sh` (A), `tests/hooks/pre-commit`, `tests/run_local_tests.sh`, `tests/verify_windows.sh` |
| `0adcff5` | `docs(agents): record the CI read forms` | `docs/agents/issue-tracker.md`, `docs/agents/verification.md`, the ticket-04 record |
| `5504909` | `tests: pin the shipped payload` | `tests/test_shipped_payload.py` (A) |
| `d1a02aa` | `tests: quiet the PR scope self-test` | `tests/check_pr_scope_test.sh`, `tests/hooks/pre-commit` |

The old combined subjects are gone from the first-parent line; the whole range is linear,
so the two halves of each pair sit in order.

Settling outputs, 2026-11-16, same tree:

- `bash tests/check_nsi_file_globs.sh` → `OK  nsi File globs resolve (31 path(s) checked)`, rc 0.
- `bash tests/check_nsi_file_globs_test.sh` → thirteen `ok` lines plus `Self-test passed`, rc 0.
- `bash tests/run_local_tests.sh` → tail `0 failed, 13 skipped`, rc 0.
- Rebuild note for the next split: carry each entry's mode from `git ls-tree` when
  stamping a tree by hand — a hardcoded `100644` drops the `100755` bits of the five
  `tests/*.sh` files and the exec-bit gate reddens.

## Comments

Judgement of the Standards axis, 2026-11-16.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
