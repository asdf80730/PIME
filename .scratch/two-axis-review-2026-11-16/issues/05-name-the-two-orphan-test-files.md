# 05: Name the originating ticket for the two orphan test files

**What to build:** `tests/check_nsi_file_globs.sh` and `tests/test_shipped_payload.py`
each point at the ticket that asked for them, so a reader can tell a gate from a
stowaway.

Status: resolved
Category: enhancement
Blocked by: None

- [x] Each file's header cites the ticket path under `.scratch/`
- [x] That ticket names the failure class the file catches (`/x` and `/oname=`
      non-paths and `*.*` for the nsi pair; the shipped payload key set for the other)

## Answer

`e1e5631` (`docs(tests): name the originating ticket for the two orphan test files`) adds
one header line to each file, in the citation form `tests/check_scratch_refs.sh` accepts:

- `tests/check_nsi_file_globs.sh` → `# Ticket: .scratch/two-axis-review-2026-11-16/issues/05-name-the-two-orphan-test-files`
  (the dotted form, no trailing slash, which is what the scratch-ref scan matches).
- `tests/test_shipped_payload.py` → a `Ticket 05 ``name-the-two-orphan-test-files``` line in
  its module docstring; the `.scratch/`-prefixed spelling was turned in by
  `tests/check_scratch_refs.sh`, so the record form is the one that stays.

Settling: `bash tests/check_scratch_refs.sh` rc 0 and `bash tests/check_line_citations.sh`
→ `checked 281 citation(s)`, rc 0, both on this tree.

## Comments

Both are mechanically adjacent to `a1bdc44`'s folder move, which is why they read as
untracked by the spec lists.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
