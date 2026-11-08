# Shared checkout

More than one agent session may use this repo, and the arrangement is
**asymmetric**: the other environment edits its checkout in place, without
worktrees. Treat that working tree and its uncommitted files as theirs — never
`restore`, `clean`, `stash`, or `checkout --` a path you did not create, and do
not commit into the shared `HEAD` while they are active.

So an omp session works in the canonical omp worktree — `Documents/PIME-omp` —
and merges into the integration ref only after pulling in the other environment's
in-place commits.

**Read the integration ref, never recall it.** It is the checked-out branch whose
tip carries `docs/agents/` and `tests/`: `git rev-parse --abbrev-ref HEAD`, then
`git log --oneline -3`. One ref carries the harness: `local/stroke-parked`, which
absorbed `local/linux-master` — that branch is retired at `33d187c` (merged
2026-11-08), and the fork's mirror ref `fork/local/linux-master` was deleted on
2026-10-31, so neither is a live base. The survivor is published with
`git push origin local/stroke-parked:master`.

Both gates print their findings each run — `tests/check_integration_ref.sh` names the
candidate carriers, `tests/check_worktree_hygiene.sh` the stray worktrees — so the
ambiguity surfaces before a commit rather than after it.

```bash
# Feature base = that integration ref. A branch destined for an upstream PR is cut
# from the product remote's master — the remote whose URL is EasyIME/PIME — because
# the integration branch carries local harness commits by design; see
# docs/agents/upstream-pr.md.
git worktree add -q -b <agent>/<topic> .worktrees/<topic-slug> <base-ref>
```

- Run the command from the main checkout root: every linked worktree lives
  under `.worktrees/` there, never beside it. The user's `Documents\` top level
  stays free of agent folders, and `tests/check_worktree_hygiene.sh` (run by both
  verification gates) fails a run that finds strays.
- Name the directory the topic slug alone, never the branch's prefix
  (`chewing-userphrase-393`, not `pr-chewing-userphrase-393`); an agent-prefixed
  slug (`omp-worktree-hygiene`) is equally fine, the gate only checks the location.
- Remove it with `git worktree remove --force`. This repo carries a submodule, and
  the plain form aborts on it — sometimes after already removing an earlier tree in
  the same chain.
- A linked worktree carries no `.tools/` (that directory is excluded, not
  versioned): `docs/agents/windows-toolchain.md` says how a vendored tool is run
  from either tree.
- Write agent artifacts into `.scratch/`, the worktree they belong to, or `%TEMP%`;
  the user's `Documents\` top level stays empty of agent output.
- Edit files inside a linked worktree by **absolute path**: a mistyped relative
  path is re-anchored by filename match and can silently retarget the main
  checkout.

The in-place shared checkout `Documents\PIME` was deleted on 2026-10-27. Its only
surviving snapshot — the other environment's untracked ARM64X forwarder WIP plus a
full tracked diff — sits in `.scratch/pime-main-wip-2026-10-27/`, whose
`ARCHIVE.md` records the restore target, `tests/`. Do not prune it until that
environment returns or disowns the WIP.
