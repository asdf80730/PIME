# Which upstream issues are worth doing

Reference tree: `origin/master` = `b3c47ad865b2ef3e2bda321a04014074925a1da5`
(2026-10-25 01:24:06 +0000, "Merge pull request #1000 from EasyIME/fix/python-getasynckeystate-bitmask"),
fetched 2026-10-25. The analysis below was first written against `1586374` on 2026-10-20 and is
retained as that snapshot; every state and every "still present" claim was re-checked against
`b3c47ad` and live `gh` output on 2026-10-25. Upstream still has no `docs/` directory
(`git cat-file -t origin/master:docs` fails); this checkout's `master` carries local-only tests and
`docs/`.

This note ranks candidates in the recent window. For the full census of all 239 open
`bug`-labeled issues — age structure, per-issue verdicts, the 20 source-fixable defects —
see [upstream-bug-backlog-2026-10.md](upstream-bug-backlog-2026-10.md) (snapshot 2026-10-29,
`upstream/master` = `3697f88`).

Scope at the 2026-10-20 snapshot: all 351 open issues and the 18 open PRs in EasyIME/PIME, plus
every issue closed after 2026-07-20 (90 days), with a per-issue adjudication of the 14 issues PCMan
filed on 2026-10-17/18. "Suitable" here means: unclaimed (no open PR doing the same work), small,
and checkable from this Linux checkout or a Windows CI run — not "interesting". At the 2026-10-25
refresh the tracker held 345 open issues and 17 open PRs, and 54 items (11 issues, 43 PRs) had
changed since 2026-10-20.

What was executed: `gh api`/`gh pr`/`gh pr checks` enumerations, the `Cin` loader experiment in
§4.3, `python3 -m unittest discover -s tests -p "test_docs_pages.py"` (3 tests, pass, both on 10-20
and on 10-25), and `git show`/`git grep` on `origin/master`. Nothing was compiled.

## TL;DR

- PCMan's 2026-10-17/18 sweep is effectively closed out: **12 of 14 issues are closed** (#936,
  #937, #938, #939, #940, #941, #943, #951, #953, #956, #961, #966). #942 is addressed on master
  by #978/#979 (its PR #972 was closed as superseded), but the issue is still open and no reporter
  has confirmed the fix; #960 is the only defect with no fix on master, with draft #962 now `DIRTY`.
- The old top 3 all moved: #966 landed as #976 (10-24), #832 landed as #981 (10-25, but the issue
  is still open), and #502 is PR #982 (`MERGEABLE`/`CLEAN`, `ci / build-and-sign` and AppVeyor
  green, no review yet).
- #355 is now claimed by PCMan's #1004 (open, CI green). #951/#936/#937 closed when #952 and
  #945/#946/#971 merged on 10-25; #864/#627/#856 closed via #933–#935 on 10-24.
- Nothing unclaimed and locally actionable is left in the adjudicated set or the delta. The remaining work is review (#982, #1004)
  and close-out (#832, #942, #973, #203, #104), not a new patch.
- Two PCMan issues are still open but already implemented in-tree and should be closed, not
  worked on: #104 (libchewing pin is 0.5.1 since 2020) and #203 (installer has
  `CheckPendingFileRename` since `d76ed79`).
- New issue #973 (filed 10-20) is addressed by merged #988 (10-24); it remains open with no
  reporter confirmation, so it is another close-out, not a patch.

## Outcome (2026-10-25)

- **Landed:** #966 (#976, 10-24; competing #974 closed unmerged); #832 (#981, 10-25; issue still
  open); #936/#937 (#945/#946/#971, 10-25); #951 (#952, 10-25); #864/#627/#856 (#933–#935, 10-24);
  #942's fix (#978 on top of #979, 10-21; #972 closed as superseded); #973's fix (#988, 10-24;
  issue still open).
- **Claimed:** #502 → #982 (open, `MERGEABLE`/`CLEAN`, CI green); #355 → #1004 (open, CI green;
  see §4.3); #960 → #962 (draft, now `CONFLICTING`/`DIRTY`).
- **Blocked:** #895 is third-party `gcantonese`; #883/#862/#890/#859/#869/#511/#802 need a live
  Windows desktop; #960/#962 need Windows DPI verification; #1003 (rime lifecycle) needs a Windows
  backend. Other open PRs from the same window (#999, #1002, #1005, #1006) are self-contained and
  carry no open issue; #1002, #1005 and #1006 have green `ci / build-and-sign` and AppVeyor checks.
- **Left:** close-out only — #832, #942, #973, #203, #104 — plus review of #982 and #1004. No
  unclaimed coding candidate remains.
- [#1002](https://github.com/EasyIME/PIME/pull/1002) now covers the `unregister_client`
  pending-request purge open question from
  [launcher-reply-validation.md](launcher-reply-validation.md); the `seqNum`-drop question is still
  undecided and shares the same file, so it is deferred.

## Ranked candidates

Expected diff sizes are given in each §1 section, judged from the surrounding code and the existing
PRs. "PR?" is the state on 2026-10-20; the verdict is the state on 2026-10-25.

| # | Issue | Layer | Defect (one line) | PR? | Verdict (2026-10-25) |
|---|---|---|---|---|---|
| 1 | [#966](https://github.com/EasyIME/PIME/issues/966) | installer (NSIS) | Installer still probes for UC RT and downloads `vc_redist` on offline machines | #976 (merged) | **CLOSED** 10-24; #974 closed unmerged |
| 2 | [#832](https://github.com/EasyIME/PIME/issues/832) | docs | README build/install instructions contradict `build.bat` and the installer | #981 (merged) | **CLOSE** — fix merged 10-25; issue still open |
| 3 | [#502](https://github.com/EasyIME/PIME/issues/502) | repo meta | No issue template; reports arrive without version/log/repro | #982 | **REVIEW** #982 — clean, CI green |
| 4 | [#355](https://github.com/EasyIME/PIME/issues/355) | python (`cinbase`) | A bad table is swallowed and the IME dies silently | #1004 | **WAIT** — claimed by #1004 |
| 5 | [#942](https://github.com/EasyIME/PIME/issues/942) | C++ TSF | 9 s UI-thread stall on pipe connect | #978 (merged) | **CLOSE?** — fix merged in #978/#979; issue open, unconfirmed (Windows-only) |
| 6 | [#951](https://github.com/EasyIME/PIME/issues/951) | node | `loadServices` throws on a bad/missing `ime.json` | #952 (merged) | **CLOSED** 10-25 |
| 7 | [#936](https://github.com/EasyIME/PIME/issues/936) | node | No `uncaughtException` handler | #945, #971 (merged) | **CLOSED** 10-25 |
| 8 | [#937](https://github.com/EasyIME/PIME/issues/937) | node | Pre-init request dereferences `null` service | #946, #971 (merged) | **CLOSED** 10-25 |
| 9 | [#960](https://github.com/EasyIME/PIME/issues/960) | C++ TSF | Candidate window ignores per-monitor DPI | #962 (draft) | SKIP — C++ only; #962 now `DIRTY` |
| 10 | [#895](https://github.com/EasyIME/PIME/issues/895) | python (3rd-party) | Cantonese IME broken on Python 3.12 | — | SKIP — external |
| 11 | #864, #627, #856 | python (`cinbase`) | Config/table crashes with clean repros | #933–#935 (merged) | **CLOSED** 10-24 |
| 12 | #883, #862, #890, #869, #859 | TSF / libchewing | Real bugs, no Linux-side reproduction | — | SKIP — needs a desktop |
| 13 | #203, #104 | installer / submodule | Already implemented in-tree | — | CLOSE (both still open) |
| 14 | #838, #768, #765 | libchewing | Upstream library work | — | SKIP — upstream |

## 1. Top 3 recommendations

These three were the 2026-10-20 recommendations. None is a live "do now": #966 and #832 landed,
and #502 is waiting on review of #982. The text under each heading is the original analysis, with
a status line added for the refresh.

### 1.1 #966 — remove `ensureVCRedist` and the `vc_redist` download

**Status (2026-10-25):** #966 closed as completed on 2026-10-24T22:29:24Z. The work landed as #976
(asdf80730, merged 22:29:22Z) after draft #975; dannyward630's competing #974 closed unmerged.
`git grep -n 'VCREDIST\|vc_redist\|ensureVCRedist' origin/master` returns nothing, TODO markers
included.

- Issue: [#966](https://github.com/EasyIME/PIME/issues/966), PCMan, filed 2026-10-18, closed
  2026-10-24, no labels, 0 comments. Body is a four-item checklist: drop `Call ensureVCRedist`, drop
  `Function ensureVCRedist`, drop the `DownloadAndInstallVCRedist` macro, drop the
  `DOWNLOAD_VCREDIST_*` / `INST_VCREDIST_*` strings.
- Current state at `1586374`: unchanged. `installer/installer.nsi:238` is
  `Function ensureVCRedist`, `:288` is `Call ensureVCRedist`, `installer/macros.nsh:269` is
  `!macro DownloadAndInstallVCRedist`, and the three locale files define the strings at
  `installer/locale/English.nsh:19-21`, `SimpChinese.nsh:19-21`, `TradChinese.nsh:19-21`.
- The code already agrees with the issue: `installer/installer.nsi:239-242` carries
  `; TODO(#966): ... Remove this function and the DownloadAndInstallVCRedist macro in a separate
  PR.` and `:286-287` repeats `; TODO(#966): Obsolete VC++ redist check`. The prerequisites the
  issue cites are visible: static CRT (`CMakeLists.txt:7` sets `CMAKE_MSVC_RUNTIME_LIBRARY` to
  `MultiThreaded`), bundled Python ships `python/python3/vcruntime140.dll`, and `ucrtbase.dll` is
  not bundled because it is in-box.
- Why now: this is the only unclaimed issue in the sweep, PCMan wrote "in a separate PR" into the
  code, and the installer was under active refactor on 10-19 (#965, #967, #968, #969 all merged),
  so the file is warm and the change is mechanical.
- Patch size: ~95 deleted lines across 5 files (`installer.nsi:238-280` is the 43-line function,
  `:284-288` the call site, `macros.nsh:259-297` the 39-line macro, 3 strings × 3 locales). No new
  logic.
- Verification here: `tests/run_local_tests.sh` now assembles `installer/installer.nsi` with
  Debian's `makensis` 3.08 (see `docs/agents/verification.md`), so a broken script, include or
  LogicLib block fails locally; packaging still relies on the `build-and-sign` job (`makensis`
  step) on a branch, plus a static check that no reference survives:
  `git grep -n 'VCREDIST' -- installer/`.
- Duplication risk: low. Of the 18 open PRs, only draft #898 lists any `installer/` file, and no PR
  mentions `vc_redist` (`search/issues?q=repo:EasyIME/PIME+is:pr+vcredist` → 0). #898
  ("Replace NSIS with a monolithic WiX Bootstrapper") rewrites `installer/` and `README.md`, but it
  has not moved since 2026-10-16 — before the four NSIS PRs merged — so NSIS is still the live path.
  Say in the PR that it is intentionally NSIS-only.

### 1.2 #832 — make the build/install documentation match the tree

**Status (2026-10-25):** #981 merged 2026-10-25T00:33:30Z. `README.md` now names Visual Studio 2026
and the `Visual Studio 18 2026` generator, tells users to install/uninstall through the setup
program instead of copying DLLs or running `regsvr32`, and no longer mentions pywin32. Issue #832
itself is still open with 0 comments — close it; the drift described below is historical.

- Issue: [#832](https://github.com/EasyIME/PIME/issues/832), stanley50z, 2024-05-30, open,
  `enhancement`, 0 comments. The reporter wrote a walkthrough because "README 裡的安裝方法屢次出現
  問題" and ends with "可以 mark as completed"; nobody acted.
- The drift was verifiable by reading, all at `1586374`:
  - `README.md:20` and `:38`/`:42` told contributors to use `Visual Studio 2019` /
    `-G "Visual Studio 16 2019"`, while the documented one-command path `build.bat:1,6,11` used
    `-G "Visual Studio 18 2026"` for x86, x64 and ARM64.
  - `README.md:66-75` (install) and `:79-85` (uninstall) told users to copy/delete
    `PIMETextService.dll` by hand in `C:\Program Files (X86)\PIME\{x86,x64}` and run
    `regsvr32`, which is not how 2.0 installs (the NSIS installer registers the TSF service; the
    manual recipe would leave an unregistered or half-registered install).
  - `README.md:9` said "The python server part requires python 3.x and pywin32 package".
    `python/python3/requirements.txt` lists only `tornado>=6.0`, and
    `grep -rn 'win32api\|pywin32\|import win32' python/ --include=*.py` returns nothing.
- Why now: the build moved to the VS 2026 generator and the installer was rewritten in the last
  two weeks (#929 static CRT, #965 ARM64X, #967/#968 uninstall/registration); every one of those
  changes makes the README less true, and #480 asks the same deployment question from 2018.
- Patch size: one file, ~25 changed lines (`README.md`). Optionally `HACKING.txt`, which is
  currently accurate (it describes the Rust launcher and `node/test`) — leave it alone.
- Verification here: `python3 -m unittest discover -s tests -p "test_docs_pages.py" -v` (3 tests,
  pass today) does not cover the root README — it only walks `docs/` (`tests/test_docs_pages.py:16`)
  — so the real check is a by-hand comparison of the four claims above against `build.bat` and
  `installer/installer.nsi`. No workflow file changes, so the Bun YAML parse is not needed.
- Duplication risk: medium-low. No open PR references #832
  (`search/issues?q=repo:EasyIME/PIME+is:pr+%23832` → 0). Draft #898 edits `README.md` too; scope this PR to the
  requirements/build section and leave the install section to whoever lands #898, or state the
  conflict explicitly. No open issue claims it.

### 1.3 #502 — add an issue template that captures the data the fixes need

**Status (2026-10-25):** PR #982 is open, `MERGEABLE`/`CLEAN`, with `ci / build-and-sign` and
AppVeyor passing and no review yet. This is a review item, not a patch; the analysis below is the
2026-10-20 snapshot.

- Issue: [#502](https://github.com/EasyIME/PIME/issues/502), johnroyer, 2018-11-30, open,
  `enhancement`, 0 comments. "希望可以加上 issue template".
- Current state at `1586374`: `git ls-tree -r --name-only origin/master .github/` lists only
  `copilot-instructions.md`, `workflows/build-and-sign.yaml` and `workflows/ci.yaml`; there is no
  `ISSUE_TEMPLATE/` (and no `docs/` on upstream, so the docs workflow exists only in this fork).
- Why now: on 2026-10-17 PCMan re-triaged the old backlog that already carried
  `unable to reproduce` by adding the missing `bug` label in one pass — `labeled` events by him that
  day exist on
  [#12](https://github.com/EasyIME/PIME/issues/12), #18, #36, #46, #55 (`bug` + `chewing`), #610,
  #640 and #641 (`bug` + `chewing`), #696, #717, #731 and #748, and #752 (`bug` + `chewing`),
  #793. The reports that did get
  fixed fast are the ones that shipped evidence: #864's paste of the
  `[PIMELauncher] [error] [Backend error]` traceback (including
  `ValueError: invalid literal for int() with base 10:`) is what pins #933 to
  `python/cinbase/__init__.py`'s `candPerPage` conversion, and #691's report was only actionable
  after a retest request. A template that requires version, OS build, backend log and steps turns
  the next report into a ticket instead of a retest round-trip.
- Patch size: one new YAML file under `.github/ISSUE_TEMPLATE/` (~40 lines), no product code.
- Verification here: `bun -e 'Bun.YAML.parse(await Bun.file(".github/ISSUE_TEMPLATE/bug_report.yml").text())'`
  (`docs/agents/verification.md:96-97` uses the same trick for workflows); rendering itself can
  only be seen after pushing to a branch.
- Duplication risk: low. No open PR references #502
  (`search/issues?q=repo:EasyIME/PIME+is:pr+%23502` → 0), and the only open PR touching `.github/`
  at all is draft #898, which edits `build-and-sign.yaml`, not the issue templates. But this is
  still a maintainer-preference change — put the rationale in the PR body and keep it to one
  template rather than a `config.yml` + chooser.

## 2. PCMan's 2026-10-17/18 sweep, issue by issue

All 14 were filed within 30 hours (2026-10-17T18:21Z to 2026-10-18T23:37Z); 12 carry the `bug`
label, the other two (#960, #966) are defect reports without labels. Sorted by number; states are
the 2026-10-25 refresh, the evidence column is the 2026-10-20 snapshot at `1586374`.

| Issue | State (2026-10-25) | Fix | Evidence at `1586374` |
|---|---|---|---|
| [#936](https://github.com/EasyIME/PIME/issues/936) node: no uncaught handler | closed 10-25 | #945, #946, #971 merged | `node/server.js:1-34` has no `process.on('uncaughtException')` |
| [#937](https://github.com/EasyIME/PIME/issues/937) node: pre-init request | closed 10-25 | #946, #971 merged | `node/node_modules/nime/src/nimeServer.js:77-79` stores `{service: null}`; `requestHandler.js:43` default does not fire for `null`; `:51` dereferences it |
| [#938](https://github.com/EasyIME/PIME/issues/938) surrogate cursor | closed | #944 → `36d8d4f` | `PIMETextService/CompositionCursor.h:13-36` |
| [#939](https://github.com/EasyIME/PIME/issues/939) `wcsncpy` NUL | closed | #947 → `f47a912` | `PIMETextService/PIMETextService.cpp:258-259` |
| [#940](https://github.com/EasyIME/PIME/issues/940) `DllMain` lock | closed | #948 → `f23efd7` | `PIMETextService/DllEntry.cpp:25-31` lazy `getImeModule()`, `:41-52` `DllMain` no longer constructs it |
| [#941](https://github.com/EasyIME/PIME/issues/941) icon cache scope | closed | #949 → `d11dee4` | `PIMETextService/PIMEImeModule.h:55-57,65` owns `IconCache` |
| [#942](https://github.com/EasyIME/PIME/issues/942) pipe connect freeze | open (fixed on master) | #978 + #979 merged; #972 closed superseded | `PIMETextService/PIMEClient.cpp:799-801` still loops 3 × `connectPipe(..., 3000)`; `:772` is the `WaitNamedPipe` |
| [#943](https://github.com/EasyIME/PIME/issues/943) stale queue | closed | #950 → `9bd239c` | `PIMELauncher/src/backend_manager.rs:233-235` drains `stdin_rx`; `:384-390` discards messages from disconnected clients |
| [#951](https://github.com/EasyIME/PIME/issues/951) node loader | closed 10-25 | #952 merged | `node/loadServices.js:8,13-16,28-40` unchanged |
| [#953](https://github.com/EasyIME/PIME/issues/953) python discovery | closed | #954 → `24e4dff` | `python/server.py:80-92` loads `TextServiceManager` from `base_dir` inside `try/except` |
| [#956](https://github.com/EasyIME/PIME/issues/956) IPC buffer cap | closed | #957 → `b4465cf` | `PIMETextService/PIMEClient.h:83` `kMaxIpcMessageLength = 4 MB`; enforced at `PIMEClient.cpp:707` |
| [#960](https://github.com/EasyIME/PIME/issues/960) per-monitor DPI | open | #962 draft, `DIRTY` | `PIMETextService/PIMETextService.cpp:412-418` still `GetDC(NULL)` + `GetDeviceCaps(LOGPIXELSY)`; no `GetDpiForWindow` anywhere in `PIMETextService/` |
| [#961](https://github.com/EasyIME/PIME/issues/961) `nlohmann` escaping TSF | closed | #964 → `e62d7c6` | `PIMEClient.cpp:89-101` `is_object()` guard + `try/catch`; `:138,268,286,346` `is_object()` checks |
| [#966](https://github.com/EasyIME/PIME/issues/966) `vc_redist` | closed 10-24 | #976 merged | see §1.1 |

#942 is the one state that needs care: #972 was closed unmerged on 2026-10-22 as superseded by
#978 (on top of #979), so master now connects asynchronously, but the issue still has no closing
reference and remains open for a maintainer to close. #951/#936/#937 closed when #952 and
#945/#946/#971 merged on 10-25.

### 2.1 The three PRs on #936/#937

**Update 2026-10-25:** all three merged — #971 at 00:02:00Z, #945 at 00:46:57Z, #946 at 00:50:56Z —
and #936/#937 closed within minutes. #952 also merged (00:50:01Z). The review question below is
historical; no fourth PR was needed, and the merged #946 dummy service now coexists with #971.

`#945` (+5 lines, `node/server.js`) registers an `uncaughtException` handler; `#946` (+8 lines,
same file) returns a dummy service when `loadServiceById` yields `null`; `#971` (+24/-6 in
`nimeServer.js`, +94 in a new `node/tests/nimeServer.test.js`, and `package.json` test script)
answers `{success:false, seqNum}` from inside nime and wraps `JSON.parse` in `try/catch`.

At the snapshot, PR #971 was the only one with tests, and PCMan routed it for review
("could you help review nime server changes, please?" — [comment 2026-10-20](https://github.com/EasyIME/PIME/pull/971)).
Our own #955 (server.js, +29/-7) was closed on 2026-10-20 by us after #971 covered the same paths.

The maintainer's stated position mattered here: on #945 he wrote "Not sure if this is a right
change. If node crashes, that means the process is in an unexpected state. Crash and let it restart
is probably better." ([2026-10-18](https://github.com/EasyIME/PIME/pull/945)). He nevertheless
merged #945 as well, after #971 had softened the crash paths.

Two review facts worth stating if asked:

- #971 also fixes a latent framing bug: `line.split('|', 2)` at `nimeServer.js:69` drops
  everything after a second `|`, so a payload containing a pipe is truncated before `JSON.parse`.
- #952 did **not** cover the `guid` dereference: `node/server.js:20` does
  `tmpService['guid'].toLowerCase()` and `parseImeConfig` only requires `moduleName`
  (`loadServices.js` in the PR diff). An `ime.json` with `moduleName` but no `guid` still throws at
  `init` inside the `createServer` callback. That gap is now open PR #1006 (`ci / build-and-sign`
  and AppVeyor both pass), not a review comment on the merged #952.

### 2.2 #942 / #972

**Update 2026-10-25:** #972 was closed unmerged on 2026-10-22T05:53:40Z by its author as superseded
by #978 (merged 2026-10-21, on top of #979). The new `AsyncConnector` performs the pipe connect
and `init` handshake on a threadpool worker, while `Client::ensureConnected()` only starts that
work and returns `false`; the per-key UI-thread wait this issue describes is gone from master. #942
has no closing reference and is still open, so the remaining action is a close-out, not a review.

At the snapshot, PR #972 replaced the 3 × 3000 ms loop with a 200 ms `WaitNamedPipe`, stopped
retrying when the failure was not `ERROR_SEM_TIMEOUT` (i.e. the launcher was simply absent), and
backed off 1 s between attempts. It was `MERGEABLE`/`UNSTABLE` with only an AppVeyor result, and the
`ci / build-and-sign` job never reported on it; that review question is moot now that it is closed.

### 2.3 #960 / #962

PR #962 (+72/-40 `PIMETextService.cpp`, +10/-5 `.h`) is C++ and verifiable only on the Windows CI
job — the remaining sweep item whose patch shape (DPI helper + font rebuild) cannot be narrowed to a
Linux test at all, which is why it is not recommended for us. At the 2026-10-25 refresh it is a
draft and `CONFLICTING`/`DIRTY`; its earlier CI runs passed but the branch no longer applies.
Master still has `GetDC(NULL)` + `GetDeviceCaps(hdc, LOGPIXELSY)` at
`PIMETextService/PIMETextService.cpp:416-419` and no `GetDpiForWindow` call.

## 3. Fix patterns visible in the 90-day closed set

Useful when writing a PR into this repo:

1. **One issue → one small PR with the issue number in the title** (`fix(node): ... (#936)`), then
   the issue is closed in the same day. The 10-17 batch merged within 24 hours.
2. **Tests travel with the fix when the layer is testable**: #933/#934/#935 each add a
   `tests/test_cinbase_*.py`; #971 adds a `node --test` file. The C++ fixes (#944, #947, #948,
   #949, #950, #957) have none — they rely on the Windows build.
3. **Replies to user reports are bilingual, name the commit/PR, and ask the reporter to retest the
   released beta** — e.g. #893 ("fixed in commit 0dc301d7"), #904 (PR #905 + #913), #903 (PR #931),
   #691 ("如果已能正常開啟，我們將會關閉此 Issue"). Several such replies are marked as
   AI-assisted, so an AI-assisted PR is acceptable if the declaration is present (the standing rules in `docs/agents/code-review.md`).
4. **Closed-as-fixed does not always mean fixed in the reporter's build**: #893/#908/#904 were all
   closed against beta3, and #895's analysis (2026-10-19) shows the remaining Cantonese failure is
   a third-party `json.loads(..., encoding=...)` call under Python 3.12, not a PIME bug.

## 4. Rejected / not suitable, with reasons

### 4.1 Windows-desktop-only symptoms

- [#883](https://github.com/EasyIME/PIME/issues/883) (Word ruler crash), [#862](https://github.com/EasyIME/PIME/issues/862)
  (Ctrl+C/V dead in WeCom/Excel), [#890](https://github.com/EasyIME/PIME/issues/890) (Shift does
  not leave Chinese mode after a phrase list), [#859](https://github.com/EasyIME/PIME/issues/859)
  (Office + Win+Shift+S), [#869](https://github.com/EasyIME/PIME/issues/869) (許氏 keyboard),
  [#511](https://github.com/EasyIME/PIME/issues/511), [#802](https://github.com/EasyIME/PIME/issues/802):
  each needs a live TSF host to reproduce, and #883 is already parked on a beta3 retest request.
  No patch can be justified from this checkout.
- [#895](https://github.com/EasyIME/PIME/issues/895): PCMan's 2026-10-19 root-cause comment puts it
  in `gcantonese` (`json.loads(..., encoding=...)` removed in Python 3.9+), and the reporter filed
  it upstream (`tinycrate/gcantonese-ime#4`). Nothing to change in PIME; the crash half was
  #905/#964.

### 4.2 Claimed by an open PR

- [#864](https://github.com/EasyIME/PIME/issues/864) → #933 (also adds `tests/test_cinbase_cand_per_page.py`);
  [#627](https://github.com/EasyIME/PIME/issues/627) → #934; [#856](https://github.com/EasyIME/PIME/issues/856)
  → #935. All three **merged on 2026-10-24** and their issues closed the same minute; this group
  is done.
- As of 2026-10-25 the open claims are #502 → #982, #355 → #1004, and #960 → draft #962. #942's old
  claim (#972) was closed as superseded by merged #978. Do not open parallel PRs.

### 4.3 Real but blocked: #355

**Update 2026-10-25:** #355 is now claimed by PCMan's
[#1004](https://github.com/EasyIME/PIME/pull/1004) (open, `MERGEABLE`/`CLEAN`, `ci / build-and-sign`
and AppVeyor green), which rewrites exactly this loader (`python/cinbase/__init__.py` and all eight
CIN IME modules). Its completion callback still ends in `except Exception: pass`, so #1004 changes
the loading architecture but does not yet surface a failed table; the silent-death half of #355
remains open inside that PR. A competing patch would still collide, so wait for #1004.

**Update 2026-10-30:** the review landed — [comment on #1004](https://github.com/EasyIME/PIME/pull/1004#issuecomment-6506773490),
executed against head `b74d6a2` with the bundled Python 3.15.1 (PR suite `tests/test_cintablebase.py` 5/5,
#355's corrupt-table repro run against the PR tree). Four failure modes measured: the completion
callback still ends `except Exception: pass` (`cinbase/__init__.py:3401-3402`, no log line); the
`cin`/`wait()` surface of `CinTableBase` re-raises into the plain None-guards
(`:3292`/`:3299`/`:3324-3325`) and into the IME `__init__` `CinTable.wait()` (`checj_ime.py:65`) —
fatal, not visible; the config mirror written at submit (`:3389-3392`) makes a failed load
un-retryable via `checkConfigChange`; and a failed reload leaves the still-serving table with
`chardefs == {}` (`Cin.__del__` ran at submit, `:3386-3387`), i.e. zero candidates, no message.
The #355 merge condition (failed table visible — logged to `python_backend.log` and user-visible,
not fatal, retryable) is stated on the PR. Async loading itself is confirmed preserved: `start()`
submits and returns, and the busy-wait is gone in all 8 modules. #1004 remains OPEN as of this
writing; tickets 13–20 keep waiting on the merge-or-abandon, and no competing loader patch is
proposed yet — #1004 was opened 2026-10-25T03:44Z, five days ago as of this writing, which is
not yet "indefinitely" under the ticket's takeover condition.

[#355](https://github.com/EasyIME/PIME/issues/355) ("copying a `.cin` renamed to `.json` hangs the
system") still reproduces in kind. `Cin.__init__` does `self.__dict__.update(json.load(fs))`
(`python/cinbase/cin.py:55`), and the loader thread swallows everything:
`python/cinbase/__init__.py:3412-3413` is `except Exception: pass`, after `:3392-3393` has already
set `cbTS.cin = None` on failure. Executed on 2026-10-20 against the then-current `origin/master`'s
`cin.py`; that path is unchanged at `b3c47ad`:

```
renamed.cin -> JSONDecodeError : Expecting value: line 1 column 1 (char 0)
shape.json  -> constructed, chardefs = []
```

So the failure mode is no longer an OS hang but a silently dead table (and, for a structurally
valid but wrong-shaped table, an empty one). A proper fix means deciding what the loader should do
— retry, fall back to another table, or surface a message — which is exactly the file draft
[#917](https://github.com/EasyIME/PIME/pull/917) started reworking and #1004 now continues; #917's
review notes say "`__init__` now blocks until the cin table loads (defeats the loader thread…). Use
a `threading.Event` or keep loading async" and list six open design points. #934, which edited
`cin.py`, and #1004 both touch this path. Revisit after #1004 is either landed or abandoned.

### 4.4 Already implemented — close, don't code

- [#203](https://github.com/EasyIME/PIME/issues/203) (installer must honour
  `PendingFileRenameOperations`): still **OPEN** on 2026-10-25, but implemented by `d76ed79`
  ("Refactor installer logic into reusable macros and fix WOW64 registration") —
  `installer/macros.nsh:361-373` defines `CheckPendingFileRename` (reads
  `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager` and matches `$INSTDIR`), and
  `installer/installer.nsi:203` inserts it before installing. That is the behaviour the issue
  asked for; it only needs a close.
- [#104](https://github.com/EasyIME/PIME/issues/104) ("Upgrade to libchewing 5.0"): still **OPEN**;
  the submodule is pinned at `452f6221fbad90c0706a3963b17e226216e40dd7`
  (`git ls-tree origin/master libchewing`), whose `CMakeLists.txt:5` is
  `set(LIBCHEWING_VERSION 0.5.1)` (2020-06-27). The 5.0 upgrade is done; close the issue. "Latest"
  is tracked by [#838](https://github.com/EasyIME/PIME/issues/838) (2024) and
  [#765](https://github.com/EasyIME/PIME/issues/765) for rime.

### 4.5 Upstream library, not PIME

- [#768](https://github.com/EasyIME/PIME/issues/768) (`user_freq` going negative), #838, #765:
  the frequency bookkeeping is libchewing's; the 2023-08-26 comment on #768 says as much. A PIME
  patch would only move the pin.

### 4.6 Vague or question-only, no reproduction

- #446 (25 % CPU), #422 (gvim exit), #451, #658, #727 ("how do I write a node IME"): each body is
  a single sentence with no version, steps, or log, so there is nothing to patch or measure. They
  need a reproduction first, not a speculative fix.

## 5. Method and limitations

- The 2026-10-20 snapshot was enumerated with `gh api --paginate` on
  `repos/EasyIME/PIME/issues?state=open` (351 issues) and
  `.../issues?state=all&since=2026-07-20T00:00:00Z`; PRs with `gh pr list --state open` (18) and
  `gh api repos/EasyIME/PIME/pulls/<n>` for state, `mergeable_state`, `merge_commit_sha`, files.
  PCMan's set came from `search/issues?q=repo:EasyIME/PIME+is:issue+author:PCMan` (31 total,
  8 open, 14 in the 10-17/18 window).
- The 2026-10-25 refresh re-read every ranked issue/PR with `gh issue view`/`gh pr view` and
  `gh pr checks`, and scanned the delta with
  `gh api 'repos/EasyIME/PIME/issues?state=all&since=2026-10-20T00:00:00Z&per_page=100'`: 54 items,
  11 issues and 43 PRs. The only new open issue is #973 (filed 10-20); #977 and #983 were opened
  and closed. #973 is addressed by merged #988, so the delta contains no unclaimed candidate.
  The live counts at refresh were 345 open issues and 17 open PRs.
- "Still present" was decided by reading `origin/master` blobs at `1586374` via `git show`, then
  re-checked at `b3c47ad` for every item that still mattered. The executions were the `Cin` loader
  experiment in §4.3 (loaded `cin.py` by path with `importlib`, because `import cinbase.cin`
  pulls in `winsound`; run 2026-10-20, and the same swallow is still at
  `python/cinbase/__init__.py:3412-3413`), two `test_docs_pages` runs (3 tests, pass each time),
  and greps for `VCREDIST`, `GetDpiForWindow`, `uncaughtException`, `win32api`.
- Windows-only claims are read-only: `PIMETextService/` cannot be compiled here
  (`docs/agents/verification.md:98-102`), so #942/#960 conclusions rest on the diff and on which
  CI job is required, not on a run.
- Not verified: whether #962 changes behaviour on a mixed-DPI desktop; whether #973's reporter
  confirms the DACL fix; whether the maintainer wants #832/#942/#973/#203/#104 closed rather than
  kept open for a release note. #982/#1004/#1005/#1006 have green checks but were not reviewed or
  executed here; #1006's AppVeyor run was pending at fetch and passed afterwards.
- Timing: the tracker moved several times during this read (PR #971 gained its review request and
  our #955 was closed at 02:16 UTC on 10-20). Numbers and states are as of the 2026-10-25 fetch
  against `origin/master` = `b3c47ad`.
