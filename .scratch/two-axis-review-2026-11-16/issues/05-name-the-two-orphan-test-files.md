# 05: Name the originating ticket for the two orphan test files

**What to build:** `tests/check_nsi_file_globs.sh` and `tests/test_shipped_payload.py`
each point at the ticket that asked for them, so a reader can tell a gate from a
stowaway.

Status: ready-for-agent
Category: enhancement
Blocked by: None

- [ ] Each file's header cites the ticket path under `.scratch/`
- [ ] That ticket names the failure class the file catches (`/x` and `/oname=`
      non-paths and `*.*` for the nsi pair; the shipped payload key set for the other)

## Comments

Both are mechanically adjacent to `a1bdc44`'s folder move, which is why they read as
untracked by the spec lists.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
