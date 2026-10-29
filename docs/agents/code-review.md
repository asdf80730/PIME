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

Stroke-table worked example: a ticket comment recorded "the 111,379 keys that lack
a prefix belong to 4,734 rare-plane-only characters". The shipped table measures
11,114 and 14,408. The prose read confidently, the numbers had been copied off an
unrelated probe, and only a reviewer re-running the query over the committed
`.cin` caught it.

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

`AGENTS.md` §4 grades a new file's header by its **category**: a script, a lookup
table or a test is machine-generated and carries the autonomous form (`Generated
by <agent> (<model>) without human creative authorship.` + SPDX); a
human-designed product file carries human copyright plus the design credit. Read
the category first, so demanding the human-design header for a generator tool, a
committed `.cin`/`.json` pair or a test module is a false positive. The design
credit lives in the commit message and the PR body, in whatever form the effort's
ticket records under `.scratch/<effort>/`.

Stroke-table worked example: a review flagged
`python/cinbase/tools/cnsstroke2cin.py` for the autonomous header because an ADR
recorded the design — an ADR describing an artifact's shape does not make the
file human-authored. The maintainer's standing choice for that feature is the
autonomous form everywhere, headers and commit messages alike.

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
presently answers big5LF"* in `python/cinbase/tools/cnsstroke2cin.py` and let it
stand: the comment reads as a known upstream limitation, no ADR recorded it, and no
test covered what it conceded — so the exclusion it described was inert while every
review treated it as settled. Accept the divergence only when a record names the
reason; otherwise the comment is the one thing the next agent trusts and nothing
asserts.
