# cinbase per-IME configuration

Reference when adding or changing a cinbase setting (the family tickets 12–20 of
`.scratch/upstream-bug-backlog/` all do). Facts pinned against `master` 2026-10-30.

## How a value resolves

`CinBaseConfig` (`python/cinbase/config.py`, module-level singleton at `:290`)
loads in two layers (`load()`, `:110-124`):

1. **Shipped defaults**: `python/input_methods/<ime>/config/config.json`, applied
   over `__init__()` defaults on every load (`getDefaultConfigDir()`, `:183-184`).
   This is the layer that reaches users who already have a personal config.
2. **User config**: `%APPDATA%\PIME\<ime>\config.json`
   (`getConfigDir()`/`getConfigFile()`, `:97-103`), with a legacy `~/PIME/<ime>`
   fallback.

Every table-affecting value is re-discovered by `checkConfigChange`
(`python/cinbase/__init__.py`) diffing `cfg` against the `CinTable` mirror
attributes — see ticket 05's Comments in `.scratch/upstream-bug-backlog/issues/`
for the loader-side surface and its pending fixes.

## Adding a key is one row

`INV-02` — the invariant list row in `docs/agents/invariants.md` is the sentence;
this section is its expansion.

Since ticket 02 of the 2026-11-13 architecture review, `CinBaseConfig` owns
ONE record list, `CONFIG_RECORDS` in `python/cinbase/config.py`. Each row is
`(key, default, control, table_affecting, mirror, effect, overrides)` and is
the whole declaration of a setting; every other copy is derived from it:

1. `CinBaseConfig.__init__` seeds each attribute from its row's `default` —
   the attribute always exists;
2. the shipped `python/input_methods/<ime>/config/config.json` of every
   Service is the deterministic writer `write_shipped_configs()`: row value =
   `overrides[ime]` or `default`, one key set for all Services, so the
   former eight-file trap is just this writer's per-`overrides` map
   (regenerate with `python/python3/python.exe` and the module's
   `write_shipped_configs()`; the committed files are its bytes);
3. the shared config page (`python/cinbase/config/config.htm` scripted by
   `js/config.js`) reads the list from the `records` and `selKeys` fields of
   the `/config` response (`python/cinbase/configtool.py`), so the script
   carries no restated defaults — a `control` of `"none"` means the key has
   no page control and none is expected;
4. for table-affecting rows only, `mirror` names the `CinTable` attribute
   `checkConfigChange` compares and `effect` its reload consequence, so the
   diff loop iterates the flagged rows instead of a hand-written sequence.

`tests/test_cinbase_config_keys.py` pins these derivations and stays green as
the single cross-file check. `keyboardLayout`, `colorCandWnd` and
`directCommitString` are the worked example: each was an orphan present only
in the shipped JSONs, and one row each brought it to the class, the JSONs,
the page, and the diff table.

## Singleton caveat

Until upstream PR #1014 lands, each cin IME's `__init__` calls
`CinBaseConfig.__init__()` on the shared module instance and then
`copy.deepcopy()`s it (`python/input_methods/*/[ime]_ime.py`), which resets the
object the running config tool reads and races between reset and copy. Do not
add state that survives `__init__()` to this class; #1014 gives every IME its
own instance.
