# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

## How a role is recorded locally

This repo has no tracker-side labels: the tracker is local markdown (see
`issue-tracker.md`). A role is written as the `Status:` line near the top of the
issue file, using the label string verbatim:

```markdown
Status: ready-for-agent
```

An issue with no `Status:` line is unlabeled and enters triage as `needs-triage`.

The category role (`bug` or `enhancement`) goes in a `Category:` line next to it:

```markdown
Status: ready-for-agent
Category: bug
```

Every triaged issue carries exactly one category role and one state role.
