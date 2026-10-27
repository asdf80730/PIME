# The Windows 11 verification box

The product is Windows-only and `windows-2025` CI is the authoritative
build; a real Windows 11 ARM64 desktop covers the layers CI cannot reach:
interactive TSF input, `tests/chewing_test.py`, an installed payload, and
the bundled `node.exe`/`python.exe` under a console.

Two machines work this repo against the same fork (`asdf80730/PIME`). As of
2026-10-30 the box is the only one with a checkout — the Linux machine's
tree, and with it its local `master` and `.scratch/` copy, is gone — so
every ref below is written from the box until a Linux checkout exists
again. Nothing below is stylistic. Each rule exists because the other
arrangement loses a commit, or mails a failure for work that never had the
secrets to pass. Commands here are written from the box, where the fork is
`origin` and the product remote is `upstream`.

## One writer per ref

| Ref | Writer | Rule |
| --- | --- | --- |
| `fork/master` | Windows box | `git push origin master` publishes the integration branch — fast-forward only, each push under explicit human approval (see the regime below). A Linux checkout, when one exists again, fetches it and rewrites its worktree from it; it never pushes there and never merges into it. |
| `fork/pr/<topic>` | Windows box | Cut from `upstream/master`, deleted after merge. Never rebased once pushed: a rebase moves the tip out from under a run. |
| `fork/win/<topic>` | Windows box | Windows-only fixes. The box pushes, then folds the commits into `master` itself — fast-forward when the branch was cut from it, otherwise cherry-pick what `master` lacks — and deletes the branch. |
| `fork/local/linux-master` | not in use | Existed to carry `master` to the box while the Linux machine wrote it. The box publishes `master` directly now, so the ref stays retired — and stays no base for a commit or a PR — until a Linux checkout returns. |
| local integration branch, `.scratch/` | Windows box | `local/stroke-parked` and the only issue-tracker copy: the Linux machine's `.scratch/` went with its tree. Exactly one copy of each. |

The fork carries ~150 stale branches. Do not add a ref outside this table, and
delete `win/*` once its commits are on `master`.

### Publishing regime (as of 2026-10-30)

No Linux checkout exists, so the box publishes `fork/master` itself:
`git push origin local/stroke-parked:master`, strictly fast-forward, each
publish under explicit human approval. The push's `linux-checks` run is the
only Linux executor left — nothing else executes `run_local_tests.sh` on
Ubuntu. Letting `master` sit 84 commits unpublished starved that signal for
weeks and turned a two-minute check into a day of red diagnosis (the
exit-126 and shimmed-`windll` defects both hid in the gap). Publish
integration work promptly. If a Linux checkout exists again, this regime
reverses and the Linux rows re-activate with it.

## Each machine's `master` is local, not shared

Measured 2026-10-26: both local `master`s descend from `fork/master` `f3bacaa`,
and neither was pushed. This machine sat 18 commits ahead (`53cb4d1`); the box
sat 5 ahead (`1da8847`, unknown here). A commit count quoted from one machine
describes that checkout, not the fork — ask
`git ls-remote origin refs/heads/master` before reasoning about shared state.
As of 2026-10-30 only the box's `local/stroke-parked` remains; the Linux side
of both measurements is history.

The box's harness layer (`verify_windows.sh`, `.tools/build_windows_artifacts.sh`,
environment notes) came from that gap: neither file existed here. It landed on
2026-10-27 as eleven commits on `29d68db` (`8573c02`), after the box rebased its
branch onto the new `master` — so the push carried the `ci.yaml` filter, ran no
build, and `master` could fast-forward, keeping the box's commit hashes. That was
the only time the box pushed a branch that is not a SHA-pinned test.

## Test a SHA, never a branch name

`pr/*` is rebased onto a fresh `upstream/master` when upstream moves, and history
is rewritten here routinely (see `upstream-pr.md`). A result keyed to a branch
name cannot be attributed to the tree that produced it.

```bash
git fetch origin pr/<topic>
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
- New `tests/*.sh` must be staged with `git update-index --chmod=+x`: the
  box's git carries `core.filemode=false`, so the tree records 100644 and
  the direct `step()` invocations of `run_local_tests.sh` — run by
  `linux-checks` — answer exit 126. `tests/check_sh_exec_bits.sh` gates the
  bit in both tree and staged modes.

## Harness authorship, execution authority

The Windows harness was written on the box, because that is the only place it
runs, and the box publishes its commits to `master` directly. Authoring and
authority remain separate: a change to `verify_windows.sh` or
`.tools/build_windows_artifacts.sh` is proven by a green run on the box plus
the push's `linux-checks`. `tests/run_local_tests.sh` skips or wines those
layers, and says so in its output.

## Why `ci.yaml` pushes only `master`

A fork holds no SignPath secrets, so `build-and-sign` can only fail there. With
`on.push.branches: ['**']`, every pushed branch — including a `win/*` branch that
exists to be fetched rather than built — started a run and mailed "Run failed".
The workflow therefore restricts branch pushes to `master`. Tag pushes
(`tags: ['v*']`) and the `paths-ignore` list are unchanged, so releases and the
markdown-only push filter behave as before.

A second guard sits on the `ci` job: `github.repository == 'EasyIME/PIME'`. The
SignPath secrets exist only upstream, so on the fork that call could only fail;
`linux-checks` still runs there, which is the signal a fork can actually
produce, and a fork PR still builds in the upstream run once a maintainer
approves it. What a fork loses is the ability to build Windows binaries at all —
take artifacts from the PR's upstream run, not from the fork.

The file is a local divergence from `origin/master`: keep it out of a `pr/*`
branch, since upstream builds its own branches.

The filter only helps a branch whose tip already carries it: a `push` event runs
the workflow file from the pushed commit, so a branch cut before this change —
such as the one-time `win/win11-layer` — still builds every push. Rebase that
branch onto the new `fork/master` before pushing it, or expect one mail.

## Publishing from the box

```bash
bash tests/verify_windows.sh                # every layer, native
bash tests/check_fork_ci_noise.sh <branch>  # the ref being pushed
git push origin local/stroke-parked:master  # fast-forward only, human-approved
git ls-remote origin refs/heads/master
```

The push's `linux-checks` run is the Linux executor: quote its run id with
the result. `local/linux-master` is not republished — the mirror carried
`master` to the box while Linux held the checkout, and its remote ref was
deleted on 2026-10-31. The inbound protocol it existed for (a Linux-side
force-push to the mirror, then a forced `git reset --hard` on the box) is
retired with it; one of those resets once cost the box an uncommitted run,
and no publishing step forces anything today.

The declaration check (`check_ai_declarations.sh`, a `verify_windows.sh`
layer) reads `origin/master`, so refresh that ref with `git fetch origin`
before running it after anyone moves the integration ref.
