# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files in `.scratch/`.

This repo (EasyIME/PIME) is an upstream project we contribute to; its GitHub
Issues are not used as our work tracker. Tickets stay local to the checkout.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- Loose single files (PR body/comment drafts, saved evidence) stay **flat** at the
  top of `.scratch/`, named after their target: `.scratch/pr-<n>-body.md`,
  `.scratch/pr-<n>-review.md`. A directory under `.scratch/` reads as a feature,
  and the layout check then demands its spec/map/ARCHIVE.
- The spec is `.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined tickets file
- Triage state is recorded as a `Status:` line near the top of each issue file (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading
- Non-feature holdings (rescued WIP, snapshots) live in `.scratch/<name>/` carrying an
  `ARCHIVE.md` that records the origin and restore target; the layout check skips those

The layout is machine-checked: `bash tests/check_tracker_layout.sh` exits 0 when
every feature directory carries its spec (or wayfinder map) — or an `ARCHIVE.md`
when it is a holding — and every ticket is `NN-<slug>.md` with a `Status:` line.

## Parking an effort

When the maintainer parks a feature — the code stays on a branch, nothing is pushed —
the records travel with it, and a branch switch is the moment they go missing: the
branch tracks them, so checking out any other branch deletes the directory.

- Commit the directory onto the branch that carries the feature: `git add -f` it there.
  `.scratch/` is excluded from git, so plain `git add` reaches nothing.
- Carry `ARCHIVE.md` in the directory: the branch, what the directory holds, and the
  restore command. The layout check skips a directory carrying it, which is what keeps
  a half-restored one from failing the gate.
- Restore after switching back with
  `git archive <branch> .scratch/<feature-slug> | tar -x`, then re-run
  `bash tests/check_tracker_layout.sh` before calling the gate green.

Done when the parked branch holds the records, and this checkout's
`.scratch/<feature-slug>/` either holds them or carries `ARCHIVE.md`.

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.scratch/<effort>/map.md` (the Notes / Decisions-so-far / Fog body).
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.
