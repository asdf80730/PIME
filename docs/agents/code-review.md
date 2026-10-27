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

## Fmt churn in a PR diff is scope creep

An upstream PR carries the smallest diff, so a hunk that is only `rustfmt`
reflow of code the change never functionally touches is **churn** — the
author ran the formatter crate-wide, not the tooling: the vendored rustfmt
disagrees with the runner's, and upstream files ride their own formatting
(`docs/agents/verification.md`, PR-worktree note). Flag every such file; the
fix is restoring it and re-running the formatter over the touched files
only. A diff where unrelated lines ride along breaks the reviewer's one
job: every line earning its review.
