# Rules for dispatched review agents

Read before dispatching a code-review sub-agent; paste the matching rule into
its prompt. Review findings carry weight: implementation has already paid for
the diff and trusts the reviewer's code reading.

## Behaviour-change claims: cite or mark `[INFERENCE]`

A finding that behaviour differs before and after the change is settled by the
code, not by the changed hunk alone. Before stating the difference, cite every
assignment to each state variable the claim reads — assignments in untouched
regions count, including per-event re-arms at the top of the enclosing
function. Cite the assignment sites in the finding itself; anything not cited
stays `[INFERENCE]` and the fix waits for a probe run instead.

cinbase worked example: `onKeyDown` re-arms `canSetCommitString = True` and
clears `candidates` on entry (`python/cinbase/__init__.py`, start of
`onKeyDown`), so a variable read deep in the key chain is almost never the one
the previous keypress left behind. A review that missed this manufactured a
false "Enter now commits" regression and sent implementation on a traceback
hunt for a bug that did not exist.

preserved-key worked example: a declined hotkey claim ends one layer below
Python — `libIME2/src/TextService.cpp` assigns
`*pfEaten = (BOOL)onPreservedKey(rguid)` in `OnPreservedKey`, so a `False`
return un-eats the key and the application receives the plain keystroke (the
issue #844 disabled Shift+Space fall-through). Cite that assignment or stay
`[INFERENCE]`.

## Fmt churn in a PR diff is scope creep

An upstream PR carries the smallest diff, so a hunk that is only `rustfmt`
reflow of code the change never functionally touches is **churn** — the
author ran the formatter crate-wide, not the tooling: the vendored rustfmt
disagrees with the runner's, and upstream files ride their own formatting
(`docs/agents/verification.md`, PR-worktree note). Flag every such file; the
fix is restoring it and re-running the formatter over the touched files
only. A diff where unrelated lines ride along breaks the reviewer's one
job: every line earning its review.

## A quoted number must be reproducible

A count written into a ticket, doc or commit body is a claim the next agent can
only re-derive from the command that produced it, or from a test that asserts it.
Bind every number to one of the two — quote the one-liner beside it, or name the
assertion — and re-run it before you write it down.

Stroke-table worked example — that feature is parked on `archive/chebihua-2026-10-29`,
the lesson outlived it: a ticket comment recorded "the 111,379 keys that lack a prefix
belong to 4,734 rare-plane-only characters". The table as then shipped measures 11,114
and 14,408. The prose read confidently, the numbers had been copied off an unrelated
probe, and only a reviewer re-running the query over the committed `.cin` caught it.

Reading a *name* is not measuring, even when the command runs. Round 2's scan
recorded this mislabel's blast radius as "0 characters in the shipped table": it
counted characters filed under the tier name, and the 符號 branch files by one name
while answering another, so that name never appears in the artifact. Two more rounds
passed before a probe counted `chardef` lines and found one character shipping at
three prefixes, offered by a single keypress. An impact number must name the
observable the user receives — the committed artifact, the settings page, the
candidate list — and a claim of *zero* impact carries both the command and what that
command inspects.

## Judge an AI header by the file's category

The standing rules (below) grade a new file's header by its **category**: a script, a lookup
table or a test is machine-generated and carries the autonomous form (`Generated
by <agent> (<model>) without human creative authorship.` + SPDX); a
human-designed product file carries human copyright plus the design credit. Read
the category first, so demanding the human-design header for a generator tool, a
committed `.cin`/`.json` pair or a test module is a false positive. The design
credit lives in the commit message and the PR body, in whatever form the effort's
ticket records under `.scratch/<effort>/`.

Stroke-table worked example: a review flagged the feature's table generator for the
autonomous header because an ADR recorded the design — an ADR describing an artifact's
shape does not make the file human-authored. The maintainer's standing choice for that
feature is the autonomous form everywhere, headers and commit messages alike.

## A quoted line must be the line the implementer wrote

A finding that quotes code is evidence only if the quote is from the file as the
implementer last saved it. Re-read the file, then cite `path:line` with the quoted
text actually present at that line; if the quote will not match, the finding is
`[INFERENCE]` and gets said so. A stale quote costs implementation a round trip to
fix nothing, and it buries the real finding beside it: one review quoted
`COMMON = list(capabilities.COMMON_MENU_ITEMS)` from a test module that never
contained that line, while the gap that mattered — a shared menu list with no
golden pin, one assertion away — had to be found again by the implementer.

The line number carries the same duty as the quote. A finding is read by someone
who will not open the file until they act on it, so `path:line` has to be where the
code actually sits — re-derived from that file, not remembered from a neighbouring
reading. One review placed `self.cbTS.cin.__del__()` at
`python/cinbase/__init__.py:3298-3299`; the call is at `:3297`, and the wrong pair
had already reached the round record before a grep corrected it.

## A comment that documents a divergence is a finding

`X says A although the code does B` is not an accepted state; it is a defect with a
paper trail. Treat it as a finding and ask for the decision record that tolerates
it. Three scan rounds of the Stroke table read *"big5S is listed although getCharSet
presently answers big5LF"* in the parked table's own generator and let it
stand: the comment reads as a known upstream limitation, no ADR recorded it, and no
test covered what it conceded — so the exclusion it described was inert while every
review treated it as settled. Accept the divergence only when a record names the
reason; otherwise the comment is the one thing the next agent trusts and nothing
asserts.

## A claim about the input data needs the measurement over it

What the code says is one thing; what a comment or a record says about the *data* the
code reads carries the same duty. `Because X does Y, this code handles it` either names
the file, the loader and what was counted, or it is `[INFERENCE]` and gets said so.
Round 5 of the parked 筆畫 effort shipped a code comment, a record paragraph and a
commit-message draft all asserting that CNS carries variant encodings, so one
character arrives through two
stroke orders — the stated reason `file()` keeps the shortest of two. Measured over the
pinned release with the generator's own loaders, 104,680 join rows give 104,680 distinct
code points and no code point is reached by a second 字碼: the case never occurs in
anything the product ships, the fold is defensive, and three artifacts had been read as
justifying code that is load-bearing. A reviewer that measures the inputs can tell the
two apart; one that trusts the prose cannot, and the next agent keeps the code believing
the prose.

## A regeneration-drift claim runs the generator

That a generated artifact drifted from its source — keys reordered, entries reshuffled,
counters off — is settled by running the committed generator over the source and
byte-comparing the output. For cinbase pairs the repo's sync test already does exactly
this (`tests/test_cinbase_tables.py` names `python/cinbase/tools/cintojson.py`), so the review's cheapest
move is running the tool or quoting that test. A drift claim the review did not run
stays `[INFERENCE]`: an imagined drift costs implementation measurement rounds to
refute.

## A mutation earns its place by naming what it reddened

``Eight mutations were run`` proves nothing; the assertion each one reddened is the
proof, so demand the pair — mutation, reddened test — and score a mutation with no red
as absence of evidence rather than as a check that passed. Round 5's harness files a
character under a key it is not a prefix of, to show the artifact test guards that chain;
the first attempt *moved* the chardef line instead of adding a second filing, so the
character kept one key, the chain held trivially, and it reported green in a column of
reds that meant something. Its harness aborts when a pattern does not match exactly
once, which is not the same as the mutation biting: a toothless mutation reads as
coverage, and nobody re-tests the assertion it appears to guard.

## A third-party return convention is quoted from the pinned source

When the diff branches on the return of a pinned third-party library (a ctypes
binding, a submodule), the implementation's premise and the reviewer's agreement
both cite that library's source at the pinned SHA, or the claim stays
`[INFERENCE]`. `git submodule status` names the checkout; a leading `-` means
initialize it first (`git submodule update --init <path>`). The #393/#417/#456
user-phrase fix hinged on this: most `chewing_*` setup calls return 0 for
success, while `chewing_userphrase_remove` returns rows deleted and 0 means
nothing was removed — a reviewer that accepted the analogy would have blessed
the success-default it was reviewing. The measured userphrase table lives in
`docs/agents/chewing-api.md`.


## A test that reads real OS state pins it at every read site

When an assertion depends on desktop state (`GetKeyState`, `GetAsyncKeyState`,
the clipboard), the pin must cover every site the product code reads it from,
activation included. Worked example: cinbase's `onActivate` copies the real
`GetKeyState(VK_CAPITAL)` into `capsStates`, while the small-letter test
patched `CinBase.getKeyState` only around the keystroke — with the physical
CapsLock on, activation cached True first and `'h'` came back `'H'`, red only
on days the shared desktop had CapsLock on. The fixed test builds the service
inside the patched window; the reviewer's check is that the patch covers every
read site, not just the obvious one.

## The standing rules: the fork's upstream prose, verbatim

§2–§4 of the agent rules upstream added to `AGENTS.md` in commit `487cb45`
(Hong Jen-Yee / PCMan), moved out of the always-loaded file on 2026-10-30 so
`AGENTS.md` keeps only its write-time floor and index. The prose below is
verbatim; judge every diff against **each** rule, and flag the breaks a gate
missed — a rule with no gate beside it is the reviewer's alone to enforce.
The build architectures, the Windows-10 floor and the comment-language rule
are stated once in `AGENTS.md`'s hard limits, so they are absent here by
design.

| Standing rule | Mechanical enforcement |
| --- | --- |
| Every added file's header carries its AI declaration | `check_ai_declarations.sh` (staged mode backs the pre-commit hook) |
| PR body carries the declaration, #996 three-way split | `check_pr_bodies.sh` |
| Commit message claims only its own diff | `check_pr_commit_claims.sh` |
| One topic per PR / branch scope | `check_pr_scope.sh` |
| No unhardened workflows on a pushed ref | `check_fork_ci_noise.sh` |

### 2. Modularity, Commits, and Pull Requests

- **CRITICAL - Small, Focused PRs (One Problem at a Time)**: This is the single most important rule. AI agents often bundle multiple disparate changes into unreviewable, monolithic PRs. You MUST prefer small, highly focused Pull Requests that solve exactly **one problem at a time**.
  - **Single Topic per PR**: Never bundle multiple unrelated bug fixes, features, or architectural adjustments into a single PR. If a task or issue involves multiple orthogonal areas, split them into independent, modular PRs. Small PRs ensure fast code review, easy rollback, and clear CI failure isolation.
  - **Granular, Incremental Commits**: Keep changes strictly scoped. Do not combine unrelated edits into a single commit. When a fix or feature spans multiple modules, break it down into logical, incremental commits where each commit handles an independent step.
  - **Strictly Reject Monolithic PRs**: Huge, kitchen-sink PRs will be strictly rejected during code review.
- **Isolate Renames and Moves**: Keep API renames or file moves/renames in their own dedicated commit/PR. Never mix renames or moves with new feature implementations or bug fixes.
- **Separate Features and Fixes**: Never mix bug fixes and new feature implementations. They must always be handled in separate commits and separate Pull Requests.
- **Commit & PR Message Style**: Apply the same concise style to both git commit messages and GitHub Pull Requests:
  - **Headline / Title**: The first line / PR title is a concise headline describing what it does. Include the bug/issue number if available.
  - **Blank Line**: (For commits) Follow the headline with a blank line.
  - **Body (Elaboration)**: If the headline/title cannot fully describe what it does, elaborate briefly in the body, using concise bullet points if needed. Avoid verbose boilerplate.
  - **Rationale (Most Important)**: Most importantly, explain *why* the change or fix is needed (if applicable; explain the motivation, context, or root cause).
  - Do NOT literally include labels or section headers like "WHAT:" or "WHY:" in the message.
  - **AI Declaration**:
    - **Commits & Pull Requests (Code)**: Distinguish the level of human creative contribution for code changes:
      - **Human-Architected / Supervised**: When a human author provided the design, architecture, API contract, or directed the triage:
        > `Architecture and design by <Author>. Implementation generated with AI assistance from <Agent> (<Model>).`
      - **Fully Autonomous**: When generated autonomously without human design intervention:
        > `Fully generated by <Agent> (<Model>) without human intervention.`
      - **Ambiguous / Undetermined**: If the prompt is brief and the agent cannot deduce whether the user considers the architecture theirs, **the agent must ask the user to clarify** before creating commits or PRs.
    - **PR Comments, Discussions & Issues**: The "Architecture and design" distinction applies strictly to code. For conversational comments, code reviews, and issue filings, simply append a concise footer declaration (e.g. `*(Review comment generated with assistance from Antigravity + Gemini 3.8 Flash)*`).

### 3. Coding Style & Language Guidelines

#### General Design & Architecture

- **Class Design & SOLID**: When adding new classes, prefer following the **SOLID** principles and favor **composition over inheritance**.
- **Functions & Modularity**: For non-class code, extract smaller helper methods/functions as needed. Prefer smaller, focused functions, and prefer pure functions wherever possible.
- **Readability Over Premature Optimization**: Focus on code readability and simplicity, unless a performance gain is obvious. For non-obvious optimizations, always add comments explaining the rationale.
- **API Documentation**: Prefer documenting public API usage (classes, methods, functions, and interfaces) with comments or docstrings.

#### Language-Specific Guidelines

Please stick to the existing coding style for each language in this repository:

- **C++**: Follow standard C++ memory management (use smart pointers where applicable). Respect the repository's formatting (check for `.clang-format`).
- **Rust**: Write idiomatic Rust. Always use `cargo fmt` and check against `cargo clippy`. Prefer robust error handling with `Result` over `unwrap()`.
- **Python**: For historical reasons, older Python APIs do not follow PEP 8. Keep the legacy naming conventions when interacting with existing code, but stick to PEP 8 in new code where possible. Prefer EAFP (Easier to Ask for Forgiveness than Permission) to write idiomatic, pythonic code rather than defensive checks (unlike C++).
- **Node.js**: Follow modern ES6+ syntax and adhere to the existing stylistic patterns in the `node/` directory.

### 4. Common Best Practices

- **Do No Harm**: Preserve existing docstrings, comments, and file structures. Do not delete code unless explicitly instructed.
- **No Placeholders**: Do not leave `// TODO` or `pass` stubs in generated code. Implement the full logic required for the task.
- **AI Authorship & Copyright in File Headers**:
  - **New Files**:
    - *Human-designed with AI implementation*: Include human copyright, credit human architecture, and note AI assistance (e.g. `PIMETextService/AsyncConnector.cpp`):
      ```cpp
      // Copyright (C) 2026 Hong Jen Yee (PCMan) <pcman.tw@gmail.com>
      //
      // API design and architecture by Hong Jen Yee (PCMan).
      // Implementation generated with AI assistance from Google Antigravity (Gemini 3.8 Flash).
      ```
    - *AI-generated, human-reviewed & integrated*: If no prior human design existed, but a human maintainer vetted and accepted the file, attribute the review and specify the project license:
      ```cpp
      // Reviewed and integrated by <Maintainer> <<email>>
      // SPDX-License-Identifier: LGPL-2.1-or-later
      //
      // Generated with AI assistance from Google Antigravity (Gemini 3.8 Flash).
      ```
    - *Fully autonomous / generated* (e.g. tests, lookup tables, scripts): Purely machine-generated code lacks human copyright; do not place a human copyright claim on unauthored code. Release under the project license or public domain:
      ```cpp
      // Generated by Google Antigravity (Gemini 3.8 Flash) without human creative authorship.
      // SPDX-License-Identifier: LGPL-2.1-or-later
      ```
  - **Modifying Existing Files**:
    - *Never remove, alter, or overwrite* existing copyright or license notices from original human authors.
    - *Routine fixes* (bug fixes, null guards, minor adjustments): **Do not modify the file header.** Document AI assistance solely in the git commit message.
    - *Substantial additions / major rewrites*: Keep the original copyright intact and append a short addendum below it acknowledging the addition, the human designer/reviewer, and the AI agent.
- **PR Review Comments & Issues**: Any comment, code review, or issue filed with AI assistance must include a footer declaration (e.g. `*(Review comment generated with assistance from Antigravity + Gemini 3.8 Flash)*`).
- **Unit Testing**: Add unit tests as appropriate. While much of the existing codebase is untested, newly written code—especially code generated by AI agents—is strongly encouraged to include unit tests.
