# 09: Human lab session for the Word ruler (#883) and the clipboard pair (#859)

**What to build:** the two desktop readings the headless layers cannot make, so tickets
33 and 39 leave `needs-info` in one direction or the other.

Status: ready-for-human
Category: bug
Blocked by: None

- [x] Record `C:\\Program Files (x86)\\PIME\\version.txt` and `cmd.exe /c ver` —
      `version.txt` = `2.0.0-beta4`, `cmd.exe /c ver` = `Microsoft Windows [版本 10.0.26300.9974]`
      (both read on 2026-11-16 from this box)
- [ ] In Word with PIME Bopomofo, type the bopomofo for the test syllable, press Space,
      record the committed string
- [ ] Drag the ruler first-line indent handle, record PASS or FAIL
- [ ] On FAIL, record which recovery fires: per-window reopen, or PIME Launcher restart
- [ ] Record whether the paragraph dialog still works
- [ ] Record whether the first drag fails, or only after several
- [ ] Record the Office build (2019 Standard or 365) and whether Outlook shows it too
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
