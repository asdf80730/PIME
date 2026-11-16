# 10: Cut the twelve product PR branches from the split table

**What to build:** every row of the `spec.md` split table exists as a branch on the
fork off the product remote's master, each with its body file and printed compare URL.

Status: resolved
Category: enhancement
Blocked by: 01, 02, 03

- [x] Rows 1-12 each carry a `pr/<topic>` branch with only product paths
- [x] `bash <integration-checkout>/tests/check_pr_scope.sh <branch>`, `check_pr_commit_claims.sh`,
      `check_pr_commit_declarations.sh` and `check_fork_ci_noise.sh` all answer before the push
- [x] Each body file `.scratch/pr-<n>-body.md` passes `bash tests/check_pr_bodies.sh`
- [x] Rows 5 and 6 reuse the existing `pr/cinbase-per-ime-config` and
      `pr/chewing-userphrase-393` rather than opening twins
- [x] Row 4 waits on upstream #1004, so it stays un-pushed until that merges

## Answer

Twelve rows, ten pushed, one parked, one already upstream. Each branch is cut from
`upstream/master` (`27f11674`) and carries only product paths; the four gates answered
per branch, from inside its own worktree, 2026-11-16:

| row | branch | tip | scope | claims | declarations | fork CI noise |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `pr/cinbase-shared-service` | `c0b380b9` | PASS | PASS | PASS | NOTE |
| 2 | `pr/cinbase-config-records` | `44de7412` | PASS | PASS | PASS | NOTE |
| 3 | `pr/textservice-hook-partials` | `8ec24e49` | PASS | PASS | PASS | NOTE |
| 4 | `pr/cinbase-table-holder` | `00434429` | PASS | PASS | PASS | NOTE |
| 5 | `pr/cinbase-per-ime-config` | `1fc024c4` | PASS | PASS | PASS | NOTE |
| 6 | `pr/chewing-userphrase-393` | `ffec9d5f` | ancestor of `upstream/master` | — | — | — |
| 7 | `pr/rimebase-move` | `c121f5d4` | PASS | PASS | PASS | NOTE |
| 8 | `pr/rime-per-language-ime-json` | `014b45e9` | PASS | PASS | PASS | NOTE |
| 9 | `pr/go-wire-map` | `72eb5c3c` | PASS | PASS | PASS | NOTE |
| 10 | `pr/rime-service-manager-shape` | `1c3b008e` | PASS | PASS | PASS | NOTE |
| 11 | `pr/cinbase-fullshape-shift` | `25e479c0` | PASS | PASS | PASS | NOTE |
| 12 | `pr/cinbase-config-change-modes` | `4dee1a2a` | PASS | PASS | PASS | NOTE |

`NOTE` is `check_fork_ci_noise.sh` saying the pushed tree carries the product workflows
unchanged, so the mails are upstream's own triggers.

Row 5 needed the documented ancestry recovery, `git rebase --onto upstream/master 739ed171`,
then `--force-with-lease`; row 6 is an ancestor of `upstream/master` (merged as #1022), so no
twin and no push. Row 4 pushed once its blocker cleared: `8cb659a Merge pull request #1004
from EasyIME/feature/cinbase-table-manager` is an ancestor of `upstream/master`
(`git merge-base --is-ancestor 8cb659a upstream/master`), and the scope gate then answers
`PASS  PR scope (pr/cinbase-table-holder is on upstream/master, 11 file(s) beyond it,
1 picked commit(s) matched)`.

Body files: `.scratch/pr-1-body.md` … `.scratch/pr-12-body.md`, each `Fixes #<issue>`
(or the `No separate issue;` opener), why paragraph, bullets, `Validation:` list,
declaration last. `bash tests/check_pr_bodies.sh` → `checked 40 PR bodies`, no red line.
One rule cost a fix: a `Validation:` line must keep the arguments outside the backtick
span that holds the path, so `python/python3/python.exe` is cited alone and `-m unittest
discover -s tests -p "…"` sits outside the span.

## Comments

Form per `docs/agents/upstream-pr.md`: title `type(scope): what it does (#<issue>)`,
body `Fixes #<issue>`, why, bullets, `Validation:`, declaration last.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
