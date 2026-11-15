# 03: Split `26a7faf` and `45a770f` into one problem each

**What to build:** each harness commit states one problem, per "Granular, Incremental
Commits", so a red CI run names one step.

Status: ready-for-agent
Category: enhancement
Blocked by: None

- [ ] `26a7faf` becomes: the new `tests/check_nsi_file_globs.sh` plus its self-test and
      its wiring, the `installer/installer.nsi` brise glob fix, then the doc records apart
- [ ] `45a770f` becomes: the `tests/test_shipped_payload.py` pin, then the
      `tests/check_pr_scope_test.sh` and `tests/hooks/pre-commit` quieting apart
- [ ] `bash tests/run_local_tests.sh` still reports `0 FAIL` after the rewrite

## Comments

Judgement of the Standards axis, 2026-11-16.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
