# Upstream bug backlog — full inventory (2026-10)

Companion to [upstream-issue-triage.md](upstream-issue-triage.md): that note answers
"what is worth doing *now*" over the recent window; this one is the full census of every
open `bug`-labeled issue in `EasyIME/PIME` with an age structure and a per-issue status
verdict. Reference tree: `upstream/master` = `3697f88` (tip 2026-10-26, "Merge pull request
#999"), fetched 2026-10-29/30. Upstream is alive: 190 commits in 2026 to date, last
`ottokang` commit 2026-10-26 (commands for these figures in §8).

Snapshot: 345 open issues, of which **239 carry the `bug` label** (the census set). All
numbers below are from `gh api` enumerations taken 2026-10-29 and read-only `git` against
`upstream/master`; classification was produced by 10 parallel agents over the full corpus
(issue bodies + all 508 comment threads, fetched locally) and spot-verified by hand (see §8).

Execution order for this backlog is tracked as 22 tickets under
`.scratch/upstream-bug-backlog/issues/` (dependency-numbered; blockers first).

## TL;DR

- **The backlog is archaeology, not a queue.** 59% (140/239) predate 2020. 143/239 have had
  no comment since before 2021; 78 of the 140 pre-2020 issues got their last comment in the
  month they were filed. `updated_at` is useless here — PCMan's 2026-10-17/18 mass re-triage
  touched almost every issue with labels only (see triage doc §1.3).
- **Zero of the 239 are referenced by any upstream commit** (`git log` sweep, 2234 lines;
  the only hit, `#18`, is a 2013 commit predating the 2016 issue — false positive). So
  nothing in this set has a "fixed but forgot to close" commit trail; each close-out call
  below rests on source reading instead.
- **The genuinely actionable core is 20 issues**, and 11 of them sit in one file:
  `python/cinbase/__init__.py` (candidate-key handling). See §3.
- **112 are the close-out pile** — 90 closable with an evidence comment (19 likely-fixed,
  27 invalid, 11 user-config, 25 unreproducible-stale, 8 dead-architecture) and 22 too
  thin to judge without a reproduction — **16 belong to libchewing**, and **91 can only
  move on a live Windows desktop** (the 102-issue `needs-windows` join minus the 11 that
  already carry a verdict). §8 binds every bucket to one jq derivation.
- Two pre-2020 bugs are verifiably **still live and still reported in 2026**: #520 (大易三碼
  `tf8` 缺「續」— confirmed missing from `dayi3.json` chardefs today, §4.3) and #557
  (ARM64 — answered 2026-10-17 with beta3, awaiting reporter, §6).

## 1. Census and age structure

Filed-year distribution of the 239 (`gh api search/issues`), with true activity measured as
**last comment date** (repo-wide comments endpoint, 508 in scope):

| filed | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| issues | 21 | 65 | 26 | 28 | 17 | 8 | 27 | 17 | 23 | 3 | 4 |
| no comment after 2020 | 20 | 61 | 24 | 23 | 15 | 0 | 0 | 0 | 0 | 0 | 0 |

- 143/239 (60%) have no comment after 2020-12-31.
- 13 issues had comments in 2026: #520, #557, #689, #691, #748, #789, #802, #836, #839,
  #869, #883, #895, #942 — that is where the project currently actually talks.
- Label crossups inside the bug set: `chewing` 63, `cinbase` 51, `rime` 17,
  `unable to reproduce` 15, `upstream` 8, `wontfix` 2, `help wanted` 1.

Component attribution (agent-judged, from title/body/comments): `tsf-cpp` 71,
`python-cinbase` 48, `libchewing` 36, `python-other` 29, `python-rime` 14,
`launcher-legacy` 10, `installer` 8, `other`/`unknown` 16, `config-data` 5,
`launcher-rust` 1, `docs` 1. The `tsf-cpp` count is inflated by symptom reports whose root
could be anywhere below the DLL; only its code-verified entries are load-bearing.

## 2. Status verdicts (239, mutually exclusive)

| status | n | meaning |
|---|---|---|
| needs-windows-repro | 91 | plausible desktop symptom; cannot be proven or disproven from source |
| invalid-by-design | 26 | expected behavior, or mislabeled feature request |
| stale-unreproducible | 25 | `unable to reproduce` label or dead retest request (§5) |
| unclear | 22 | corpus too thin to judge (single-sentence reports, screenshots only) |
| still-present-code | 21 | defect visibly present on `upstream/master`, cited file:line |
| likely-fixed | 19 | current master addresses it; close after reporter retest (§4.2) |
| libchewing-upstream | 16 | root cause in the pinned libchewing 0.5.1 submodule (§7) |
| user-config | 11 | reporter's environment/config, not a PIME defect |
| obsolete-pre2 | 8 | targets deleted architecture (legacy C++ launcher, libIME-era callbacks) (§5) |

`act` (what should happen): close-out 93, needs-windows 102, **fixable-here 20**,
upstream-lib 16, dead 8.

Status × filed-year, selected (full matrix in `.scratch/upstream-bugs/joined.json`, the
`"\(.y)|\(.status)"` jq pass in §8): pre-2020 skews heavily to needs-windows-repro
(53/140) and stale/unclear (27/140 — 14 stale + 13 unclear); 2022–2024 skews to
needs-windows-repro as well (26/67); the fixable-here 20 span 2017–2024.

## 3. The 20 that can be patched from source today

Verified against `upstream/master` (agent citations; the marked ★ lines were re-checked by
hand). Four families, in descending patch coherence:

**3.1 cinbase candidate-key handling — 11 issues, one file (`python/cinbase/__init__.py`).**
The selection machinery hardcodes assumptions that each issue independently contradicts:

| # | (yr) | defect | locus |
|---|---|---|---|
| 463, 539 | (18, 19) | 選字鍵固定 `1234567890`，無 0 起編選項 | ★`:76` `candselKeys="1234567890"`, `:481-484` resets |
| 525 | (19) | 前導 `` ` `` 與大易快鍵「巷」衝突 | ★`:410` intercepts `` ` `` in Chinese mode, `:506` |
| 665 | (21) | 空白換頁與空白選字互斥（倉頡萬用字元） | `:1954`, `:1981` single `switchPageWithSpace` flag |
| 683 | (22) | 多鍵同按丟 keyup，`capsStates` 永久滯留 | only assigned `:196`, `:2559`; no per-keyup refresh |
| 710 | (22) | 行列30 需 Shift+數字才能選字 | ★`:2104` selKey branch gated on `isKeyDown(VK_SHIFT)` |
| 730 | (22) | NumLock 亮時 NumPad 數字無法選字 | ★`:367-370` NumLock-on pass-through before selection |
| 826 | (24) | Hold-Ctrl 標點吞掉 Ctrl 快捷鍵，無開關 | `:345`, `:1011` capture gated only on langMode |
| 438 | (17) | 「直接顯示候選清單」與翻頁挑選互斥 | `:1244`, `:1382`, `:1691`, `:1751` directShowCand |
| 394 | (17) | PuTTY 內 Shift 無法切中英 | `:2292-2304` toggle only in `filterKeyUp` |
| 639 | (21) | 「正在載入輸入法碼表」訊息亂竄 | `:436` |

One design question — *make selKeys/lead-key/paging behavior per-IME configurable* — closes
or shrinks most of this family at once. It is the single highest-leverage target in the
whole backlog, and it shares the file with #355 (loader rewrite claimed by PR #1004; triage
doc §4.3 — coordinate, do not collide).

**3.2 User-phrase editor debug prints — 3 issues, one root.**
`python/input_methods/chewing/config_tool.py:147` `print(chewing_ctx, ret)` and `:165`
`print("add", added, "remove", removed)` (★both re-checked; comment `# 0: error, 1: success,
default to success` follows). Printing non-BMP/non-console chars throws, aborting the delete
loop while the default reports success. Closes **#393** (2017, second-delete silently fails),
**#417** (2017, 罕用字刪除失敗恆稱成功), **#456** (2017, 詞庫刪不掉 POST 500).

**3.3 Data tables — 2 issues.**
**#520** (2019): ★`python/cinbase/json/dayi3.json` has `"tf8": ["績","纈"]`; 「續」 exists only
under `t8` — exactly the 2019 report, still true in the runtime table. Fix = repair
`cin/dayi3.cin` + regenerate `json/`, then audit the table as the reporter asked.
**#390** (2017): `cin/checj.cin:29487` maps `qnsm`→㤘 (忄部) where 扌部 is correct.

**3.4 python-rime — 3 issues.**
**#481** (2018): ★`python/input_methods/rime/ime.json` `"locale": "zh-Hans-CN"` — the rime
profile registers only under Simplified Chinese; a one-field fix.
**#403** (2017): `app_options` unhandled anywhere (`git grep` hits only a commented example
in `rime/data/PIME.yaml:6`).
**#445** (2017): `python/server.py:34-36` opens an unbounded append-only log; userdb growth
unpruned (950k-file report).

**3.5 One-off.** **#582** (2020): candidate font hardcoded 細明體 at
`chewing/chewing_ime.py:144` and `cinbase/__init__.py:3152`; no config path.

## 4. Close-out pile (112: 90 closable, 22 needing a reproduction)

### 4.1 Already answered by current master — close after a retest cycle (19, likely-fixed)

| group | issues | basis on master |
|---|---|---|
| backend-death / kill-python family | #131, #291, #292, #365, #375 | Rust launcher watchdog restarts hung backends, `PIMELauncher/src/backend_manager.rs:225-228,406-431` — all reports predate the 2026-04 rewrite; retest on beta3 then close |
| UILess games | #185, #199 | ★`isUiLess` exposed at `PIMETextService/PIMEClient.cpp:705`; cinbase honors it (`cinbase/__init__.py:435,512`) |
| installer/locale | #203, #506 | `installer.nsi:201-207` PendingFileRename check (triage §4.4); `en_US/ieprotectedpage.ini` gone |
| chewing features | #478, #725, #719, #789, #802 | export/import `config_tool.py:185-228`; autoLearn toggle `chewing_config.py:47`; config.json fix `eca76915`; paging fix PR #809 (`2efd45e`) |
| misc | #483, #557, #689, #691, #942 | simplex `io` now contains 次; ARM64 in beta3 (awaiting reporter); embedded-Python `_pth` isolation; tornado pin; AsyncConnector (triage §2.2) |

### 4.2 Already-fixed suspects needing a Windows retest before closing (4 — a subset of §4.1's 19, not an addition)
#131/#291/#292/#185 are counted above but their verdict leans on the Rust rewrite's watchdog;
they need one human beta3 session each before anyone presses *Close*. In the join these
four carry `act: needs-windows`; §4.1's other 15 carry `act: close-out`.

### 4.3 Dead architecture — close with a comment (8, obsolete-pre2)
#168, #37 (libIME-era callback/compose paths replaced by RPC dispatch,
`PIMEClient.cpp:521-638`); #374, #451, #489, #538, #540 (legacy C++ PIMELauncher — master's
`PIMELauncher/` is Rust-only, `src/*.rs` + `Cargo.toml`); #763 (tray/`WM_TASKBARCREATED`
code no longer exists post-rewrite). All describe killing/restarting the pre-2026 launcher.

### 4.4 Invalid (27) and user-config (11)
Invalid: #389, #388, #378, #336, #421, #397, #477, #465, #517, #509, #499, #543, #542,
#529, #527, #671, #607, #599, #588, #742, #741, #727, #716, #895 (→ gcantonese, triage
§4.1), #830, #829, #373 (mislabeled feature requests — #373 asks for UZIM-style reverse
lookup in chewing; `imeReverseLookup` exists only in cinbase,
`python/cinbase/__init__.py:118,1767`). User-config: #391, #428, #407, #435, #547,
#530, #817, #814, #762, #759, #753.

### 4.5 Stale unreproducible (25)
The 15 `unable to reproduce`-labeled issues (#12, #18, #36, #46, #55, #235, #610, #640,
#641, #696, #717, #731, #748, #752, #793) plus 10 with dead retest threads (#359, #317,
#475, #493, #491, #556, #552, #534, #883, #836 — 23 of these carry `act: close-out`,
#883/#836 carry `act: needs-windows`). House pattern (triage §3.3): bilingual
retest request against the current beta, close if silent.

### 4.6 Unclear (22)
#269, #115, #432, #419, #416, #396, #467, #455, #513, #508, #487, #480, #479, #658, #598,
#583, #577, #740, #721, #780, #843, #819 — one-sentence or screenshot-only reports. Nothing
to patch; they need a reproduction, not a fix (triage §4.6 says the same about its
subset; 17 carry `act: close-out`, #419/#416/#721/#780/#843 carry `act: needs-windows`).

## 5. Longevity outliers

Pre-2020 issues that still have a pulse (last comment ≥ 2024):

| # | filed | last activity | state |
|---|---|---|---|
| #520 | 2019-03 | 2026-02 (off-topic; defect confirmed live, §3.3) | **the oldest verifiably real bug in the tree** |
| #557 | 2019-11 | 2026-10-17 (PCMan: beta3 ships ARM64 native; awaiting reporter) | close-out pending retest |
| #131 | 2016-07 | 2024-06 (40 comments, Win7→Win11) | likely-fixed via watchdog, retest then close |
| #375 | 2017-05 | 2024-02 | same family |
| #463 | 2018-01 | 2024-02 | 嘸蝦米選字鍵 0-起編 — fixable §3.1 |
| #509 | 2019-01 | 2024-10 | invalid-by-design (chewing punctuation behavior) |
| #539 | 2019-06 | 2024-02 | fixable §3.1 |

## 6. Windows-only mountain (91 + 11 needs-windows retest)

Clusters, for whoever gets a lab machine: Word/Office input death and ruler-drag crashes
(#770, #772, #778, #862, #859, #850, #841, #840 … — #836 and #883 sit in this pile but
carry their stale-retest verdict in §4.5); fullscreen-game/UILess (#185 and friends —
verdicts in §4.1/§4.2); Line/gvim/PuTTY per-app key-routing (#422; #396's verdict is
§4.6, and #394 was adjudicated fixable in §3.1, so it belongs to the ticket queue, not
the lab). The pure `needs-windows-repro` members beyond those cannot be adjudicated from
this checkout — same stance as triage §4.1.

## 7. libchewing block (16)

#117, #157, #361, #363, #411, #549, #585, #682, #685, #715, #736, #760, #768, #858, #869
(+ #765, librime). Root cause sits in the submodule pinned at 0.5.1 (2020-06-27, triage
§4.4); the only PIME-side lever is moving the pin — tracked by #838. Two worth watching:
#715 (user dictionary >66k phrases makes the editor hang — also hits PIME's `config_tool`)
and #736 (DVORAK 許氏 mismaps `S`→`;` — plausibly a PIME key-routing layer too; the agent
kept it upstream with med conf).

## 8. Method and limitations

- Enumeration: `gh api search/issues?q=repo:EasyIME/PIME+type:issue+state:open+label:bug`
  (3 pages, 239); full bodies via `repos/EasyIME/PIME/issues?labels=bug`; 2161 repo comments
  via `issues/comments?per_page=100 --paginate`, joined by `issue_url` (coverage: 508/508 of
  the census comment counts). Age/activity/git-reference stats are deterministic jq/grep.
- Partition of the 239 — the numbers §2/§4/§6/§7 quote:
  `jq -r '.[] | "\(.act)|\(.status)"' .scratch/upstream-bugs/joined.json | sort | uniq -c`
  gives needs-windows 102 (91 `needs-windows-repro`, 4 likely-fixed, 2 stale, 5 unclear),
  close-out 93 (26 invalid, 23 stale, 17 unclear, 15 likely-fixed, 11 user-config,
  1 `still-present-code` — #373, a mislabeled feature request, filed at §4.4), dead 8,
  upstream-lib 16, fixable-here 20; 102+93+8+16+20 = 239.
  The same command with `"\(.y)|\(.status)"` gives the year matrix behind §2's skew
  line. Activity figures: the per-year "no comment after 2020" row and the
  78-of-140 last-comment-in-filed-month count join `full_all.json`'s
  `created_at[:7]` to `joined.json`'s `lc` on `number`. Upstream-activity claims:
  `git rev-list --count --since=2026-01-01 3697f88` → 190;
  `git log --author=ottokang --format=%ci -1 3697f88` → 2026-10-26;
  `gh api "search/issues?q=repo:EasyIME/PIME+type:issue+state:open" --jq .total_count` → 345.
- Classification: 10 parallel agents, slices of 20–26 issues, each embedded corpus
  self-contained (no network), every still-present/likely-fixed claim required to cite a
  `git show`/`git grep` on `upstream/master` run in-session.
- Spot-checked by hand this session and found accurate: cinbase `:76/:410/:481-484/:506`,
  `:345/:1011`, `:367-370/:2104`; `config_tool.py:147/:165`; `dayi3.cin` `tf8`/`t8`;
  `dayi3.json` `"tf8":["績","纈"]`; `rime/ime.json` locale; `PIMEClient.cpp:705` isUiLess.
- Confidence spread over the 239: high 45, med 90, **low 104** — low is concentrated in the
  pre-2020 needs-windows/unclear buckets, where no source-level verdict is possible. Treat
  §3–§4 as load-bearing and §6 as descriptive.
- Not covered: open non-`bug`-labeled defect reports (e.g. #960 DPI, #966-era installer, all
  covered by triage doc); issues closed before the snapshot; libIME2/libchewing submodule
  interiors (not greppable from the superproject).
