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

Upstream issue #883; the retest lives in `.scratch/upstream-bug-backlog/issues/33-word-ruler-crash.md`
and both now carry the same minimal repro. Found by ticket 09's human lab session. The
bilingual retest comment is
[issues/883#issuecomment-6906934433](https://github.com/EasyIME/PIME/issues/883#issuecomment-6906934433),
posted 2026-11-16.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
