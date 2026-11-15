# Two-axis review 2026-11-16: the 33-commit range on `local/stroke-parked`

Status: in-progress
Category: enhancement

Fixed point `origin/master` = `2342734`; head `c635689`. Diff command
`git diff origin/master...HEAD` (33 commits, 168 files), plus the uncommitted
half through `git diff HEAD` (12 modified, 2 untracked). Both axes ran as
parallel reviewer sub-agents and were reported separately, never merged.

Standards axis: 3 hard documented-standard breaches + 5 judgement calls.
Spec axis: 1 missing requirement + 5 warnings. The worst item on both axes is
the same one: the untracked `python/input_methods/rime/rime_ime.py`.

## The settled PR split (author's `docs/agents/code-review.md` section 2)

Product files ride PRs cut from the product remote's master; `docs/`,
`tests/` and `AGENTS.md` stay on the local integration ref. One problem each,
renames and moves isolated, features and fixes apart.

| # | Title | Source |
| - | ----- | ------ |
| 1 | `refactor(cinbase): collapse the nine cin Service bodies onto one shared module` | `fd7180d` + the chepinyin hunk of `3734d14` |
| 2 | `refactor(cinbase): one record list declares every cinbase setting` | `c3a53e2` |
| 3 | `refactor(textservice): hooks return their partial reply, the dispatcher merges` | `fac7d55` |
| 4 | `refactor(cinbase): one TableHolder for the three table kinds` | `297ebb9`, waits on upstream #1004 |
| 5 | `refactor(cinbase): one config class name and per-Service instances` | `eae1976`, the existing `pr/cinbase-per-ime-config` |
| 6 | `fix(chewing): read the phrase POST through jQuery callbacks` | `00739a9`, the existing `pr/chewing-userphrase-393` |
| 7 | `refactor(rime): move the shared engine files to python/rimebase` (17 renames only) | first half of `a1bdc44` |
| 8 | `fix(rime): give each Windows input language its own ime.json folder` | second half of `a1bdc44` |
| 9 | `refactor(go): one wire reply shape in pime.Response.WireMap` | product half of `20f790d` |
| 10 | `fix(rime): keep the shared service manager in the shape the local suite pins` | `c7d3a6c` |
| 11 | `fix(cinbase): fullshape letters on the shift-to-English path` | working tree, `python/cinbase/__init__.py` three sites |
| 12 | `fix(cinbase): checkConfigChange re-applies defaultEnglish and defaultFullSpace` | working tree, `python/cinbase/__init__.py` one site |

11 and 12 share a file but are two problems, so they stay two commits.

## Layers already re-run on this tree, 2026-11-16

Thirteen python suites green (`test_service_manager` 14, `test_cinbase_config_keys`
12, `test_cinbase_shift_to_english` 9, `test_input_methods_smoke` 5 with
`skipped=1`, `test_js_ime_options` 5, `test_text_service` 15,
`test_server_protocol` 30, `test_cintablebase` 10, `test_shipped_payload` 5,
`test_agent_docs` 7, `test_chebihua_service` 14, `test_readme_contract` 9,
`test_cinbase_config_isolation` 3); the three node harnesses (23 fixture cases);
`go test ./...` 4 packages; the Rust launcher test, `cargo fmt --check` and
`cargo clippy`; the C++ IME profile GUID helper test; and the gates
`check_nsi_file_globs.sh` (31 paths), `check_gate_lib_test.sh`, and
`check_line_citations.sh` (281 citations).

## Verification

- `bash tests/check_tracker_layout.sh` exits 0 with this directory counted.
- Each ticket names the command that settles it and closes only on that output.
