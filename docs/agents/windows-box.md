# The Windows 11 verification box

This checkout is Linux and the product is Windows-only. `windows-2025` CI is the
authoritative build; a second machine runs a real Windows 11 desktop for the
layers CI cannot reach: interactive TSF input, `tests/chewing_test.py`, an
installed payload, and the bundled `node.exe`/`python.exe` under a console.

Two agents work this repo from two machines against the same fork
(`asdf80730/PIME`). Nothing below is stylistic. Each rule exists because the
other arrangement loses a commit, or mails a failure for work that never had
the secrets to pass.

## One writer per ref

| Ref | Writer | Rule |
| --- | --- | --- |
| `fork/master` | Linux | `git push fork master` publishes the integration branch. The box fetches it and rewrites its worktree from it; it never pushes there and never merges into it. |
| `fork/pr/<topic>` | Linux | Cut from `origin/master`, deleted after merge. Never rebased once pushed: a rebase moves the tip out from under a run on the box. |
| `fork/win/<topic>` | Windows box | Windows-only fixes. The box pushes; Linux fetches, cherry-picks what it does not already have, deletes the branch. |
| `fork/local/linux-master` | Linux | Read-only mirror of local `master` for the box. Force-push allowed; never a base for a commit or a PR. |
| local `master`, `.scratch/` | Linux | Integration branch and the only issue tracker. Exactly one copy, on this machine. |

The fork carries ~150 stale branches. Do not add a ref outside this table, and
delete `win/*` once its commits are on `master`.

## Each machine's `master` is local, not shared

Measured 2026-10-26: both local `master`s descend from `fork/master` `f3bacaa`,
and neither was pushed. This machine sat 18 commits ahead (`53cb4d1`); the box
sat 5 ahead (`1da8847`, unknown here). A commit count quoted from one machine
describes that checkout, not the fork — ask
`git ls-remote fork refs/heads/master` before reasoning about shared state.

The box's harness layer (`verify_windows.sh`, `.tools/build_windows_artifacts.sh`,
environment notes) came from that gap: neither file exists here. It merges once,
as `win/win11-layer` cherry-picked on this side, and the branch is then deleted.
That is the only time the box pushes a branch that is not a SHA-pinned test.

## Test a SHA, never a branch name

`pr/*` is rebased onto a fresh `origin/master` when upstream moves, and history
is rewritten here routinely (see `upstream-pr.md`). A result keyed to a branch
name cannot be attributed to the tree that produced it.

```bash
git fetch fork pr/<topic>
git switch --detach "$(git rev-parse FETCH_HEAD)"
git rev-parse HEAD      # quote this SHA in the report
```

A report carries the SHA, the workflow run id and the Windows build; without
them it is not evidence.

## Win11 box checklist

- Clone to a native NTFS path (`C:\src\PIME`). Never open this checkout over
  `\\wsl.localhost\…`: two index files and two build trees over one worktree
  lose writes.
- `git config core.autocrlf false`. The measured default on that machine was
  `true`, which reports LF files as modified (`git ls-files --eol` counts 607
  `i/lf` files here) and would commit CRLF churn into a product diff.
- `git config fetch.prune true`; the fork's stale branches otherwise accumulate.
- Prefer CI artifacts to a local MSVC build. `build-and-sign.yaml` uploads
  unsigned binaries and a signed installer for every non-tag ref, so
  `gh run download <run-id>` installs the payload the PR will ship. The first run
  of a fork PR waits in `action_required` for a maintainer; that is not a failure.
- A branch, when one is needed, starts from the tested SHA:
  `git switch -c win/<topic>-<short-sha> <sha>`.

## Harness authorship, execution authority

The Windows harness was written on the box, because that is the only place it
runs. Its commits still enter `master` from this side, so `master` keeps one
history; authoring and authority are separate. A change to `verify_windows.sh`
or `.tools/build_windows_artifacts.sh` is proven by a green run on the box.
`tests/run_local_tests.sh` skips or wines those layers, and says so in its output.

## Why `ci.yaml` pushes only `master`

A fork holds no SignPath secrets, so `build-and-sign` can only fail there. With
`on.push.branches: ['**']`, every pushed branch — including a `win/*` branch that
exists to be fetched rather than built — started a run and mailed "Run failed".
The workflow therefore restricts branch pushes to `master`. Tag pushes
(`tags: ['v*']`) and the `paths-ignore` list are unchanged, so releases and the
markdown-only push filter behave as before.

Residual: a push to `fork/master` still runs, and still fails for want of
secrets. If that mail is unwanted, the next step is a repository guard on the
`ci` job (which also drops the fork's `linux-checks` run) or disabling Actions on
the fork; neither follows from the branch filter.

The file is a local divergence from `origin/master`: keep it out of a `pr/*`
branch, since upstream builds its own branches.

The filter only helps a branch whose tip already carries it: a `push` event runs
the workflow file from the pushed commit, so a branch cut before this change —
such as the one-time `win/win11-layer` — still builds every push. Rebase that
branch onto the new `fork/master` before pushing it, or expect one mail.

## Publishing to the box

```bash
tests/run_local_tests.sh
git push fork master
git push fork +master:local/linux-master
git ls-remote fork refs/heads/master refs/heads/local/linux-master
```

Both refs must print the same commit (`git rev-parse master`); the mirror is not
a second history, just the same commit under a name the box may fetch without
touching `master`. The box then runs, in its own clone:

```powershell
git fetch fork
git reset --hard fork/local/linux-master
```

so its harness always matches this `master`. The forced update is confined to
`local/linux-master`; `master` only ever moves forward.
