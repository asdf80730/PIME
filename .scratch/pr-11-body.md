fix(cinbase): fullshape letters on the shift-to-English path (#890)

Fixes #890 — follow-up on the shift-letter switch of #1013.

The three shift-letter exits of `filterKeyDown` in `python/cinbase/__init__.py`
built CommitStr straight from the halfshape charStr, so with fullshape
selected the letter committed in halfshape while the same key on the ordinary
path committed fullshape.

- All three sites now read the fullshape form through `charCodeToFullshape`
  when shapeMode is FULLSHAPE_MODE.
- The small-letter upper/lower handling and the composition-buffer branch
  are unchanged.

Validation:

- `python/python3/python.exe` `-m unittest discover -s tests -p "test_cinbase_shift_to_english.py"`
  on the integration tree carrying this diff: `Ran 9 tests ... OK` — the
  fullshape form is the one the shift-letter exits commit.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
