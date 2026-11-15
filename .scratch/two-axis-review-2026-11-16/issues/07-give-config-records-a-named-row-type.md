# 07: A named row type for a `CONFIG_RECORDS` entry

**What to build:** the seven positions of a record are read by name, so
`checkConfigChange` and `shipped_defaults_for` stop indexing by place
(Primitive Obsession).

Status: ready-for-agent
Category: enhancement
Blocked by: None

- [ ] One `namedtuple` (or dataclass) declares `key`, `default`, `control`,
      `table_affecting`, `mirror`, `effect`, `overrides`, and `CONFIG_RECORDS` is built
      from it in `python/cinbase/config.py`
- [ ] `checkConfigChange` reads `record.table_affecting`, `record.mirror`, `record.effect`
      instead of `record[3]`, `record[4]`, `record[5]`
- [ ] `python/python3/python.exe -m unittest discover -s tests -p "test_cinbase_config_keys.py"`
      stays at 12 tests OK, which is the `INV-02` pin over the nine shipped JSONs

## Comments

`docs/agents/cinbase-config.md` fixes the row shape; the type is that one declaration
in code rather than a second prose copy.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
