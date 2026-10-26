# Host environment notes (Windows 11 ARM64, 2026-10)

This branch (`omp/master`, worktree `../PIME-omp`) is the omp-side
environment layer for this machine: what exists here, what tripped us, and
where the durable answers live. Keep it one page; the detail belongs in the
files it points at.

## What this checkout is

- The other agent environment edits `Documents/PIME` **in place**, without
  worktrees. That checkout is not ours; read it, never write or restore
  anything there that we did not create.
- Our canonical worktree is `../PIME-omp`, branch `omp/master`, maintained
  by omp. Base it on `upstream/master` at every sync; harness layers merge
  in, never out.
- `.tools/` arrives here as a directory junction onto the shared checkout.
  Deleting this worktree must never `rm -rf` the junction itself —
  `git worktree remove` handles it.

## Host facts that change behaviour

| Fact | Consequence | Durable answer |
|---|---|---|
| Non-PTY harness shells resolve PATH entries only in Windows form | `source .tools/env.sh` with POSIX entries gives rc=127 | both formats exported; see `docs/agents/windows-toolchain.md` |
| `python3`/`python` on PATH are Microsoft Store stubs (exit 49) | every probe needs a real run | use `python/python3/python.exe` |
| System lacks node/bun/go/cargo/Visual Studio/cmake | nothing builds without `.tools/` | `tests/install_windows_toolchain.sh` |
| Two sessions may run verification at once | Rust integration tests share machine pipe slots | stagger the cargo step, not the whole suite |

## Mistakes made here, so they stop here

- Believing an open upstream issue before re-checking it against the tree
  (#973 was already fixed by PR #988) — the check is a step in
  `docs/agents/upstream-pr.md`.

- Treating upstream CI as evidence for the Go backend — upstream `ci.yaml`
  never compiles Go; the go-backend on `upstream/master` imports
  `input_methods/{fcitx5,simple_pinyin}`, which are absent from its tree
  (build fails). Our local `verify_windows.sh` is the only Go gate that
  exists.
- Editing the shared checkout directly, then trying to disentangle after the
  fact; the worktree rule exists to make that impossible.

## Pushing this fork triggers its CI, which cannot pass

`build-and-sign` runs on every branch pushed to `asdf80730/PIME` and fails
there because the fork holds no signing secrets — every push becomes a
"Run failed" email to the owner. Back up with `git bundle` or rely on the
local worktree; do not push a backup branch. A push for a PR is fine — it
is the one time CI on a branch is wanted, and the failed fork run is
superseded by the `action_required` run in the PR itself.

## Tests on this host are ours alone

The suites here (unittest, node --test, go, cargo, gtest helpers) run on
this machine's toolchain and harness; the other environment's tests
differ by construction — same product, different probes. Green here proves
this layer; green in `build-and-sign` proves the product.
