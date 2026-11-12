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
- A linked worktree also starts with the `libIME2` submodule **uninitialized**,
  and `tests/check_line_citations.sh` reddens on the two citations inside it
  until you run `git submodule update --init libIME2` in that tree. The second
  one is `python/input_methods/rime/brise`: `tests/test_agent_docs.py` reddens
  on the `docs/adr/0002-*` citation into
  `python/input_methods/rime/brise/preset/stroke.dict.yaml`, so a
  fresh worktree fails the pre-commit suite until
  `git submodule update --init python/input_methods/rime/brise` runs there too.
- `bash tests/check_tracker_layout.sh` has to run in the **main** checkout:
  `.scratch/` is gitignored, so a linked worktree holds none and the check
  answers `SKIP ... (no .scratch in this checkout)` with its 125 code instead
  of the 0 the ticket asks for.
- The installed pre-commit hook writes its suite log under
  `$(git rev-parse --absolute-git-dir)`, the one path that exists in both tree
  shapes; a `$root/.git/...` spelling dies in a linked worktree and the commit
  goes through `--no-verify`, skipping the staged AI-declaration check.
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
