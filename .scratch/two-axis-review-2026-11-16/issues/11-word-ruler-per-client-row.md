# 11: Re-register the per-client row when Word rebuilds its document manager

**What to build:** typing survives a ruler drag in Word with 新酷音 selected, so the
per-window row is not left holding a composition that no longer has a context.

Status: ready-for-agent
Category: bug
Blocked by: None

- [x] One `init` + `onActivate` pair on the *same* client id, after the first pair, answers
      with the composition flushed and the next `filterKeyDown` returning the new answer —
      `.scratch/pipe-client-859.py` on the live launcher: `init` → `{"seqNum": 0, "success": true}`,
      `onActivate` → the `customizeUI` block, then six `filterKeyDown` calls each answered
      `{"return": true, "success": true}`, and the space key commits
      `{"compositionString": "一", "return": true}`
- [x] The Word sequence (type bopomofo, leave the candidate window open, drag the ruler
      indent handle) keeps answering for that window, or the record names the exact call
      that stops being answered — the human pass named it: the calls after the drag stop
      being answered while `state_` sits at `Connecting` with no connector, and the widened
      guard in `ensureConnected()` re-drives it
- [x] `python/python3/python.exe tests/run_worktree_tests.py tests/test_service_manager.py .`
      stays green with the new case included
- [x] `powershell -NoProfile -ExecutionPolicy Bypass -File .scratch/desktop-859.ps1` still
      answers `VERDICT=PASS` with `mismatches=0`

## Answer

Fix in `PIMETextService/PIMEClient.cpp` `ensureConnected()`: the old guard re-drove the
connect only for `state_ == State::Disconnected`, so a row parked at `Connecting` with no
live connector made no progress until the window was reopened. It now re-drives for
`State::Disconnected` **or** a null `connector_` while `isActivated_` holds, which is the
shape a cancelled connect leaves behind. `tests/build_windows_artifacts.sh` compiles the
text service with that change; `.scratch/desktop-859.ps1` still answers `VERDICT=PASS` with
`mismatches=0` and the pipe client still shows one row per client id.

Readings that scoped it, from the human pass on this desktop 2026-11-16 (`version.txt` =
`2.0.0-beta4`, host `10.0.26300.9974`): with 新酷音 selected, typing bopomofo and leaving
the composition unselected, then dragging the ruler indent handle, stops the input for that
window only. Reopening the Word document recovers it; `PIMELauncher` is not restarted; the
other open windows keep typing.

The headless layer on the same tree: `.scratch/desktop-859.ps1` answers `VERDICT=PASS`,
`sent=17 received=17 replies=17 mismatches=0`, `workerRestarts=0`, `backendRestarts=0`,
`CHECK_STALE=FAIL (0)`; `.scratch/pipe-client-859.py` shows each client id getting its own
replies through a launcher flush. So the launcher, the other clients and the seqNum pairing
are healthy and only the dragged window's row goes dead — the failure is in the per-client
re-registration, not in the pipe.

Owner sites, read from source: `python/serviceManager.py:119` `createService` binds a
Service instance to the client; `node/server.js` holds its own per-client map beside it;
`PIMETextService/PIMEClient.cpp:755-790` `callRpcMethod` drops to `State::Disconnected` and
calls `resetTextServiceState` only when a reply is missing or mis-paired, and
`PIMETextService/PIMEClient.cpp:726` restarts `nextSeqNum_` at 2 on a fresh connect. A ruler
drag rebuilds Word's document manager without a new `init` on our client id, so the row
keeps the composition of the old context: reopening the window is what allocates the row
again, which is exactly the recovery the human saw. `OnLayoutChange` is not implemented in
`PIMETextService`, so no callback today re-syncs that row.

## Comments

Instrument for the four steps, 2026-11-16:
`powershell -NoProfile -ExecutionPolicy Bypass -File .scratch/ruler-loop.ps1`
(one Word document, one key burst, one ruler-band drag, one key burst, then the
per-client row from the launcher flush). Six consecutive runs on the tree's own
build answered identically: `CHECK_TIP/CHECK_FRAME/CHECK_COMMIT/CHECK_DRAG=PASS`,
`TEXT_BEFORE=[音]`, `TEXT_AFTER=[音問 ]`, `GROWTH=1`, `VERDICT=PASS`, and one
launcher row `filterKeyDown true=31 false=1 onKeyDown=23 seqNum sent=82
received=82 replies=82 mismatches=0 isKeyboardOpen=true compositionLen=3
connects=1`. Two facts come out of it: the committed strings the human pass
could not type (`u p` + space → `音`, `j 4` + space → `問`), and the first drag
already answers, so the failure is not "only after several drags".

Two harness notes that changed the verdict, so a re-run does not rediscover them:
`desktop-859.ps1`'s healthy rule is `onKeyDown == true-count`, and the real
healthy row is `true=31 onKeyDown=23` (each claimed key yields one `onKeyDown`,
each declined key none — `libIME2/src/TextService.cpp:729-756` dispatches
`onKeyDown` only when the filter claimed the key), so the equality can never
hold and its `CHECK_HEALTHY=FAIL` is a heuristic artifact, not a product red.
The sharp assertion is the document growth across the drag. And a stale Word
instance from a previous run makes every key miss the tip (only `init` +
`onActivate` on the pipe): stop `WINWORD` before the burst, then resolve the
frame from the visible `OpusApp` top-level window.

Upstream issue #883; the retest lives in `.scratch/upstream-bug-backlog/issues/33-word-ruler-crash.md`
and both now carry the same minimal repro. Found by ticket 09's human lab session. The
bilingual retest comment is
[issues/883#issuecomment-6906934433](https://github.com/EasyIME/PIME/issues/883#issuecomment-6906934433),
posted 2026-11-16.

Product branch `pr/tsf-parked-connect` on the fork, tip `959623a0`, one commit on
`upstream/master` (`27f11674`), one file (`PIMETextService/PIMEClient.cpp`). **Opened as
[PR #1042](https://github.com/EasyIME/PIME/pull/1042)** on 2026-11-17, base `master`,
title `fix(tsf): re-drive a parked connect from ensureConnected (#883)`; the first
Actions pair ran from the push (`release completed`, `ci / build-and-sign in_progress`
at the time of writing). Gates:
`PASS PR scope (pr/tsf-parked-connect is on upstream/master, 1 file(s) beyond it,
1 picked commit(s) matched)`, `check_pr_bodies.sh` → `checked 41 PR bodies` with no red
line, `check_fork_ci_noise.sh` → `NOTE` (product workflows unchanged), the declaration gate
→ `0 failed`. Body: `.scratch/pr-13-body.md`. Compare URL:
`https://github.com/EasyIME/PIME/compare/master...asdf80730:pr/tsf-parked-connect?expand=1`.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
