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
- **C++ / Rust** — the product targets Windows. `PIMELauncher` can be built for
  `i686-pc-windows-gnu` and its tests run under Wine (15 at the time of writing;
  `docs/agents/wine.md`); treat that as a smoke check, not Windows. The C++ text
  service cannot build or run here: the root `CMakeLists.txt` uses MSVC flags
  (`/MT`, `/D_UNICODE`), TSF needs a Windows host, and running `cmake` on Linux
  proves nothing.
- **Docs pages** — `docs/tour/` is static and outside CI (`paths-ignore: docs/**`),
  so this check is the guardrail: serve with `python3 -m http.server 8765 -d docs`,
  open `http://127.0.0.1:8765/tour/` with `browser.open` (headless Chromium), and
  check layout, console errors, and tab behaviour. Screenshot only the changed
  region. If the prelude reports "Shared browser daemon unavailable", the daemon's
  Chrome profile holds a lock from a dead PID (exit 21): remove
  `~/.omp/run/daemons/*/omp.browser.headless.profile/Singleton*` and retry.

## CI (GitHub Actions, `windows-2025`)

`.github/workflows/build-and-sign.yaml` runs, in order:

1. `cargo test` in `PIMELauncher/`
2. `python -m unittest discover -s tests -p "test_*.py" -v`
3. `npm test` in `node/`
4. `build.bat` (x86 + x64 text service, launcher, backends)
5. sign the built binaries, then build the NSIS installer

So the feedback loop for a C++ or Rust change is: push a branch, or run the workflow
on it, and read the `build-and-sign` job. Do not claim a C++/Rust change verified
without a green run there.

## Ordering

Backend behaviour → local unittest first. Anything touching `PIMETextService/`,
`libIME2/`, or `PIMELauncher/` → CI. A change spanning both → local first, then CI.
