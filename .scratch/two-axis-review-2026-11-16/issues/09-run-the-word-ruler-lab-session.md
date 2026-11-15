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
- [ ] Same session, #859: Win+Shift+S, then Ctrl+V, then type Chinese once more
- [ ] Turn the second checkbox green in
      `.scratch/upstream-bug-backlog/issues/33-word-ruler-crash.md` and post the bilingual
      result on #883, zh-Hant first

## Comments

Silence window closes 2026-11-26; no reply closes #883 as `stale-unreproducible`. The
two owner sites are in place and were read from source:
`PIMETextService/PIMEClient.cpp:766-781` and
`PIMELauncher/src/backend_manager.rs:117-135`, `:251`.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
