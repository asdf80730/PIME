# 33: Word 拉動尺規立即當機 (upstream #883)

**What to build:** one dated beta retest of the ruler-drag sequence, then a close or a
fresh minimal repro — this is ticket 22's Word cluster, first row. The pipe/reconnect and
watchdog layers that own the symptom already got their 2026 fixes, which is why the
retest is the whole job.

**Blocked by:** None (can start immediately). Batch with tickets 02/22's lab session.

Status: ready-for-agent
Category: bug

- [x] Dated retest comment on #883 (beta version named), bilingual per house pattern
- [x] Pass → close; fail → minimal repro recorded here and a fixable ticket if the
      reconnect path is implicated — **fail**, minimal repro below, and the reconnect path
      is implicated (local ticket 11 of `two-axis-review-2026-11-16`)
- [x] Reply received inside the 14-day window → Status moves to `ready-for-agent`
      (fail, repro complete) or the issue is closed (pass / no reply)

**Minimal repro, human-observed on this desktop 2026-11-16 (`version.txt` =
`2.0.0-beta4`, host `10.0.26300.9974`), 新酷音 (McBopomofo) selected:**

1. Open a document in Word.
2. Type bopomofo and leave the composition unselected (candidate window showing).
3. Drag the ruler indent handle → the input stops answering for that window.
4. Recovery: close and reopen the Word document. Typing works again. The `PIMELauncher`
   is not restarted, and the other open windows keep typing normally.

Read together with the headless layer, the shape is one per-client row going stale while
the TSF document manager is rebuilt: the flush summary still answers
`sent=17 received=17 replies=17 mismatches=0` with `workerRestarts=0` and
`backendRestarts=0`, and the pipe client shows each client id getting its own replies, so
the launcher and the other clients are healthy while that one window is not.

## Comments

Owner sites, read from source: the reconnect-on-broken-pipe path
`PIMETextService/PIMEClient.cpp:766-781` and the watchdog pending purge
(`PIMELauncher/src/backend_manager.rs`, commit `7676819`, merged `31dec68`). Census
verdict `stale-unreproducible` (med conf); PCMan already asked the beta3 retest on
2026-10-17 (issue comment), reporter silent since. Smallest reproduction: the reporter's
own two steps — type in Word, drag the ruler indent handle — with pass/fail per beta.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*

**2026-11-11, omp (Qwen3.8-Flash-Next), Windows 11 ARM64 native box — HEAD
`2d160fe`, `cmd.exe /c ver` = `10.0.26300.9711`, installed payload
`C:\Program Files (x86)\PIME\version.txt` = `2.0.0-beta4`:** the dated bilingual retest
comment naming that beta is posted as
https://github.com/EasyIME/PIME/issues/883#issuecomment-6774634318. Native layer runs on
this box: `python/python3/python.exe tests/run_worktree_tests.py
tests/test_backend_resilience.py .` printed `Ran 9 tests in 0.448s` / `OK`, exit code 0
(the one skip is `test_backend_start_prunes_the_rime_directories_once`, `librime bindings
are not available`), and `cmd.exe /c "tasklist"` showed `PIMELauncher.exe` resident twice
on session 1 (PIDs 10608, 13512). The two layers the symptom hangs on are in place: the
reconnect-on-broken-pipe path at `PIMETextService/PIMEClient.cpp:766-781` and the watchdog
pending purge at `PIMELauncher/src/backend_manager.rs:237`/`:433`. **Blocked on the human
lab session (ticket 22):** the two reporter steps still need a person at this desktop —
(1) type Chinese in Word, (2) drag the ruler indent handle — with pass/fail recorded per
beta; the second checkbox turns on that result.

**2026-11-12, omp (Qwen3.8-Flash-Next), questionnaire sent — ticket 54:** posted as
https://github.com/EasyIME/PIME/issues/883#issuecomment-6826114513. **Who answers:** the
reporter @cgleework-coder, the only party whose desktop produced the symptom. **Payload
named in the send:** installed `C:\Program Files (x86)\PIME\version.txt` =
`2.0.0-beta4`, host `cmd.exe /c ver` = `10.0.26300.9711` (Windows 11 ARM64), integration
tree `2d160fe`. **What must come back** — five numbered items, none of which the local run
can answer: (1) pass/fail of the two reporter steps on beta4, (2) which recovery fires,
per-window reopen versus PIME Launcher restart, (3) whether the 「段落」dialog still works
where the ruler drag fails, (4) first drag or after several drags, (5) Office 2019 Standard
or 365 and whether Outlook shows it too. **Already tried, stated in the send so nobody
re-answers it:** `tests/test_backend_resilience.py` → `Ran 9 tests ... OK (skipped=1)`,
exit 0, plus both owner sites read from source (`PIMETextService/PIMEClient.cpp:766-781`,
`PIMELauncher/src/backend_manager.rs:237`/`:433`). **Silence window:** 14 days, replies due
2026-11-26; no reply closes the issue as `stale-unreproducible`, a fail with all five items
turns the second checkbox green and moves Status to `ready-for-agent`.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
