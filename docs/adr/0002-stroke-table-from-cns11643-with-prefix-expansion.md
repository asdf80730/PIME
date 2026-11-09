# Stroke table derived from CNS11643, prefixes expanded offline

The 筆畫 (stroke) Service feeds cinbase a plain chardefs table, but cinbase matches compositions exactly (`cin.py isInCharDef` — `haveNextCharDef` is never called) while full stroke codes run 1–66 strokes long, and the established stroke table (rime brise
`python/input_methods/rime/brise/preset/stroke.dict.yaml`) was built for Rime's prefix-matching translator. We decided to derive the table ourselves from the CNS11643 全字庫 `CNS_strokes_sequence.txt` (OGDL-1.0, 1=橫 2=豎 3=撇 4=點 5=折, joined to Unicode via CNS2UNICODE) and have the offline generator emit **every prefix of every code as its own key**, so "candidates after any number of strokes" works with zero changes to the shared engine.

## Considered options

- **Copy brise `python/input_methods/rime/brise/preset/stroke.dict.yaml`** — rejected: it is a finished third-party table (upstream rime-stroke labels it LGPL-3.0) and copying a table is not deriving one; the CNS URL its AUTHORS cites is dead.
- **MOE 筆順網 / g0v zh-stroke-data** — rejected: the underlying MOE data is non-commercial-only.
- **Add prefix matching to the cinbase engine** — rejected: every cinbase-family IME shares that engine; an upstream PR touching it carries disproportionate risk for one small IME.
- **No expansion (exact codes only)** — unusable: a user would have to type all 66 strokes of 𪚥 before a single candidate appears.

## Consequences

- The generated table is large (prefix fan-out) but within committed precedent (`ezbig.json` 2.1 MB).
- OGDL-1.0 attribution (顯名聲明) is a validity condition, not etiquette: the three-line exhibit must reach the user's disk, or the license is void ab initio. Its carriers are the `.cin` header and — because the installer copies cinbase with `/x "cin"`, so a `.cin` never ships — a `json/<stem>.LICENSE.txt` notice beside the runtime JSON, both rendered by the generator from one function; `LICENSE.txt` is the inventory entry naming the table and where the exhibit ships, and the installer installs that inventory. The shipped half is pinned by the guard in `tests/test_cinbase_tables.py`.
- `maxCharLength` is capped at 30 strokes; ultra-long-code characters (up to 66) are deliberately unreachable, and no `t→h`/`d→n` key remaps ship in v1.
- 聯想字 stays off (`showPhrase: false`) and the wildcard is fixed to `*` (`selWildcardType: 1`), because `z` is the 折 root key and would shadow it.
