# Input method tables (cinbase)

Consult when adding a table, re-deriving one, or touching anything under `python/cinbase/`.

## Pipeline

`.cin` source → converter → committed runtime JSON → engine.

- **Source of truth**: one `.cin` per table (CMIME format: `%ename`/`%cname`/`%selkey`, a `%keyname begin/end` block mapping each root key to its display glyph, and a `%chardef begin/end` block of `key<separator>root` lines). Sources live in the cinbase table source directory; the engine never parses them.
- **Converter**: `python/cinbase/tools/cintojson.py` — `cintojson.py <file.cin> [sort]` for one table, no argument for the whole batch. It writes compact JSON (`sort_keys`, no whitespace) into the cinbase `json/` directory.
- **Runtime**: the engine loads only the JSON. The installer ships `json/` and **excludes** the `cin/` source directory, so a `.cin` edit alone changes nothing a user receives.

## Rules

- **Commit the pair.** `.cin` and its `.json` are always committed together; the JSON is what ships. `tests/test_cinbase_tables.py` regenerates every committed pair and fails on drift — edit the `.cin`, rerun the converter, commit both.
- **Table licenses live in the `.cin` head comments.** Provenance and license statements (Public Domain, GPL, OGDL…) are header comments of the source; the root `LICENSE.txt` additionally lists third-party data payloads. A table derived from government open data must carry that license's attribution exhibit verbatim in the header — for 政府資料開放授權條款‑第1版 the three-line 顯名聲明, whose omission voids the license ab initio.
- **Third-party data arrives via a dev-only generator** that emits a `.cin`, after which the standard converter path takes over. `python/cinbase/tools/liu_unitab2cin.py` (Boshiamy `.tab` → `.cin`) is the working example; Boshiamy is also the only table converted at install time, everything else ships pre-generated.

## CNS11643 open data (canonical coordinates)

Stroke-order and other attribute tables derive from the 全字庫 open-data release:
`https://data.cns11643.gov.tw/opendata/Properties.zip` (release index: `https://data.cns11643.gov.tw/opendata/release.txt`).

- `CNS_strokes_sequence.txt` — TSV `CNS字碼 <TAB> 筆順`, digits `1..5` = 橫豎撇點折.
- Join keys: `CNS2UNICODE_Unicode*.txt` TSVs under the release's MappingTables.
- Field spec ships inside the same zip (`全字庫屬性資料說明文件.txt`).
- Older citations pointing at `cns11643.gov.tw/AIDB/Open_Data.zip` are **dead links** (site rebuilt); rewrite them to the URL above.
