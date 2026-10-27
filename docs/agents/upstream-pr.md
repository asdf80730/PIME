# Upstream pull requests

A PR to `EasyIME/PIME` carries the product change only. The local harness stays local.

A Windows 11 box verifies what this checkout cannot and pushes only `win/*`; ref
ownership and the SHA-not-branch rule are in `windows-box.md`.

## Syncing local `master`

`master` is the integration branch and the base of every PR branch, so bring upstream in
before branching. Merge on `master` itself: `git push fork master` pushes that ref, not
`HEAD`, so a merge parked on a side branch still ships the old tip and CI spends a run on
the stale SHA.

The fork carries ~150 stale remote branches, so `git branch -a` and `git branch -avv`
print kilobytes of noise. Ask ancestry and recency questions directly instead:
`git branch --contains <sha>`, `git log --all --oneline --since=<date>`, or
`git ls-remote fork refs/heads/master`.

```bash
git fetch origin
git switch master
git merge --no-ff origin/master      # the EasyIME remote, whatever this checkout names it; resolve here
tests/run_local_tests.sh             # all PASS before the push
git push fork master
git ls-remote fork refs/heads/master # must equal `git rev-parse master`
```

Conflicts land in the same places every sync:

- Product code (launcher, node, Python): take upstream's side, then re-apply only the local
  seam a test needs — `loadServices(baseDir)` is the standing example.
- `node/package.json` — upstream owns the `test` script and names one file
  (`tests/nimeServer.test.js`), and its workflows install Node without ever running a
  test, so #999's `tests/emojime.test.js` runs only where the script names it. Name
  both: `node --test tests/nimeServer.test.js tests/emojime.test.js && node
  test/server.test.js && node test/loadServices.test.js`. A PR branch that adds a test
  under `node/tests/` merges its file into that list the same way.
- Rust: run `cargo fmt` after taking their hunks; upstream's formatting fails the local
  `cargo fmt --check` step.
- `AGENTS.md` and the workflows: keep upstream's text and re-add the local sections and
  steps below it.

## Before picking up an upstream issue

Open issues go stale: merged PRs resolve parts of a report faster than the
thread updates, so some stay open regardless (#973's `mode=0o700` removal and
NULL-context raise landed in #988; only the launcher elevation warning was
left). Before writing code, re-check the report against `origin/master` —
`git grep` the named code, `git log -S <key>` for the fix — and record which
claim of the report is still true.

## Delivering a PR

Review the diff before delivering it; the rules the reviewers work under are
`docs/agents/code-review.md`.

PR verbs on `gh` follow the credential in front of them. This Windows box has a
scoped gh login: `gh pr create` and `gh pr edit` worked (#1013). Checkouts holding
the fine-grained push-only token get 403 on `gh pr create`, `edit`, `comment`,
`ready`, label and close — when 403 comes back, do not retry; write the body file
and hand the compare URL plus body to the human.

- Branch from the product remote's master — whichever remote's URL is
  `EasyIME/PIME` (`upstream` on this box; `origin` is the fork, whose master *is*
  the integration branch and carries `docs/agents/`, `GLOSSARY.md`, research notes,
  and CI steps that run local test suites). The PR branch carries none of `docs/`,
  `tests/` or `AGENTS.md`, so read those and run the checks on the integration
  branch before branching, then switch back after pushing.
- Before pushing a `pr/*` branch, run the check from the PR worktree by absolute
  path (`<integration-checkout>/tests/check_pr_scope.sh <branch>`): the script
  exists only on the integration branch, and `tests/run_local_tests.sh` checks its
  own checkout, so it skips there. It resolves the product master by remote URL —
  never by the fork — and fails when the branch does not sit on it, when the diff
  carries `docs/`, `tests/`, `AGENTS.md` or `GLOSSARY.md`, or — first, before any
  remote is consulted — when the worktree you stand in tracks integration-only
  paths (`docs/agents/`, `GLOSSARY.md`, `.scratch/`). Push only after it
  prints `PASS`; recover with `git rebase --onto <product-base> <base>` or a fresh
  worktree plus cherry-picks.
- Before any push to the fork — branch or PR — run
  `tests/check_fork_ci_noise.sh <branch>`: the pushed tree's own workflow files
  decide what GitHub runs, so refs cut before the ci.yaml hardening mail the
  owner a startup failure per push. The check names them; a rebase onto a state
  carrying the hardened ci.yaml ends the mails.
- Ship the smallest diff that fixes the issue. Regression tests, CI wiring and HACKING
  entries stay on local `master` unless the maintainer asks for them in the PR.
- Title: `type(scope): what it does (#<issue>)`. Body: `Fixes #<issue>` (or `Closes`), a
  short paragraph of why, bullets for the change, a `Validation:` list, then the AI
  declaration as the last line. The merged PRs here carry no
  `Summary`/`Evidence`/`Merge Danger` headings; do not import a generic template.
- Keep the body self-standing: justify naming and behaviour choices by the product
  facts that shaped them. Cite an unmerged PR you do not own only when its author
  has agreed to the link; otherwise state the behaviour as fact, so the PR never
  reads as dependent on someone else's pending work.
- The declaration follows `AGENTS.md` §2 as rewritten upstream in #996, which splits code
  work three ways: `Architecture and design by <author>. Implementation generated with AI
  assistance from <agent> (<model>).` when the human set the approach,
  `Fully generated by <agent> (<model>) without human intervention.` when nothing human
  shaped the fix, and a question to the user when the brief cannot tell the two apart. Do
  not write the pre-#996 one-liner (`Generated with assistance from …`) on a new PR.
- The first workflow run from a fork PR sits in `action_required` until a maintainer
  approves it. Check `gh api repos/EasyIME/PIME/commits/<sha>/check-runs` before claiming
  CI evidence, and ask for the approval in the PR conversation.
- Write each `Validation:` line only after its run is green on the exact tree being
  committed: run `tests/verify_windows.sh` first, then compose the commit message.
  A green claim written before the run is credit taken before the sale; if the run
  fails after committing, fix and re-run before touching the message.
- Verify on `master`: `tests/run_local_tests.sh` runs the Python, Node, C++ helper, Go and
  Rust layers plus the GitHub YAML parse, skipping toolchains this machine lacks. Use the
  narrow command in `docs/agents/verification.md` when that loop is too slow.
- Commit messages follow `AGENTS.md` §2, including the AI declaration.
- Deliver: push the branch to `fork`, write the PR body to
  `.scratch/pr-<number>-body.md`, then open the browser compare URL and paste the
  body. A PR opened as a draft stays a draft until the human clicks "Ready for review".
  `gh api notifications` is 403 as well: list the work with
  `gh search prs --author @me --state open` and read discussion through
  `gh api repos/EasyIME/PIME/issues/<n>/comments`.
  Rerun `tests/run_local_tests.sh` after writing the body: its `PR bodies carry the AI
  declaration` step fails when the last line is missing. A body kept outside `.scratch`
  can be checked without moving it: `PR_BODY=/tmp/pr-<number>-body.md tests/run_local_tests.sh`.
- Done means: branch pushed, body file written, compare URL printed:
  `https://github.com/EasyIME/PIME/compare/master...asdf80730:<branch>?expand=1`.

## Rewriting history

Only rewrite a commit you created moments ago. More than one agent session can hold this
checkout, so the tip may already carry someone else's commit. Read `git log --oneline -5`
before `--amend`, `--fixup` or `rebase`, and leave a commit alone when its message is not
yours: a rebase that replays it anyway rewrites its hash and detaches the other session's
branch from its own work.
