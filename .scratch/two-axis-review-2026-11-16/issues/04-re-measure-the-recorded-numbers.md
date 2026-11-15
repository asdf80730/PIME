# 04: Re-measure the numbers the 2026-11-13 tickets recorded

**What to build:** every quoted count in the two 2026-11-13 efforts reproduces from a
named command at a pinned SHA, per "A quoted number must be reproducible".

Status: ready-for-agent
Category: bug
Blocked by: None

- [ ] `python/cinbase/service.py` reads 211 ln against the 213 recorded in ticket 01,
      or the record names the SHA its number came from
- [ ] `tests/gate_lib.sh` measured, against the 149 and 166 recorded in tickets 06 and 07
- [ ] The sourced-script tally measured, against the 39/40 recorded in tickets 06 and 07
- [ ] Ticket 05's "three new outcome tests" replaced by the file's own tally
- [ ] Ticket 03's "7 void hooks return the merge table" corrected: only `applyConfig`
      carries a `return`, and `handleRequest` drains `currentReply`
- [ ] The loader-trio citation in the ticket 06 record corrected to
      `python/cinbase/__init__.py:3458`, `:3537`, `:3588`
- [ ] `bash tests/check_line_citations.sh` exits 0 after the edits

## Comments

Each number is re-derived with `wc -l` or the suite's own `Ran N tests` line at the
close SHA, never carried over.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
