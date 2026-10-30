# Input method tables (cinbase)

Consult when adding a table, re-deriving one, or touching anything under `python/cinbase/`.

## Pipeline

`.cin` source → converter → committed runtime JSON → engine.

- **Source of truth**: one `.cin` per table (CMIME format: `%ename`/`%cname`/`%selkey`, a `%keyname begin/end` block mapping each root key to its display glyph, and a `%chardef begin/end` block of `key<separator>root` lines). Sources live in the cinbase table source directory; the engine never parses them.
- **Converter**: `python/cinbase/tools/cintojson.py` — `cintojson.py <file.cin> [sort]` for one table, no argument for the whole batch. It writes compact JSON (`sort_keys`, no whitespace) into the cinbase `json/` directory. For tables outside the batch's `sortList` in the converter's `main()`, the candidate list order in the JSON is the `.cin` line order verbatim — an insertion's position is a product decision; `sort` instead merges the tier dicts (big5F → big5LF → … → privateuse).
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

### Stroke table (筆畫表) — parked

The generated Stroke table, the generator that derives it from the 全字庫 release,
the Service that ships it, and every test over it are parked on
`archive/chebihua-2026-10-29` rather than deleted: the maintainer does not want a
new input method in the product right now. What that branch's copy of this page
records, and what a revival has to follow, is the regeneration recipe (unzip
`Properties.zip` and `MapingTables.zip`, read the version out of `release.txt`, and
pass Windows-form paths because the bundled interpreter resolves a POSIX `/c/...`
argument against `C:\c`), why `--release` is not decoration (the release version is
quoted inside the 顯名聲明 the data licence requires, and `--emit-license` writes the
notice beside the JSON so the committed copy is never typed), the table budget
(`CLOSURE_TIERS`/`FULLCODE_TIERS`/`EXCLUDED_TIERS`, prefix closure only for the Big5
tiers, nothing past 30 strokes), and the rule that a character's tier is read from
which of the converter's tier dicts gained it — not from the name `getCharSet`
returns, because its Big5 符號 branch files in `big5S` and answers `"big5LF"`.

## 大易 canonical coordinates

For 校對 (auditing) `dayi3`/`dayi4` or re-deriving official codes, the reference is
the 太易資訊-licensed table — the Windows IME data cannot be mined from disk (the
built-in Traditional IMEs keep their dictionaries only as binary blobs under
`C:\Windows\System32\IME\IMETC\*.DLL`). Fetch from:

- Official licensed table, as distributed by gcin:
  `https://raw.githubusercontent.com/solomonhuang/gcin/master/data/dayi3.cin`
- Windows built-in 大易三碼 (plain-text archive, plus branch variants):
  `https://github.com/righthandabacus/dayi_table`, file `7_gcin-dayi-win.cin`

The #520 audit's cached `ref/` copies, machine-readable diff, and dated
write-up sit under the local-only `.scratch/upstream-bug-backlog/` — never
tracked, so the two URLs above are the fresh-clone path.

## Where a new table or Service has to register

Committing the pair is not the whole delivery. Everything else that has to know
the table exists:

- `python/cinbase/json/<stem>.json` is the only file the engine reads, and the
  installer copies `cinbase/` excluding `cin/`, so a committed pair ships with no
  installer edit (`installer/installer.nsi`).
- `python/cinbase/debug.py` — `jsonNameDict` maps a JSON name to the display name
  the debug log prints; without an entry the log shows the raw file name.
- `python/cinbase/configtool.py` — `CinDict` is the roster the settings tool
  resolves a Service's tables through; a Service missing there dies on open, and it
  is the only roster this tree carries. The Capability roster that gated per-Service
  behaviour switches (learning counts, 功能開關 menu items) arrived with the 筆畫
  effort and is parked with it on `archive/chebihua-2026-10-29`: reviving Intelligent
  select for a Service means reviving that roster module first.
- The settings dialog is split across two directories, and the route table in
  `python/cinbase/configtool.py` (`ConfigApp.__init__`) decides which one serves
  a request: `*.html` and `config.js` come from the Service's own `config/`, so
  `config.html` is per-Service and its `config.js` declares `imeFolderName`, the
  table list and `disableConfigItem`; `*.htm` and `css|fonts|images|js/*` come
  from `python/cinbase/config/`, which is where the shared
  `python/cinbase/config/js/config.js` and the `config.htm` fragments it loads
  into the page live. So a checkbox that behaves wrong for one Service is
  usually a bug in the shared script (it gates blocks on `imeFolderName`), not
  in the Service copy. `tests/test_config_tool_js.py` parse-checks both kinds
  with the shipped `node/node.exe` and fails when a `config.html` has no
  `config.js` beside it.
- `tests/ime_smoke_runner.py` and the expected-roster assertion in
  `tests/test_input_methods_smoke.py` — when the table reaches users through a
  Service directory under `python/input_methods/`.
- `tests/test_cinbase_tables.py` discovers pairs from `cin/`, so it needs nothing
  for a normal table; one generated on the user's machine at install time (like
  `liu`) goes into its `INSTALL_TIME_TABLES` instead, or the inventory test fails.
- `LICENSE.txt` — the root inventory entry, whenever the table derives from
  third-party open data and owes an attribution exhibit of its own: name the
  shipped table file, its origin, the licence, and where the exhibit ships. The
  exhibit itself ships as `python/cinbase/json/<stem>.LICENSE.txt`, a notice the
  table's own generator writes beside the runtime JSON, because the installer copies
  `json/` and excludes `cin/` and the converter gives the JSON no licence key.
  `installer/installer.nsi` installs `LICENSE.txt` into `$INSTDIR` with the payload
  (no extra wizard page), so the inventory reaches the user too;
  `tests/stage_installer.bat` stages it, like `version.txt` and `PSF.txt`.

The 全字庫 release the stroke table was built from sits unzipped under
`C:\Users\<user>\cns11643-opendata\` on the Windows box; re-download it when the
release version quoted in the `.cin` header has to change.
