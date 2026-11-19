Fixes #883 — the Word ruler drag leaves one window dead until it is reopened.

`Client::ensureConnected()` restarted the pipe connection only for `State::Disconnected`. A connect that gets cancelled leaves `state_` at `Connecting` with `connector_` already gone and no callback left to fire, so that branch makes no progress: every later `filterKeyDown`/`onKeyDown` returns `false` for the whole life of the window. Word's ruler drag leaves exactly that shape — the retest on `2.0.0-beta4` shows the dragged window stops answering while the other windows and the launcher stay healthy, and reopening the document (which runs a fresh `init`) is what recovers it.

- Widen the guard to re-drive `startAsyncConnect()` for `State::Disconnected` **or** a null `connector_` while `isActivated_` holds; both leave the same shape, so one call covers them.
- `isReady()` and the reply-matching path are untouched, so the seqNum pairing and the per-client rows keep their current shape; the only difference is that a parked row restarts the connect on the next key instead of waiting for a window reopen.

Validation:

- `bash tests/build_windows_artifacts.sh` links all three architectures: I386 491008, AMD64 593920, ARM64 535552 bytes, plus the `PIMETextService_arm64.dll` forwarder.
- `bash tests/build_windows_installer.sh` re-emits the staged setup artifact
  `PIME-2.0.0-beta4-setup.exe` (49745890 bytes) from that tree.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .scratch/ruler-loop.ps1` (Word, one document, key burst, ruler-band drag, second burst, then the launcher flush row): `CHECK_TIP`, `CHECK_FRAME`, `CHECK_COMMIT`, `CHECK_DRAG` all `PASS`, the document holds `音` before the drag and `音問 ` after it (`GROWTH=1`), `VERDICT=PASS`, flush row `filterKeyDown true=31 false=1 onKeyDown=23 seqNum sent=81 received=81 replies=81 mismatches=0 isKeyboardOpen=true compositionLen=3 connects=1`. Before the fix that same sequence left the dragged window at `true=1 onKeyDown=0` with no further text.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .scratch/desktop-859.ps1`: the per-client table answers with `mismatches=0`, `workerRestarts=0`, `backendRestarts=0`.
- `python/python3/python.exe .scratch/pipe-client-859.py`: `init` → `{"success": true}`, `onActivate` → the `customizeUI` block, six `filterKeyDown` calls answered, space commits `{"compositionString": "一", "return": true}`.
- `python/python3/python.exe -m unittest discover -s tests -p "test_service_manager.py"`: `Ran 14 tests ... OK`.
- `bash tests/verify_windows.sh` on this tree (every Linux-verifiable layer plus the Windows cross-build, the C++ helper gtests under mingw, and the Rust tests/fmt/clippy): `57 passed, 0 failed`.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
