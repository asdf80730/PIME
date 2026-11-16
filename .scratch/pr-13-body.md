Fixes #883 — the Word ruler drag leaves one window dead until it is reopened.

`Client::ensureConnected()` restarted the pipe connection only for `State::Disconnected`. A connect that gets cancelled leaves `state_` at `Connecting` with `connector_` already gone and no callback left to fire, so that branch makes no progress: every later `filterKeyDown`/`onKeyDown` returns `false` for the whole life of the window. Word's ruler drag leaves exactly that shape — the human retest on `2.0.0-beta4` shows the dragged window stops answering while the other windows and the launcher stay healthy, and reopening the document (which runs a fresh `init`) is what recovers it.

- Widen the guard to re-drive `startAsyncConnect()` for `State::Disconnected` **or** a null `connector_` while `isActivated_` holds; both need the same fresh start, so one call covers them.

`isReady()` and the reply-matching path are untouched, so the seqNum pairing and the per-client rows keep their current shape; the only difference is that a parked row restarts the connect instead of waiting for a window reopen.

Validation:

- `bash tests/build_windows_artifacts.sh` configures and links all three architectures: `PIMETextService.dll` for I386 (491008 bytes), AMD64 (593920 bytes) and ARM64 (535552 bytes) plus the `PIMETextService_arm64.dll` forwarder.
- `bash tests/build_windows_installer.sh` re-emits `.tools/stage/installer/PIME-2.0.0-beta4-setup.exe` (49745890 bytes) from that tree.
- `powershell -NoProfile -ExecutionPolicy Bypass -File .scratch/desktop-859.ps1`: `VERDICT=PASS`, flush block `sent=17 received=17 replies=17 mismatches=0`, `workerRestarts=0`, `backendRestarts=0`.
- `python/python3/python.exe` `-m unittest discover -s tests -p "test_service_manager.py"`: `Ran 14 tests ... OK`.
- `python/python3/python.exe` `.scratch/pipe-client-859.py`: `init` then `onActivate` then six `filterKeyDown` calls all answered, and the space key commits `{"compositionString": "一", "return": true}`.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
