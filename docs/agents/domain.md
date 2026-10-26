# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root, or
- **`GLOSSARY-MAP.md`** at the repo root if it exists: it points at one `GLOSSARY.md` per context. Read each one relevant to the topic.
- **`docs/adr/`**: read ADRs that touch the area you're about to work in.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

This repo is single-context:

```
/
├── GLOSSARY.md
├── docs/adr/
│   ├── 0001-....md
│   └── 0002-....md
├── PIMETextService/
├── PIMELauncher/
└── node/ python/ go-backend/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_

## Record a decision once

A decision that outlives the change it accompanies — a support floor, a runtime version, a
rejected alternative — belongs in `docs/adr/` as its only statement. `AGENTS.md`, the research
notes and `GLOSSARY.md` point at the ADR; they do not restate its argument, because a restatement
is what has to be found and edited again when the decision moves. ADR-0001 is the shape: policy
here, pointer there.

Write the decision against what the tree ships, not what an open PR promises. A commit that
lowered the support floor to 8.1 on the strength of unmerged PRs had four files reverted within
the hour, once the payload was checked; a direction that depends on unmerged changes stays in the
research note as a pending or rejected option until the change lands.

