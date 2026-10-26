# Verifying changes in this repo

This checkout is Linux; the product is Windows-only. Verify each layer in the
cheapest place it actually runs.

## Sandbox facts

- **YAML**: `python3` has no PyYAML. The Bun parse command is the `GitHub YAML
  parses` step under Local below.
- **Windows interop**: `cmd.exe` is not reachable from this WSL install. Run
  Windows binaries with Wine (`docs/agents/wine.md`), not through `/mnt/c`.
- **Go**: `gofmt` is not on `PATH`; use `go fmt` / `go test` through the Go
  toolchain when it is installed.

## Local (Linux, this checkout)

One command runs every layer below, skips toolchains the machine lacks, and
exits nonzero on failure. It also checks that a `pr/*` branch starts at
`origin/master`; local `master` commits in a product PR fail the run.

```
tests/run_local_tests.sh
```

Every step is bounded (`STEP_TIMEOUT`, default 600s) and reports `HANG` when the
deadline fires, so one stuck Wine call cannot eat the run. A run reads the script
incrementally: leave `tests/run_local_tests.sh` untouched while a background run
is still going, or run a copy.

Prove a harness change on both paths: a synthetic `hang() { sleep 30; }` step
under `STEP_TIMEOUT=2` must print `HANG` within a couple of seconds, and a normal
run must still finish in about 30s — a watchdog that outlives its step holds the
run's stdout, which only the pipeline's wall time reveals.

Individual commands, if you want to narrow the loop:

- **Python backend** — the full `tests/` suite (protocol loop, TextService
  dispatch, service manager, cin counting, input-method smoke, docs pages,
  README build contract):

  ```
  python3 -m unittest discover -s tests -p "test_*.py" -v
  ```

  `tests/run_local_tests.sh` also runs the same suite on the shipped
  interpreter (`python/python3/python.exe`, 3.15.1) under Wine; the Linux-only
  IME smoke test skips itself there, and so do the modules that import
  `cinbase`, because `cinbase/__init__.py` reaches
  `propsys.dll.VariantToString`, which this Wine build does not implement (Wine
  aborts into `winedbg` instead of raising, so the test would hang). The host
  run keeps that coverage: those modules install the smoke runner's Win32
  shims, and the logic under test never calls a Win32 function. Run the
  bundled suite directly with:

  ```
  WINEDEBUG=-all wine python/python3/python.exe -m unittest discover -s tests -p "test_*.py" -v
  ```

  `tests/chewing_test.py` does not match the pattern on purpose: it imports `windll`
  and drives the Windows desktop. Run it on Windows by hand.

  `tests/test_input_methods_smoke.py` instantiates the real service subclasses
  with Windows API shims, activates them, and sends key events. It covers the ten
  cinbase services plus `meow`; `chewing`/`braille_chewing` are reported as
  skipped when the system libchewing does not match the bundled binding, and
  `rime` when `librime.so` is absent. It needs `libopencc-dev` (the wrapper loads
  `libopencc.so`); without it the test skips. `libchewing3`/`librime1` are
  optional: installing them turns the skipped checks into real ones, matching
  the versions PIME ships. Input methods that import Windows-only modules can
  still be syntax-checked:

  ```
  python3 -m compileall -q -x '(^|/)python3(/|$)' python
  ```

- **Node backend** — `cd node && npm test`: three scripts. Upstream's
  `tests/nimeServer.test.js` covers the line protocol under `node --test`;
  `server.test.js` spawns `node/server.js` and speaks the launcher's
  `<client_id>|<json>` framing over stdin/stdout; `loadServices.test.js`
  discovers services from a temporary `input_methods` tree (both loaders accept
  an optional `baseDir` for this).
  The bundled `node/node.exe` is v22.23.4 (32-bit); CI runs Node 22.x. Wine
  cannot run that Node build (`EBADF` while loading builtins), so the bundled
  runtime is exercised on Windows CI instead: `server.test.js` spawns
  `process.execPath`, which is the shipped `node.exe` there.
- **Go backend** — `cd go-backend && go test ./...` (4 packages). `go.mod`
  requires Go 1.21; Debian bookworm's 1.19 is too old. `tests/run_local_tests.sh`
  looks in `PATH`, `/usr/local/go/bin`, and `/opt/go/bin`. To install:

  ```
  curl -sSLo /tmp/go.tgz https://go.dev/dl/go1.21.13.linux-amd64.tar.gz
  sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf /tmp/go.tgz
  export PATH=/usr/local/go/bin:$PATH
  ```

  The Linux `linux-checks` job installs Go from `go.mod` and runs this same
  command through the script, so a missing package or registration fails PR CI.
  The script also cross-compiles the shipped target:
  `CGO_ENABLED=0 GOOS=windows GOARCH=386 go build ./...`.
- **C++ pure helpers** — `PIMETextService/JsonUtils.h` and
  `CompositionCursor.h` have no Windows dependencies, so they are testable here:
  - `JsonUtils`: host g++ links the vendored gtest:
    `g++ -std=c++17 -pthread -I PIMETextService -I json/single_include -I libIME2/lib/googletest-release-1.10.0/googletest/include -I libIME2/lib/googletest-release-1.10.0/googletest tests/json_utils_test.cpp libIME2/lib/googletest-release-1.10.0/googletest/src/gtest-all.cc libIME2/lib/googletest-release-1.10.0/googletest/src/gtest_main.cc -o /tmp/json_utils_test && /tmp/json_utils_test`
    (6 tests).
  - `CompositionCursor`: Linux `wchar_t` is 32-bit while the helper indexes a
    Windows UTF-16 buffer, so build it for Windows and run under Wine:
    `i686-w64-mingw32-g++ -std=c++17 -static -I PIMETextService tests/composition_cursor_test.cpp -o /tmp/composition_cursor_test.exe && wine /tmp/composition_cursor_test.exe`
    (needs `g++-mingw-w64-i686`).
- **Rust launcher** — cross-build for `i686-pc-windows-gnu` and run under Wine
  (`docs/agents/wine.md`; the run prints its own test counts). Treat that as a
  smoke check, not Windows. The same block runs `cargo fmt --check` and
  `cargo clippy --target i686-pc-windows-gnu --all-targets -- -D warnings`
  when `rustfmt`/`clippy` are installed (`rustup component add rustfmt clippy`).
- **Docs pages** — `tests/test_docs_pages.py` checks local links/assets, anchors,
  duplicate ids, and `aria-controls`/`aria-labelledby` targets. The `Docs checks`
  workflow runs it on pushes and PRs that touch `docs/**`; `docs/tour/`
  is still outside the Windows workflow (`paths-ignore: docs/**`), so a changed
  page also needs the manual pass: serve with
  `python3 -m http.server 8765 -d docs`, open
  `http://127.0.0.1:8765/tour/` with `browser.open` (headless Chromium), and
  check layout, console errors, and tab behaviour. Screenshot only the changed
  region. If the prelude reports "Shared browser daemon unavailable", the daemon's
  Chrome profile holds a lock from a dead PID (exit 21): remove
  `~/.omp/run/daemons/*/omp.browser.headless.profile/Singleton*` and retry.
- **GitHub YAML (workflows, issue forms, AppVeyor)** — `tests/run_local_tests.sh`
  parses every file under `.github/` plus `appveyor.yml` with Bun
  (`Bun.YAML.parse`), because `python3` has no PyYAML and GitHub reports a broken
  workflow only after a push. An issue form has a second gate GitHub applies when
  it renders the form from the default branch: an `id` with a space, or a `body`
  item without `attributes.value`, parses fine and still renders nothing. Validate
  a new form against SchemaStore's `github-issue-forms.json` before pushing.
- **C++ text service** — cannot build or run here: the root `CMakeLists.txt` uses
  MSVC flags (`/MT`, `/D_UNICODE`), TSF needs a Windows host, and running `cmake`
  on Linux proves nothing. The NSIS installer is not in that group: Debian's
  `makensis` is 3.08, the same version `build-and-sign.yaml` pins, and it
  preprocesses and assembles `installer/installer.nsi` in full, vendored
  plugins included. The only failures are `File` directives whose Windows
  build output is absent. `tests/run_local_tests.sh` therefore copies
  `installer/` plus `version.txt`, `LGPL-2.0.txt` and `PSF.txt` into a temp
  directory, rewrites each `File ` to `File /nonfatal`, and compiles, so a
  broken script, include or LogicLib block fails locally. What that does not
  prove: packaging and signing, plugin behaviour at install time, and the
  payload, since the installer packages the JavaScript input methods
  `build.bat` generates (`node/input_methods/McBopomofo`, `McFoxim`,
  `McTabim`, and `emojime/dist`). Windows CI (`windows-2025`) remains the
  check for those.

## CI (GitHub Actions)

`.github/workflows/ci.yaml` runs two kinds of check for non-tag refs:

- `linux-checks` (`ubuntu-latest`) checks out `libIME2`, installs Go from
  `go-backend/go.mod`, adds Bun for the YAML parse, installs `libopencc-dev`,
  then runs `tests/run_local_tests.sh`. This is the same command as local; it
  covers the GitHub YAML parse, Python, Node, Go (tests plus Windows/386
  cross-build), and the host C++ `JsonUtils` test. Layers needing Wine or the
  bundled runtimes report `SKIP` here and run in the Windows job.
- `ci` calls `.github/workflows/build-and-sign.yaml` (`windows-2025`), which runs,
  in order:

  1. `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, then
     `cargo test` in `PIMELauncher/`
  2. `python -m unittest ...` on the runner and on the bundled
     `python\python3\python.exe`
  3. `npm test` on Node 22.x and both Node tests on the bundled `node\node.exe`
  4. `build.bat` (x86 + x64 text service, launcher, backends)
  5. sign the built binaries, then build the NSIS installer

`.github/workflows/docs.yaml` runs `test_docs_pages.py` on changes to `docs/**`
or the test itself.

So the feedback loop for C++/TSF, MSVC-only helpers, or installer changes is:
push a branch, or run the workflow on it, and read the `build-and-sign` job. Do
not claim such a change verified without a green run there.

## Ordering

Backend behaviour → local unittest first. Anything touching `PIMETextService/`,
`libIME2/`, or `PIMELauncher/` → CI. A change spanning both → local first, then CI.
