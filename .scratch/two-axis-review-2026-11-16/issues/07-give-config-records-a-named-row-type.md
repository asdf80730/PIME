# 07: A named row type for a `CONFIG_RECORDS` entry

**What to build:** the seven positions of a record are read by name, so
`checkConfigChange` and `shipped_defaults_for` stop indexing by place
(Primitive Obsession).

Status: resolved
Category: enhancement
Blocked by: None

- [x] One `namedtuple` (or dataclass) declares `key`, `default`, `control`,
      `table_affecting`, `mirror`, `effect`, `overrides`, and `CONFIG_RECORDS` is built
      from it in `python/cinbase/config.py`
- [x] `checkConfigChange` reads `record.table_affecting`, `record.mirror`, `record.effect`
      instead of `record[3]`, `record[4]`, `record[5]`
- [x] `test_cinbase_config_keys.py` stays at 12 tests OK, which is the `INV-02` pin over
      the nine shipped JSONs

## Answer

`010a09d` (`refactor(cinbase): give CONFIG_RECORDS rows a named ConfigRecord type`) is the
one commit; it touches four files, no harness path:

- `python/cinbase/config.py` — `ConfigRecord = namedtuple(...)` with the seven fields, and
  `CONFIG_RECORDS` built from it, so `docs/agents/cinbase-config.md`'s row shape has exactly
  one declaration (`INV-02`).
- `python/cinbase/__init__.py` — `checkConfigChange` reads `record.table_affecting`,
  `record.mirror`, `record.effect`.
- `python/cinbase/config/js/config.js`, `python/cinbase/configtool.py` — the two other
  readers of the row positions.

Settling, 2026-11-16 on this tree:
`python/python3/python.exe tests/run_worktree_tests.py tests/test_cinbase_config_keys.py .`
→ `Ran 12 tests ... OK`, which includes the fifth projection,
`test_every_record_key_is_read_by_the_engine`, the scan that makes a row no engine function
reads a red.

## Comments

`docs/agents/cinbase-config.md` fixes the row shape; the type is that one declaration
in code rather than a second prose copy.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
