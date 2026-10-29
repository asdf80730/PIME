# Shared checkout

More than one agent session may use this repo, and the arrangement is
**asymmetric**: the other environment edits its checkout in place, without
worktrees. Treat that working tree and its uncommitted files as theirs — never
`restore`, `clean`, `stash`, or `checkout --` a path you did not create, and do
not commit into the shared `HEAD` while they are active.

So an omp session works in the canonical omp worktree — `Documents/PIME-omp`,
branch `local/linux-master`, the integration ref, maintained by omp — and merges
into it only after pulling in the other environment's in-place commits:

```bash
# Feature base = the checkout's integration ref (`master`, else
# `local/linux-master`). A branch destined for an upstream PR is cut from the
# product remote's master — the remote whose URL is EasyIME/PIME — because the
# integration branch carries local harness commits by design; see
# docs/agents/upstream-pr.md.
git worktree add -b <agent>/<topic> ../<repo>-<agent> <base-ref>
```

- Name the directory `<repo>-<agent>-<topic-slug>`: a bare slug, never the
  branch's prefix (`PIME-omp-890`, not `PIME-omp-rimepr`).
- Remove it with `git worktree remove --force`. This repo carries a submodule, and
  the plain form aborts on it — sometimes after already removing an earlier tree in
  the same chain.
- A linked worktree carries no `.tools/` (that directory is excluded, not
  versioned): `docs/agents/windows-toolchain.md` says how a vendored tool is run
  from either tree.
- Write agent artifacts into `.scratch/`, the worktree they belong to, or `%TEMP%`;
  the user's `Documents\` top level stays empty of agent output.
- Edit files inside a sibling worktree by **absolute path**: a mistyped relative
  path is re-anchored by filename match and can silently retarget the main
  checkout.

The in-place shared checkout `Documents\PIME` was deleted on 2026-10-27. Its only
surviving snapshot — the other environment's untracked ARM64X forwarder WIP plus a
full tracked diff — sits in `.scratch/pime-main-wip-2026-10-27/`, whose
`ARCHIVE.md` records the restore target, `tests/`. Do not prune it until that
environment returns or disowns the WIP.
