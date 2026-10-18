# Launcher reply validation in PIME 2.0

This note answers four reply-side questions left open by
[input-request-lifecycle.md](input-request-lifecycle.md). The wire framing, spawn path, and request
flow are described there and are not repeated here. Scope is the reply direction only: backend
stdout → launcher → TSF.

Nothing was executed. This checkout is Linux and the product is Windows-only
(`docs/agents/verification.md:1-3`); every claim below comes from reading the source in this
checkout, including the existing tests and `git log`/`git show`. Test intent is read from test code,
not from a run.

## TL;DR

- The launcher never compares the `seqNum` a backend echoes with the one it forwarded.
  `extract_seq_num` is used at exactly two sites in the launcher's routing path: to insert a pending key before writing
  (`PIMELauncher/src/backend_manager.rs:381-384`) and to remove it when a reply arrives
  (`backend_manager.rs:316-319`). Routing is by `client_id` alone
  (`backend_manager.rs:323-334`). Enforcement is in C++ (`PIMETextService/PIMEClient.cpp:751`).
- A wrong or missing echo fails the C++ call, nulls the response, closes the pipe, and clears
  language-bar state (`PIMEClient.cpp:751-766`, `838-864`). The launcher-side pending entry is not
  removed by the wrong echo, so unless a later reply carries the right one, the 15 s watchdog kills
  and restarts the backend (`backend_manager.rs:409-421`, `228-232`).
- The `"method":"close"` branch (`backend_manager.rs:340-349`) only chooses a log level. Its
  `debug!` arm is reachable only when the client has already been unregistered and the payload
  contains the exact compact substring. Python, Node/nime and Go all reply to `close` without a `method` field, so they
  hit the `warn!` path; only `PIMELauncher/src/bin/mock_backend.rs` emits the matching shape.
- `readBuffer_` persists between calls and is cleared only by `closeRpcConnection`
  (`PIMEClient.cpp:718-728`, `854-864`). Any extra line the launcher forwards—duplicate, late, or
  unsolicited—can be consumed as the next reply; a subsequent `seqNum` mismatch then takes the
  close/reset path. #943 can replay stale requests into a restarted backend, but a fresh UUID per
  pipe connection (`PIMELauncher/src/pipe_server.rs:109`) keeps their replies from reaching a live
  client.
- Both 15 s constants are real and deliberately matched: C++ uses 15 s only for `init` and
  `onActivate` (`PIMEClient.h:82`, `PIMEClient.cpp:418`, `654`), the launcher uses 15 s for its
  pending-request watchdog (`PIMELauncher/src/protocol.rs:8`,
  `backend_manager.rs:409-421`). The commit that introduced the C++ constant says it was chosen
  "matching PIMELauncher's hang timeout" (`79abda2`).

## 1. Reply-side `seqNum`: a liveness ledger, not a validator

**Answer.** The launcher uses the echoed `seqNum` only as a key to delete a pending liveness
timestamp; it never compares it with the request. A mis-echoed reply is still forwarded to C++,
which detects the mismatch, nulls the response, closes the pipe, and resets state. The router/
validator split is deliberate; the absence of a launcher-side drop is an untested gap.

### What the launcher does with the echo

The backend line is parsed once, in `forward_outputs_to_client`:

- `PIME_MSG|` and the client id are stripped by `parse_backend_output`
  (`PIMELauncher/src/protocol.rs:35-40`; call site `backend_manager.rs:312-314`). Lines without the
  prefix are dropped at `:312-314`.
- `extract_seq_num` parses the payload and returns `Option<i64>`
  (`protocol.rs:49-56`). If present, the launcher removes the exact key
  `(client_id, seq_num)` from `pending_requests` (`backend_manager.rs:316-319`). The `remove`
  result is discarded: absence is not an error and is not logged.
- The payload is then routed to `state.clients[client_id]` regardless of what was removed
  (`backend_manager.rs:323-334`). If the client is missing, the payload is dropped with a warning
  (`:340-349`). If the client is slow to drain, it is removed after a 500 ms send timeout
  (`:332-338`).
- Every line sent to the backend's stdin channel is inserted into the pending map when the input
  loop dequeues it, provided it contains a numeric `seqNum` (`backend_manager.rs:381-384`). Client
  requests always carry one (`PIMEClient.cpp:740-741`), and `ClientEntry.last_seq_num` is updated
  (`:386-389`). The launcher's own close notice also carries one, computed by `unregister_client`
  (`:91-104`); it goes to the same `stdin_tx` (`:143-163`), and the input loop inserts the close's
  key even though the client entry was already removed. The map is created once per backend
  *process instance* (`:190-191`), so a restart starts with an empty ledger.

The pending map is read only by the watchdog: every second (`backend_manager.rs:369`) it checks
whether *any* value is at least `HANG_TIMEOUT` old (`:411-414`), and if so kills the process and
returns `BackendExitReason::Error` (`:415-421`). There is no reply-vs-request comparison anywhere in
`PIMELauncher/src`; the two `extract_seq_num` call sites above are the whole use of the echoed value
in `backend_manager.rs`.

`last_seq_num` is a separate use of the request-side value: it mints the `seqNum` of the synthetic
`{"method":"close",...}` sent when a client unregisters (`backend_manager.rs:91-104`). It is not
used for validation either.

### What C++ does on a mismatch

`callRpcMethod` owns the request counter and the check:

- The request gets `seqNum = nextSeqNum_++` (`PIMETextService/PIMEClient.cpp:740-741`) and is
  serialized (`:743`); `callRpcPipe` adds the newline (`:704-706`). The reply is parsed after the
  first newline (`:747-750`).
- The parsed reply's `seqNum` is compared with the request's (`PIMEClient.cpp:751-752`). The
  comparison is inside the `try`; any exception (for example a missing or non-numeric `seqNum`) is
  caught at `:754-756` and also means failure.
- On a failure in the send/parse/compare path, the response is set to `nullptr`, the pipe is
  closed, and the text-service state is reset (`PIMEClient.cpp:762-766`). `closeRpcConnection`
  closes the handle and event and clears
  `readBuffer_` (`:854-864`). `resetTextServiceState` removes and clears the language-bar buttons
  (`:838-852`); despite the comment that "the state is unknown", that is all it resets.
- Callers do not act on the response on failure: `handleRpcResponse` rejects a non-object
  (`PIMEClient.cpp:105-109`), and `filterKeyDown`/`onKeyDown` return `false`
  (`:434-444`, `:446-456`). The key is therefore not consumed by the IME.
- There is no retry of the failed request. The next RPC re-enters `waitForRpcConnection` because
  `shouldWaitConnection_` is still true (`PIMEClient.cpp:733-736`), which reconnects (3 × 3000 ms,
  `:812-815`), sends `init` again, and re-sends `onActivate` if the client was activated
  (`:817-831`). `init` failure closes the pipe and returns `false` (`:818-824`).
- Nuance: `onActivate` sets `isActivated_ = true` unconditionally after the call
  (`PIMEClient.cpp:413-422`), even when the call failed and the pipe was closed. The next
  connection then sends `onActivate` again because of that flag (`:826-831`).

The response-nulling at `:763` is recent defensive work: commit `a132a8b` states that callers
ignored `callRpcMethod`'s return value and previously applied the stale parsed reply through
`updateStatus()`. That commit is the reason a mismatched reply cannot be applied today.

### End-to-end cases

| Backend echo | Launcher | C++ | Net effect |
|---|---|---|---|
| current `seqNum` | removes the matching pending key, forwards payload | accepts | normal |
| wrong `seqNum` (e.g. always `0`) | removes `(id, 0)` if present, otherwise no-op; forwards anyway | mismatch → null/close/reset | call fails; the pending `(id, N)` entry survives and, if no correct echo follows, the 15 s watchdog restarts the backend |
| no `seqNum` | no removal; forwards | parse succeeds, comparison throws → caught → failure | same as above, and the pending entry survives this reply |
| stale `seqNum` that matches a *different* pending request | removes that other key | mismatch for the current request → failure | one request's liveness is masked, so its hang may not be detected on time |
| stale payload labelled with the current `seqNum` (`N`) | removes the key, forwards | accepted; there is nothing to compare it with | residual risk: a stale payload carrying the right number is indistinguishable from the real reply |
| consistently wrong echo | every reply leaves the real pending entry | every request fails immediately | IME stops working, keys pass through, backend is killed/restarted about every 15 s |

The key-insertion and key-removal columns also apply to the launcher's own close notice: it goes to
the same stdin queue and is inserted when the input loop dequeues it, so its reply clears the key.
The C++ column does not apply—the client is already gone. A backend that treated close as a
notification and did not reply would leave that key to trip the watchdog about 15 s later—the
failure the side branch's `is_notification_message` bypassed and `d0e4235` fixed by replying.

The launcher's pending ledger is per backend, not per client: one stale key causes
`map.values().any(...)` to be true (`backend_manager.rs:411-414`), so one mis-echoing request stalls
and then restarts the backend for every client attached to it. When the C++ side times out first
(for keystrokes, after 2 s, not 15 s: `PIMEClient.h:81`), it closes the pipe; the launcher session
then ends and unregisters the client (`pipe_server.rs:87-96`), sending a synthetic close. The input
loop inserts the close's pending key (`backend_manager.rs:381-384`), and the close reply clears it
(`:316-319`). The original unanswered key remains until a late reply or the watchdog.

### Deliberate or oversight?

The evidence supports "deliberate as a router, not a validator", but not "deliberately ignoring
mismatches":

- On mainline, seqNum-keyed pending tracking dates to `23fd633` (a watchdog-race fix), and the
  current `(client_id, seqNum)` key is from `11db679`, whose message describes its purpose as
  "ensure monotonic timeouts, prevent cross-client sequence collisions, and time pipelined requests
  independently". Neither message mentions rejecting a reply.
- `PIMELauncher/README_SPEC.md:4-15` defines the process as a proxy that forwards messages and
  monitors hangs; validation is not a stated requirement. The C++ check is older than the Rust
  launcher: it was introduced by `ef610de` (2016) and is present at
  `382d676^:PIMETextService/PIMEClient.cpp:680`, so the rewrite could reasonably have left
  correctness to TSF `[INFERENCE]`.
- There is no comment in `backend_manager.rs` saying mismatches are ignored, and no test covers a
  mis-echoing backend. The integration tests cover reconnect and hang detection
  (`PIMELauncher/tests/integration_test.rs:148-200`), and the close test only checks a manually
  forwarded close reply (`:256-273`). `git log -S'pending_requests'` returns `11db679` for that
  identifier (the earlier `23fd633` added the seqNum-keyed variant);
  `git log -S'sequence number mismatch'` hits the C++ client history, not the launcher.

So the *purpose* of tracking `(client_id, seqNum)` is deliberate: it is a hang ledger. The absence
of any defensive action on a mismatch is an untested gap rather than a documented decision. Nothing
in the code or history says a mis-echoing backend was considered safe; it simply falls to C++ to
detect, at the cost of the session.

## 2. The `"method":"close"` reply branch

**Answer.** The `debug!` arm is reachable in the code, but no shipped producer emits its payload
shape: Python, nime and Go reply to close without a `method` field, so they take the `warn!` arm.
Only the test-only `mock_backend` emits `"method":"close"`.

### The branch and its exact guard

The branch is the `else if`/`else` arm of reply routing:

```rust
let tx = state.clients.get(&client_id).map(|e| e.tx.clone());   // 323-326
if let Some(tx) = tx { /* forward */ }
else if !payload.contains(r#""method":"close""#) { warn!(...) } // 340-344
else { debug!(...) }                                             // 345-349
```

It has no effect on delivery. Both arms only log. To take the `debug!` arm, **both** of these must
hold:

1. `state.clients.get(&client_id)` is `None` (`backend_manager.rs:323-326`), and
2. the payload contains the literal bytes `"method":"close"` (`:340`).

For the launcher's own close request, condition 1 is guaranteed by ordering: `unregister_client`
removes the entry (`backend_manager.rs:94`) and only then sends the close line (`:102-104`). The
backend's reply therefore always arrives with no registered client. Condition 2 is producer-
dependent.

### What each producer actually writes

| Producer | Success reply | Failure reply | Reply to `{"method":"close"}` | Exit |
|---|---|---|---|---|
| Python | service reply with `success` + `seqNum`, e.g. `python/textService.py:135-141`, written at `python/server.py:118-119` | uninitialized/unknown-init `{"seqNum":n,"success":false}` (`python/server.py:59-72`); unknown method sets `success=false` but still returns `seqNum` (`python/textService.py:131-141`); per-line exception `{"success":false,"seqNum":n}` (`python/server.py:123-140`) | `{"success":true,"seqNum":n}` — no `method` (`python/server.py:107-113`) | `EOFError` breaks the loop, no line (`python/server.py:120-122`) |
| Node / nime | `service.response()` result; default `{success:true, seqNum}` (`node/node_modules/nime/src/textService.js:25-27`), overridden per method by services (`node/input_methods/meow/index.js:257-265`, `node/input_methods/emojime/src/index.js:42-50`), written at `nimeServer.js:92-97` | unresolved init → `{success:false,seqNum}` via `NULL_SERVICE` (`node/server.js:22-29`, `requestHandler.js:30-38`); a first non-`init` request for an unseen client stores `{service:null,state:null}` (`nimeServer.js:77-79`) and dereferences it in `requestHandler.js:43-53`, so it throws with no reply. There is no `uncaughtException` handler; bootstrap ends at `server.listen()` (`node/server.js:54-56`) | `{"success":true,"seqNum":n}` — no `method` (`nimeServer.js:83-91`) | with no services loaded, `process.exit(1)` before reading (`node/server.js:10-13`); on stdin EOF, the `stdio` close callback only logs `Finished` (`nimeServer.js:100-102`), no reply line |
| Go | `{"success":true,"seqNum":n,...}` (`go-backend/server.go:233-238`, `:240-251`, `:296-303`), written by `sendResponse` (`:282-290`) | `{seqNum, success:false, error}` for missing GUID, unknown factory, failed `Service.Init`, uninitialized client, unknown method (`go-backend/server.go:181-187`, `202-208`, `225-230`, `259-264`, `272-278`); the `Run` error path writes `{success:false,error}` **without** `seqNum` (`:125-135`) | `{"seqNum":n,"success":true}` — no `method` (`go-backend/server.go:240-251`) | EOF returns `nil` (`go-backend/server.go:112-116`); a `Run` error calls `log.Fatal` in `main` (`:470-472`), no reply line |
| `mock_backend` (test fixture) | non-close input gets `REPLY: <line>`, not JSON (`PIMELauncher/src/bin/mock_backend.rs:40`, `:52`, `:63`) | same echo | the only producer with the branch's shape: `{"method":"close","success":true,"seqNum":n}` (`mock_backend.rs:26-38`) | loop ends at stdin EOF, no line |

The shipped backends are exactly the three named in `backends.json:1-19`. The second Go server in
`go-backend/pime/server.go` is not named there; its `sendResponse` (`:153-159`) is not a launcher
target (its write is at `go-backend/pime/server.go:161-162`). `PIMELauncher/test_backend.py:16` is a
manual helper, also not in `backends.json`.

### History: did a producer ever emit it?

No shipped backend did. Commit `d0e4235` ("backend: reply with success on close method") is the
change that made Python and nime reply to close at all; its diff adds `{"success": True}` plus
`seqNum` for Python (`python/server.py:109-112`) and `{success: true}` plus `seqNum` for nime
(`nimeServer.js:86-90`), with no `method`. The same commit added `"method":"close"` to the
**mock** backend's synthetic reply (`mock_backend.rs` in `d0e4235`). Commit `11db679` later added
the launcher-side `payload.contains(...)` arm and made the mock echo the close `seqNum`
(`11db679` diff for `backend_manager.rs` and `mock_backend.rs`). A history search for the string
does hit `0128f36` ("为pime加入go的支持"), but those hits are Go's handling of a close **request**
and its tests, not a reply shape.

An unmerged alternative is visible on `origin/agent_bug_fixes`: commit `e980a58` added
`is_notification_message` (`origin/agent_bug_fixes:PIMELauncher/src/protocol.rs:48-53`) so a
`{"method":"close"}` line in the backend input queue would not arm the watchdog, on the
assumption that backends do not reply. Mainline
`d0e4235` instead made Python and nime reply to close, with the message "avoid special-case
notification bypasses in the launcher". The current code follows `d0e4235`: the close request is
inserted into `pending_requests` like any other request when the input loop dequeues it
(`backend_manager.rs:381-384`), and its reply clears the key (`:316-319`). The reply-side
`payload.contains` arm is therefore not the old notification bypass either; it is only a log
filter.

### Verdict

For the three shipped backends the `debug!` arm is dead: condition 1 holds on close, condition 2
never does, so the `else` warn arm runs. Every normal disconnect of a Python, Node or Go client
therefore logs
`"Received message for unknown client"` (`backend_manager.rs:340-344`) after the close reply is
routed to no client. The close reply's real job is to clear the synthetic close's pending key
(`:316-319`); the `method` check is only cosmetic.

It is live for `mock_backend`. The integration test drops the test client at the end of
`PIMELauncher/tests/integration_test.rs:256-273`, which is the post-unregister situation that can hit
the branch, but the assertion at `:272` covers the *manually forwarded* close while the client is
still registered, not the launcher log branch.

For the `debug!` arm to fire with a shipped backend, that backend's close reply would have to add
the exact compact substring `"method":"close"` (the guard is a byte `contains`, not a JSON field
lookup). Alternatively the launcher would have to change the predicate—for example, recognise the
pending close key or the `last_seq_num + 1` value instead of looking for a `method` string. Python's
close reply is built with `json.dumps(reply_dict)` (`python/server.py:112`), so a future addition
would also have to match whatever separators that call emits; the guard itself does no JSON parsing.

## 3. `readBuffer_` carry-over and queued lines

**Answer.** Yes. The launcher writes complete lines and the C++ buffers leftover bytes across calls;
a duplicate or late line that reaches a still-registered client can be consumed as the next reply,
and C++ then fails the `seqNum` check and resets the connection. #943 can replay stale requests, but
a fresh UUID keeps their replies from reaching a reconnected client.

### The buffering logic

`callRpcPipe` checks `readBuffer_` for a newline **before** reading the pipe
(`PIMETextService/PIMEClient.cpp:716-723`). If one exists, it returns that line and erases it from
the buffer. Otherwise it reads up to 8192 bytes, appends them, and loops (`:725-728`). The buffer is
not cleared at the start of a call; it survives across RPC calls and is cleared only by
`closeRpcConnection` (`:854-864`). The read is one overlapped `ReadFile` with a per-read timeout
(`:666-700`); a timeout cancels the I/O and returns `false` (`:688-698`).

This is correct and necessary for fragmented/coalesced pipe reads: a single 8 KiB read can contain a
complete reply plus the start of the next one, and the excess must be kept. The consequence is that
the class has no notion of "this line belongs to this call" beyond the `seqNum` check in
`callRpcMethod` (`:751`).

### Every site that writes a line to the client pipe

The launcher has exactly one writer to the client pipe: `ClientSession::process_backend_output`
sends each payload to `pipe_writer` (`PIMELauncher/src/client_session.rs:90-97`). The `LinesCodec`
writer appends the newline (`client_session.rs:17`); the client-side reader also uses `LinesCodec`
(`pipe_server.rs:116-118`). The session receives that payload from the per-client channel
(`client_session.rs:49-63`), which `forward_outputs_to_client` fills (`backend_manager.rs:323-334`).
There is no other write path in `PIMELauncher/src`.

Everything else writes to a backend's **stdout**, not to the client pipe; the launcher turns those
lines into client lines if the `PIME_MSG|` prefix and client id match:

- Python: `python/server.py:112-113` (close), `:118-119` (normal), `:136-137` (exception).
- Node/nime: `node/node_modules/nime/src/nimeServer.js:90-91` (close), `:96-97` (normal).
- Go: `go-backend/server.go:289` for every response produced by `sendResponse`
  (`:282-290`).
- `mock_backend`: `PIMELauncher/src/bin/mock_backend.rs:29-37` (close), `:40`, `:52`, `:63`
  (echoes).
- `PIMELauncher/test_backend.py:16` is a manual helper; it is not in `backends.json`.

Non-`PIME_MSG|` lines from stdout are discarded at `backend_manager.rs:312-314`, so debug prints do
not reach the client.

### Can a queued or unsolicited line be consumed as a reply?

Yes, mechanically. The launcher forwards every parsed `PIME_MSG|<uuid>|payload` line for a
registered uuid, in arrival order, with no request/reply state (`backend_manager.rs:312-334`). The
C++ side has no background reader; it reads only inside `callRpcMethod`. Because the pending key is
removed before routing and is not tied to the current request, an unsolicited line also clears
whatever pending key its `seqNum` names (`backend_manager.rs:316-319`), so it can mask a real hang.
Therefore:

- A second line already in `readBuffer_` (a duplicate reply, or the tail of a coalesced read) is
  returned by the next `callRpcPipe` (`PIMEClient.cpp:718-723`) and treated as the reply to the
  *new* request.
- A line that arrives while no call is in flight sits in the pipe buffer; the next call consumes it
  first.
- If the consumed line is a JSON object, `callRpcMethod` compares its `seqNum` with the current
  request (`:751`). If it differs, or is missing/non-numeric, the call fails and the
  null/close/reset path runs (`:762-766`). `closeRpcConnection` then clears `readBuffer_`
  (`:863`), discarding any remaining carried lines.
- If the consumed line is not JSON at all, the parse at `:749` throws and the same failure path runs
  (`:754-766`).

Today no shipped producer emits unsolicited lines: each request line gets exactly one reply line
(table above), and the launcher-generated close reply is sent to an already-unregistered uuid, so it
is never forwarded. The realistic sources of an extra line are a duplicate reply, a late reply that
was already written into the pipe before the client timed out, or a future push channel. The
`seqNum` check makes a duplicate/late line a session failure rather than a silently applied stale
state—this is exactly the case `a132a8b` hardened by nulling the response.

### The #943 stale-queue angle

The launcher's stdin queue is not reset on backend restart. `stdin_tx`/`stdin_rx` are created once
per backend (`backend_manager.rs:167`), the restart loop reuses the same receiver
(`:173`, `:206-214`), and `disconnect_clients_for_backend` only removes routing entries
(`:108-118`, `:228-232`); it does not drain the queue. Any lines already queued—or enqueued by a
session that has not yet noticed the failure—are written to the new backend process after the 1 s
sleep (`:228-232`).

What that stale queue can and cannot do:

- It **cannot** deliver a reply to a reconnected C++ client. The launcher assigns a fresh
  `Uuid::new_v4()` per pipe connection (`pipe_server.rs:109`), so the old queued requests carry the
  old uuid. Replies to them find no entry in `state.clients` and are dropped
  (`backend_manager.rs:323-326`, `:340-349`).
- It **can** feed a restarted backend requests for which it has no session. Python creates a new
  `Client` for the old id and, for a non-`init` request, returns `{"seqNum":n,"success":false}`
  (`python/server.py:59-72`, `:101-105`). Go returns `success:false` for an uninitialized client
  (`go-backend/server.go:259-264`). Node/nime stores `{service:null,state:null}` for the unseen id
  (`nimeServer.js:77-79`) and dereferences the null service on a non-`init` line
  (`requestHandler.js:43-53`), which throws; with no `uncaughtException` handler
  (`node/server.js:54-56`), that is the #937 crash. A stale queued non-`init` request can therefore
  crash a freshly restarted Node backend, and the cycle can repeat.
- It can **delay** the new client's `init`, because the stale lines are ahead of it in the same FIFO
  queue. Whether any stale lines exist at a given restart depends on whether requests were queued
  when the process died; that is a runtime property, `[INFERENCE]` here.

The C++ `readBuffer_` angle is separate: a line left in `readBuffer_` from before the failure can be
consumed by the next call, but the next call is on a reconnected pipe after `closeRpcConnection`
cleared the buffer (`PIMEClient.cpp:854-864`). If the C++ has not yet detected the failure and calls
again on the old pipe, the stale line can be consumed and produces the same `seqNum` mismatch path.
Either way the stale line is not applied.

## 4. The 15 s pairing

**Answer.** Both constants are 15 s, but they are different deadlines: C++ applies 15 s to each
`init`/`onActivate` overlapped read/write, while the launcher checks its pending ledger every second
and kills at the first tick at or after 15 s. A reply after the C++ deadline fails the client call;
a reply after the launcher deadline finds the backend killed and the client disconnected.

### Constants and use sites

| Constant | Value | Defined | Used |
|---|---|---|---|
| `kDefaultRpcTimeoutMs` | 2000 ms | `PIMETextService/PIMEClient.h:81` | default for all RPCs (`PIMEClient.h:85`, `:89`) |
| `kServerStartupTimeoutMs` | 15000 ms | `PIMEClient.h:82` | `init()` (`PIMEClient.cpp:645-655`), `onActivate()` (`PIMEClient.cpp:413-422`) |
| `HANG_TIMEOUT` | 15 s | `PIMELauncher/src/protocol.rs:8` | watchdog comparison (`backend_manager.rs:411-414`), log value (`:418`) |
| `BACKEND_WRITE_TIMEOUT` | 5 s | `protocol.rs:11` | write to backend stdin (`backend_manager.rs:395-406`) |

`kServerStartupTimeoutMs` is not used anywhere else, and `HANG_TIMEOUT` is not used anywhere else.
`PIMELauncher/README_SPEC.md:12-13` still describes the default as 30 s; the implemented value is
15 s (`PIMELauncher/src/protocol.rs:8`), so that line of the spec is stale. The 15 s pairing is
intentional: commit `79abda2` says the C++ startup timeout was raised to
"15 seconds (matching PIMELauncher's hang timeout)" so cold-start `init`/`onActivate` would not be
cut off while the Python backend imports dictionaries. All interactive keystroke RPCs stay at 2 s.

The two deadlines are not the same kind of deadline. C++ applies its timeout to each overlapped
read/write (`PIMEClient.cpp:688-698`); `callRpcPipe` can perform multiple reads before a newline
(`:716-729`), so a backend that trickles bytes can exceed 15 s in total while no single read times
out. The launcher stamps the pending entry when the request is dequeued, before writing
(`backend_manager.rs:381-384`), and checks it every second (`:369`), so its kill happens on the
first tick at or after 15 s.

### Observable failure mode: client side

- `init` or `onActivate`: the read waits up to 15 s, then `callPipeIO` cancels the overlapped I/O
  and returns `false` (`PIMEClient.cpp:688-698`). `callRpcMethod` nulls the response, closes the
  pipe, and resets state (`:762-766`). For `init`, `waitForRpcConnection` closes the pipe and
  returns `false` (`:818-824`). For `onActivate`, the call fails but `isActivated_` is still set to
  `true` (`:413-422`); the next connection re-sends `onActivate` (`:826-831`).
- A keystroke RPC: the deadline is 2 s, not 15 s (`PIMEClient.h:81`). The same failure path runs,
  `filterKeyDown` returns `false` (`PIMEClient.cpp:434-444`), and the key is passed through to the
  application. The next keystroke triggers `waitForRpcConnection` (`:733-736`) and re-`init`s.
- In both cases the failed call is not retried. The C++ pipe session is lost, the language-bar
  buttons are removed (`:838-852`), and the user sees a missed key or a failed activation followed
  by a reconnect on the next event.

### Observable failure mode: launcher side

- The pending entry timestamped at `backend_manager.rs:381-384` ages. At the first 1 s tick where
  `now - sent_time >= 15 s` (`:409-414`) the launcher kills the child and returns `Error`
  (`:415-421`). The restart path disconnects every client of that backend, sleeps 1 s, and respawns
  (`:228-232`).
- If the reply arrives **after** the C++ deadline but **before** the watchdog tick, the launcher
  removes the pending key and forwards the payload (`:316-319`, `:323-334`). The C++ has already
  closed its pipe; if the session's write then fails (`client_session.rs:90-96`), the session exits
  and `unregister_client` sends a close (`pipe_server.rs:87-96`). The backend may survive; the reply
  is never applied. Whether the write fails immediately on a closed pipe is a Windows property
  (see below).
- If the reply arrives **after** the kill, the process is gone and any line not already forwarded is
  lost; the C++ sees the pipe close or its own timeout.
- The boundary between the two is timing-dependent: the launcher's clock starts before the write,
  the C++ clock starts when its read is issued, and the watchdog has 1 s granularity. The exact
  winner in the 15–16 s window is `[INFERENCE]` without Windows instrumentation; the code supports
  either ordering, and neither ordering applies the reply.
- Because the pending ledger is per backend, a request whose client has already timed out and
  disconnected can still trigger the kill. Its entry is removed if the backend eventually replies
  with the right `seqNum` (even to the dead uuid), because removal happens before the client lookup
  (`backend_manager.rs:316-319`). If no reply ever comes, the backend is restarted ~15 s after the
  request, not after the disconnect.

## Issue anchors

| Issue | Site that matters |
|---|---|
| #943 stale queue replayed after restart | queue survives restart (`PIMELauncher/src/backend_manager.rs:167`, `:173`, `:206-214`); disconnect + 1 s sleep does not drain it (`:108-118`, `:228-232`); fresh UUID per connection is what keeps replies away from a new client (`pipe_server.rs:109`) |
| #937 Node null-service crash re-triggered by stale queue | unseen client stored as `{service:null,state:null}` (`node/node_modules/nime/src/nimeServer.js:77-79`), dereferenced on a non-`init` line (`requestHandler.js:43-53`), with no `uncaughtException` handler (`node/server.js:54-56`) |

## Open questions

- Should the launcher *drop* a reply whose `seqNum` is not pending for that client, instead of
  forwarding it and letting C++ pay for the session? The current code only removes the key
  (`backend_manager.rs:316-319`); there is no test or comment deciding this.
- Should `unregister_client` purge that client's pending entries? Today a timed-out keystroke can
  still restart the backend ~15 s later even though the client is gone
  (`backend_manager.rs:91-104` vs `:409-421`).
- Does any third-party backend emit `"method":"close"` in a compact reply? Only the three shipped
  backends and the mock fixture were inspected.
- Is the exact 15–16 s race on Windows resolved in favour of the watchdog or the late reply? The
  code allows both; only instrumentation on Windows would settle it.

## Not verifiable here

- No execution of `PIMETextService`, `libIME2` or `PIMELauncher`; this checkout is Linux and those
  targets are Windows-only (`docs/agents/verification.md:1-3`). No tests, builds, or backends were
  run.
- Windows named-pipe timing and close semantics: whether a write to a pipe whose client handle has
  just closed fails immediately or is buffered, and whether a cancelled overlapped read can still
  deliver data to the buffer. The code assumes cancellation completes before return
  (`PIMEClient.cpp:693-697`); the actual scheduling is a Windows property.
- The visible TSF effect (composition/candidate clearing) of `resetTextServiceState`; the code only
  clears language-bar buttons (`PIMEClient.cpp:838-852`).
- Real backend stdout encoding and line buffering (`PYTHONIOENCODING` is set at
  `backend_manager.rs:282-283`; Node uses its default stream encoding; Go uses `encoding/json`).
- Third-party or locally installed backends outside `backends.json`.
