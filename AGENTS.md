# PIME AI Agent Rules

All AI agents (Antigravity, Cursor, Windsurf, Aider, omp, etc.) working in this
repository follow the rules below. The review-axis prose — PR granularity,
commit and PR message style, the AI-declaration forms, coding style, and
file-header attribution — lives verbatim as the **standing rules** in
`docs/agents/code-review.md`: read it before writing a commit message or
delivering a diff; the `tests/` gates named beside each rule enforce them
mechanically. What stays here is the write-time floor for every edit and the
index of agent docs.

## Hard limits, every edit

- **Invariant ids**: the load-bearing invariants live once, as a numbered list
  of `INV-NN` rows, in `docs/agents/invariants.md`; prose and gate headers cite
  the id instead of restating the sentence.
- **Read `HACKING.txt` first** before proposing an architectural change,
  adding a feature, or touching IPC logic: it is the authority on the C++
  client (TSF) and the Python/Node.js backend server architecture.
- **Guided overview**: `docs/tour/index.html` (zh-Hant) covers the
  architecture, one keypress lifecycle, wire formats, backend comparison, and
  glossary. Its status tables are dated snapshots; quote status from source.
- **Do not break the build**: the PIME DLL must support 32-bit (x86), 64-bit
  (x64), and ARM64 architectures; `PIMELauncher` and the backend servers are
  deliberately kept x86 to maximize compatibility.
- **OS compatibility** (`INV-01`): the minimum supported OS is **Windows 10**;
  use APIs available since Windows 10. The floor and its reason are settled by
  `docs/adr/0001-windows-support-floor.md`.
- **Comment languages**: in the core framework, **English only**; in input
  method modules, comments in the local language (e.g., zh_TW for a
  Traditional Chinese IM) are welcomed. Otherwise default to English.
- **Every added file declares its AI authorship** (`INV-03`) in its header;
  `tests/hooks/pre-commit` fails the commit on a missing one, and the category
  forms live in the standing rules of `docs/agents/code-review.md`.
- **Maintainer's plan, every session**: **v2.0 first, features after** — the framework
  is stabilised and tagged, and only then do new features start, so a `feat(...)` PR
  waits while the stabilizing set moves toward the tag. @PCMan settled it on 2026-11-13.
  The dated per-PR state (which numbers merged, which wait, which closed unmerged) lives
  in `.scratch/maintainer-plan-2026-11-13/spec.md`; read the numbers there rather than
  from memory. Every PR still carries exactly one problem: fixes and features never
  share a PR, and a rename or move is its own commit.
- **Reply language**: what the human reads is **zh-Hant** — answers, questions,
  and progress reports. What the machines and the upstream author read stays
  **English**: GitHub issue/PR comments, commit messages and PR bodies, and the
  prompts and findings passed between agent and subagents. The one bilingual case
  is the reporter-facing upstream issue comment: zh-Hant first, then English, per
  the standing rule in `docs/agents/code-review.md`.

## Agent skills

### Answers render as one page

`answer-me-with-html always-on` is on; the panel rules live in the skill at
`~/.agents/skills/answer-me-with-html`. Two box-specific facts: run its CLI as
`./.tools/node/node.exe ~/.agents/skills/answer-me-with-html/scripts/am.mjs`, and open
every panel with a `##` heading (a `#` is the page title, so an all-`#` draft renders
`0 panels`). Small talk, a one-line answer, raw command output and anything the user
asked to keep as text stay plain.

### Issue tracker

Issues live as local markdown under `.scratch/` in this checkout, and a **parked**
effort's records travel with its branch — upstream EasyIME/PIME issues are not used as
a work tracker. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context layout: `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
One decision record per settled question; the file name is the fact, the `INV-NN`
id is what prose cites:
`docs/adr/0001-windows-support-floor.md` (`INV-01`),
`docs/adr/0002-stroke-table-from-cns11643-with-prefix-expansion.md` (`INV-08`),
`docs/adr/0003-table-load-policy-lives-with-the-service.md` (`INV-09`),
`docs/adr/0004-per-backend-profile-guids.md` (`INV-07`).

### Input method tables

cinbase tables are `.cin` sources run through the converter into committed runtime JSON; the installer ships only the JSON, so sources and JSON are committed as a pair and must stay in sync. Adding or re-deriving a table: see `docs/agents/input-method-tables.md`.

### Cinbase configuration

Adding a cinbase setting is one `CONFIG_RECORDS` row (`INV-02`) and hides the
per-Service shipped-config trap in the shipped defaults. `docs/agents/cinbase-config.md` names
the files and the working example PR.

### Chewing backend

Return conventions of the pinned libchewing submodule — `git -C libchewing status`
answers the pin, and `git submodule update --init libchewing` restores it when the
checkout is uninitialized — are settled from that pinned source, never guessed or
analogy-carried between neighbouring APIs. `docs/agents/chewing-api.md` has
the init command, the files that answer what, and the verified userphrase
return table.

### Rime backend

Return conventions of the bundled `rime.dll` — the librime source is not
vendored here — are settled by probing that DLL and by the `RimeApi._fields_`
declarations, never carried over from libchewing. `docs/agents/librime-api.md`
has the re-derive commands, the verified config/option return table, the
case-sensitive profile matching, the one-`RimeSetup`-per-process rule, and the
expected `E1112`/`E1113` glog lines (`INV-04`).

### Verification

`tests/run_local_tests.sh` runs every Linux-verifiable layer (host and bundled
Python, Node, Go tests plus Windows cross-build, C++ helpers, Rust tests/fmt/clippy
under Wine) and skips missing toolchains. C++/TSF and installer changes still need
Windows CI. On a Windows checkout the same layers run natively through
`bash tests/verify_windows.sh` (direct exec dies rc 193; toolchain under `.tools/`, installed by
`tests/install_windows_toolchain.sh`, excluded locally). See
`docs/agents/verification.md`, `docs/agents/windows-toolchain.md`, the Wine
path in `docs/agents/wine.md`, and the issue-triage labels in
`docs/agents/triage-labels.md`.
Narrow a Python run to one test file with the command in
`docs/agents/verification.md`; the bundled interpreter is an embedded
distribution, so plain `-m unittest tests.test_x` fails there.

### Upstream PRs

Upstream PRs carry product changes only; tests, CI wiring and agent docs stay on local `master`, and PR branches start from the product remote's master — whichever remote's URL is `EasyIME/PIME`, whatever this checkout names it. See `docs/agents/upstream-pr.md`. Before any push to the fork — any branch, not just `pr/*` — run `tests/check_fork_ci_noise.sh <branch>`: the pushed tree's own workflow files fire the runs, so a ref carrying the old push trigger mails the owner a failure per push.

### Windows verification box

A second agent works from a Windows 11 machine against the same fork, and the
Windows-only harness lives there. Read `docs/agents/windows-box.md` before
pushing any branch to `fork`: one writer per ref, `win/*` is the box's only ref,
and results are reported against a SHA.

### Shared checkout

Two environments can work this repo at once, asymmetrically: one edits a checkout in
place, sessions like this one use a worktree off the integration ref. Read
`docs/agents/shared-checkout.md` before touching a worktree, a shared `HEAD`, or any
path you did not create.
