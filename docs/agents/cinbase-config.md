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

## Adding a key is a quartet

A new setting touches four places, or it is silently half-dead:

1. key + default in `CinBaseConfig.__init__` (`python/cinbase/config.py`) —
   otherwise the attribute only exists when a JSON happens to define it;
2. the default in **all eight** `python/input_methods/*/config/config.json`
   (chearray, checj, chedayi, cheez, cheliu, chephonetic, chepinyin, chesimplex) —
   a key missing there never lands in the object for existing users, because
   layer 1's `__dict__.update` is the only place it gets applied; this is the
   eight-file trap;
3. a control in the shared config page `python/cinbase/config/config.htm`
   (scripted by `js/config.js` in the same directory);
4. for table-affecting values only: a `CinTable` mirror attribute + its
   `checkConfigChange` diff so the change triggers a reload.

`enableShiftSpace` in merged PR #1017 is the working example — its diff is exactly
`python/cinbase/config.py` + `python/cinbase/config/config.htm` + the eight shipped JSONs.

## Singleton caveat

Until upstream PR #1014 lands, each cin IME's `__init__` calls
`CinBaseConfig.__init__()` on the shared module instance and then
`copy.deepcopy()`s it (`python/input_methods/*/[ime]_ime.py`), which resets the
object the running config tool reads and races between reset and copy. Do not
add state that survives `__init__()` to this class; #1014 gives every IME its
own instance.
