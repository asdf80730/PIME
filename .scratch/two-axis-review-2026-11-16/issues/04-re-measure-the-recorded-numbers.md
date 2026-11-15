# 04: Re-measure the numbers the 2026-11-13 tickets recorded

**What to build:** every quoted count in the two 2026-11-13 efforts reproduces from a
named command at a pinned SHA, per "A quoted number must be reproducible".

Status: resolved
Category: bug
Blocked by: None

- [x] `python/cinbase/service.py` reads 211 ln against the 213 recorded in ticket 01,
      or the record names the SHA its number came from
- [x] `tests/gate_lib.sh` measured, against the 149 and 166 recorded in tickets 06 and 07
- [x] The sourced-script tally measured, against the 39/40 recorded in tickets 06 and 07
- [x] Ticket 05's "three new outcome tests" replaced by the file's own tally
- [x] Ticket 03's "7 void hooks return the merge table" corrected: only `applyConfig`
      carries a `return`, and `handleRequest` drains `currentReply`
- [x] The loader-trio citation in the ticket 06 record corrected to
      `python/cinbase/__init__.py:3448`, `:3527`, `:3578`
- [x] `bash tests/check_line_citations.sh` exits 0 after the edits

## Answer

`cdfc36a` (`docs(tracker): re-measure the numbers the 2026-11-13 records quote`) carries
every correction, each derived at that SHA and each naming the command:

- `wc -l python/cinbase/service.py` → 211; the record now says the 226/213 pair are
  per-commit readings and names the SHA each came from.
- `wc -l tests/gate_lib.sh` → 175, with the two earlier readings kept as such
  (149 at the `01d8c93` cutover, 166 after ticket 07's additions).
- `bash tests/check_gate_wiring.sh` → `wired 42 check script(s) in both directions`,
  which supersedes the 39/40 tally pair.
- The per-file tallies in the ticket 01 record are the `Ran 376 tests ... OK (skipped=3)`
  layer reading, quoted from the harness' own line rather than carried over.
- `python/cinbase/__init__.py` loader trio re-cited by `grep -n 'class CinTableBase'`,
  `class TableHolder`, `class TableLoadError` → 3448, 3527, 3578.
- `bash tests/check_line_citations.sh` → `checked 281 citation(s)`, rc 0.

## Comments

Each number is re-derived with `wc -l` or the suite's own `Ran N tests` line at the
close SHA, never carried over.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
