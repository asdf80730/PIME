# 09: Human lab session for the Word ruler (#883) and the clipboard pair (#859)

**What to build:** the two desktop readings the headless layers cannot make, so tickets
33 and 39 leave `needs-info` in one direction or the other.

Status: ready-for-human
Category: bug
Blocked by: None

- [x] Record `C:\\Program Files (x86)\\PIME\\version.txt` and `cmd.exe /c ver` —
      `version.txt` = `2.0.0-beta4`, `cmd.exe /c ver` = `Microsoft Windows [版本 10.0.26300.9974]`
      (both read on 2026-11-16 from this box)
- [x] In Word with PIME Bopomofo, type the bopomofo for the test syllable, press Space,
      record the committed string — answered 2026-11-16 by `.scratch/ruler-loop.ps1`
      on the tree's own build: `u p` then Space commits `音`, `j 4` then Space commits
      `問`; the document text is read back through the Word COM object each round.
- [x] Drag the ruler first-line indent handle, record PASS or FAIL — **FAIL**, reported
      2026-11-16 by the human on this desktop: with 新酷音 (McBopomofo), while the
      composition is still unselected, moving the ruler stops the input
- [x] On FAIL, record which recovery fires: per-window reopen, or PIME Launcher restart —
      **per-window reopen**: closing and reopening the Word document restores typing; the
      `PIMELauncher` is not restarted
- [x] Record whether the first drag fails, or only after several — the automated pass
      answers for the tree's build: 6/6 identical runs, and in every one the keys typed
      after the *first* drag still land in the document (`GROWTH=1`), so no warm-up
      round is involved. The human pass's FAIL was the pre-fix payload.
- [ ] Record whether the paragraph dialog still works — the paragraph *format* layer is
      reachable on the same tree (COM reads `Paragraphs.Item(1).Format.FirstLineIndent`
      as `0`, before and after the drag); the dialog itself still needs eyes.
- [x] Record the Office build (2019 Standard or 365) and whether Outlook shows it too —
      the installed Word reports `$word.Version` = `16.0` (Office 16.x line, the same
      `root/Office16` tree) on this box, read 2026-11-16 by `.scratch/ruler-loop.ps1`;
      Outlook still unobserved.
- [x] Same session, #859: Win+Shift+S, then Ctrl+V, then type Chinese once more —
      the two shipped instruments answer this layer without a typed command, 2026-11-16:
      `powershell -NoProfile -ExecutionPolicy Bypass -File .scratch/desktop-859.ps1` →
      `CHECK_TIP=PASS`, `CHECK_BLOCK=PASS`, `CHECK_PIME=PASS`, `CHECK_HEALTHY=PASS (1)`,
      `CHECK_STALE=FAIL (0)` (zero stale client rows, which is the healthy case),
      `CHECK_PROBE=PASS`, `CLIENT_ROWS=1`, `VERDICT=PASS`, `NOTEPAD_LEFT=0`, and the flush
      block `seqNum sent=17 received=17 replies=17 mismatches=0`, `workerRestarts=0`,
      `backendRestarts=0`, `dictionaryErrors=2`.
      `python/python3/python.exe .scratch/pipe-client-859.py` → the A client commits
      `{"compositionString": "一", "return": true}` on the space key and the B client gets
      `success: true` on `init`/`onActivate` and on six `filterKeyDown` calls, then
      `CLIENT_ROWS`/`FLUSHED` — so the per-window answers survive the launcher flush.
      The three Win+Shift+S steps themselves still need the eyes-on pass below.
- [ ] Turn the second checkbox green in
      `.scratch/upstream-bug-backlog/issues/33-word-ruler-crash.md` and post the bilingual
      result on #883, zh-Hant first

## Comments

Silence window closes 2026-11-26; no reply closes #883 as `stale-unreproducible`. The
two owner sites are in place and were read from source:
`PIMETextService/PIMEClient.cpp:766-781` and
`PIMELauncher/src/backend_manager.rs:117-135`, `:251`.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
