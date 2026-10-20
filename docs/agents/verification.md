# Verifying changes in this repo

This checkout is Linux; the product is Windows-only. Verify each layer in the
cheapest place it actually runs.

## Local (Linux, this checkout)

- **Python backend**:

  ```
  python3 -m unittest discover -s tests -p "test_*.py" -v
  ```

  `tests/chewing_test.py` does not match the pattern on purpose: it imports `windll`
  and drives the Windows desktop. Run it on Windows by hand.
- **Node backend** — `cd node && npm test`: spawns `node/server.js` and speaks the
  launcher's `<client_id>|<json>` framing over stdin/stdout, so it needs no Windows.
  The bundled `node/node.exe` is v10.12.0; CI runs Node 21.x.
- **Go backend** — needs Go installed: `cd go-backend && go test ./...`.
- **C++ / Rust** — cannot build here. The root `CMakeLists.txt` uses MSVC flags
  (`/MT`, `/D_UNICODE`) and `PIMELauncher` is built only for x86 against Windows
  named pipes. Running `cmake` on Linux proves nothing; don't.
- **Docs pages** — `docs/tour/` is static: serve it with
  `python3 -m http.server 8765 -d docs`, then open
  `http://127.0.0.1:8765/tour/` with `browser.open` (headless Chromium) to check
  layout, console errors, and tab behaviour. Screenshot only the changed region.
  If the browser prelude reports "Shared browser daemon unavailable", inspect
  `~/.omp/run/daemons/*/omp.browser.headless.profile/Singleton*`: a lock left by
  a dead Chrome PID (exit 21) persists until those symlinks are removed.

## CI (GitHub Actions, `windows-2025`)

`.github/workflows/build-and-sign.yaml` runs, in order:

1. `cargo test` in `PIMELauncher/`
2. `python -m unittest discover -s tests -p "test_*.py" -v`
3. `npm test` in `node/`
4. `build.bat` (x86 + x64 text service, launcher, backends)
5. NSIS packaging and signing

So the feedback loop for a C++ or Rust change is: push a branch, or run the workflow
on it, and read the `build-and-sign` job. Do not claim a C++/Rust change verified
without a green run there.

## Ordering

Backend behaviour → local unittest first. Anything touching `PIMETextService/`,
`libIME2/`, or `PIMELauncher/` → CI. A change spanning both → local first, then CI.
