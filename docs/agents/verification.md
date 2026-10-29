# Verifying changes in this repo

The product is Windows-only. Verify each layer in the cheapest place it
actually runs. This checkout can be either a Linux box (Wine) or a Windows box
(native) — see [Windows (native)](#windows-native-this-machine) below for the
Windows path.

## Sandbox facts (Linux checkout)

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
  interpreter (`python/python3/python.exe`; read `python/python3/python3*._pth`
  for the bundled version) under Wine; the Linux-only
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
  Corrosion copies `<bin>.pdb` after the Windows release build, so a release profile
  that emits none breaks `build.bat` while the build itself reports success; only
  `windows-2025` sees that half.
- **Docs pages** — `tests/test_docs_pages.py` checks local links/assets, anchors,
  duplicate ids, and `aria-controls`/`aria-labelledby` targets. The `Docs checks`
  workflow runs it on pushes and PRs that touch `docs/**`; `docs/tour/`
  is still outside the Windows workflow (`paths-ignore: docs/**`), so a changed
  page also needs the manual pass: serve with
  `python3 -m http.server 8765 -d docs`, open
  `http://127.0.0.1:8765/tour/` with `browser.open` (headless Chromium), and
  check layout, console errors, and tab behaviour. Screenshot only the changed
  region, then `tab.close` — this is the only sanctioned browser use, and a tab
  left open is the user's memory. If the prelude reports "Shared browser daemon
  unavailable", the daemon's Chrome profile holds a lock from a dead PID (exit 21):
  remove
  `~/.omp/run/daemons/*/omp.browser.headless.profile/Singleton*` and retry.
- **Nothing opens a window from a test or a probe** — the local suite must never
  reach the desktop. `ime_smoke_runner.install_windows_shims()` records
  `os.startfile` and `shell32.ShellExecuteW`/`ShellExecute` into
  `ime_smoke_runner.LAUNCHES` instead of performing them, on every platform.
  Without that, a test at the wrong seam opens real tabs: `python/cinbase/__init__.py`
  `os.startfile`s a GitHub URL for the 語言列選單 items (:2352-2364) and
  `ShellExecuteW`s `python/cinbase/configtool.py` for 「功能設定」 (:2527), which then
  `os.startfile`s the settings page (`python/cinbase/configtool.py:249`) — and
  because the pre-commit hook runs the suite, that happened on every commit. Any
  test that drives a menu or a command asserts `LAUNCHES == []`; to check
  settings-page semantics, read the script and the route table rather than
  starting `python/cinbase/configtool.py`.
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
  `installer/` plus `version.txt`, `LGPL-2.0.txt`, `PSF.txt` and `LICENSE.txt`
  into a temp directory, rewrites each `File ` to `File /nonfatal`, and compiles, so a
  broken script, include or LogicLib block fails locally. What that does not
  prove: packaging and signing, plugin behaviour at install time, and the
  payload, since the installer packages the JavaScript input methods
  `build.bat` generates (`node/input_methods/McBopomofo`, `McFoxim`,
  `McTabim`, and `emojime/dist`). Windows CI (`windows-2025`) remains the
  check for those.

## Windows (native, this machine)

This checkout lives on a Windows 11 ARM64 box, so every layer runs natively —
no Wine, no WSL. The toolchain is not installed system-wide: Go, Node, Bun,
Rust, and mingw-w64 all sit under `.tools/` in the project directory, and
`.tools/` is excluded through `.git/info/exclude` (local only, never upstream).

```
bash tests/install_windows_toolchain.sh   # once
bash tests/verify_windows.sh              # every time
```

Probe discipline here: a command whose stderr you discard with `2>/dev/null` is not
evidence — a `tasklist` whose `/FI` quoting Git Bash mangled printed an empty process
list, and the discarded half was the error saying so. When a probe disarms a Win32
entry point, replace only that entry point: replacing all of `ctypes.windll` makes
`ime_smoke_runner.under_wine()` find `wine_get_version` on the fake and report Wine,
which silently skips every Service-level test and turns a green run into no run.

A test comment that names what would turn the test red is a verification claim too,
and it needs the same proof as a `Validation:` line: delete the guard the comment
points at, watch the test fail, put it back. A comment can describe a race the test
never enters — a Stroke Service round shipped a back-to-back construction test whose
comment claimed it pinned a spawn guard, while deleting the guard left it green 8/8
because the first load had already finished. The test that does pin it parks its
loader *before* the loader raises its own flag, and asserts the loader was still
parked when the second call arrived, so missing the window is a failure rather than
a vacuous pass.

Sixteen layers, and the run prints its own tally (`16 passed, 0 failed`) — quote
that line rather than a counted number: the AI-declaration check, the PR scope-gate
self-test, the AI-declaration self-test and the local issue-tracker layout check
(`.scratch/` is gitignored, so no CI job can ever run it — the Windows box holds
the tickets), the GitHub/AppVeyor YAML parse (Bun), the Python backend suite on the
shipped `python/python3/python.exe`, three Node backend suites on the shipped
`node/node.exe`, the Go backend tests plus the shipped `GOOS=windows GOARCH=386`
build, `PIMELauncher` tests / `cargo fmt --check` / `cargo clippy`, and the two
pure-C++ helpers (`JsonUtils` gtest, `CompositionCursor`) built with mingw g++.
Counting `run_native` call sites comes out at 15: the tracker check is dispatched
inline (`write_step` plus its own `pass`/`fail`, so its exit 125 can read as
"no .scratch" rather than a failure), so it is not one of those calls.

**The agent docs have their own check, and it is not a layer.**
`tests/test_agent_docs.py` resolves every backticked or linked token ending in md, sh,
py, yaml, yml, nsi or ns inside `AGENTS.md` and `docs/agents/*.md` against the doc's
own directory, the repo root and the source roots, and fails when `AGENTS.md` leaves a
file under `docs/agents/` unnamed. Nothing in the gate runs it, so deleting or renaming
a file those docs cite is only caught if the same change runs
`python/python3/python.exe -m unittest discover -s tests -p test_agent_docs.py` — do it
before the stale doc reaches a reviewer, not after.

**The scope self-test's throwaway refs are not sediment.** While `bash
tests/verify_windows.sh` runs, `git branch` and `git worktree list` also show
`selftest/scope-dirty.$$`, `selftest/scope-clean.$$` and `selftest/scope-pyc.$$` with
worktrees under the temp directory; the self-test's EXIT trap removes them, so they are
the gate running, not a branch someone left behind. They are real `refs/heads/`
branches on purpose: the gate reads the checked-out name through `git symbolic-ref` and
skips on integration names, so a detached worktree would turn those assertions into
skips that still report as passing.

A run reads this script as it goes: leave `tests/verify_windows.sh` untouched while
a background run is still going, or run a copy. A failing layer keeps its output
under `.tools/.run/` rather than deleting it, so the traceback is there to read
without rerunning the step.

Narrowing the Python layer to one file on the shipped interpreter needs
`discover`: `python/python3/python.exe` is an embedded distribution whose
`python3*._pth` pins `sys.path` to the interpreter directory and ignores
`PYTHONPATH`, so `python/python3/python.exe -m unittest tests.test_x` fails with
`No module named tests`, and dropping a package marker into the `tests` directory
is not the fix. What works from the repo root:

```
python/python3/python.exe -m unittest discover -s tests -p "test_x.py" -v
```

Passing the dotted name to `discover` is not needed — the `-p` pattern is the
selector, and it is the same interpreter and the same tests the umbrella runs.

Two tracked trees are vendored third-party code and make a repo-wide search time
out before it reaches anything you wrote: `python/python3/` (the bundled
interpreter plus its `site-packages`) and `node/`. Name the trees you actually want
— `python/cinbase`, `python/input_methods`, `PIMETextService`, `libIME2`,
`go-backend`, `PIMELauncher`, `tests`, `docs`, `installer` — and a whole-tree grep
is unnecessary; `.tools/` is excluded through `.git/info/exclude`, so a search that
does reach it is looking for a toolchain you are not supposed to edit anyway.

Commits on this checkout also pass a pre-commit gate that runs the Python backend
suite on the shipped interpreter, skipping the suite's slow layer — regenerating
every committed cinbase table through the converter — unless a staged path touches
`python/cinbase/cin|json|tools` or the check itself, which is the case that pays
for it. `tests/verify_windows.sh` prints the seconds each layer took; quote that
line rather than a figure copied into a doc.
It skips by exporting `PIME_SKIP_TABLE_REGEN=1`, which only
`tests/test_cinbase_tables.py` honours; `tests/verify_windows.sh` never sets it,
so the full gate always regenerates. The gate is versioned at
`tests/hooks/pre-commit`; recreate it with
`cp tests/hooks/pre-commit .git/hooks/ && chmod +x .git/hooks/pre-commit`.
A manual `unittest discover` inherits that variable from whatever shell you typed
it in, and the suite reports the difference only as one extra skip in its
`OK (skipped=N)` line. So a `Validation` line names the skip count it actually
observed, and a commit touching a cinbase table or the converter is claimed green
only after a run with the variable explicitly unset.
Product worktrees skip it (they carry no `tests/`), and
`git commit --no-verify` carries a deliberately mid-refactor commit that the
next commit makes green.

On a worktree cut from the product master, the two Rust style gates need a
wider base than this branch offers. The vendored `rustfmt` disagrees with the
runner's rustfmt — the same drift `upstream-pr.md` hits when syncing — so run
`cargo fmt` / `rustfmt --check` scoped to the files your branch touches: a
whole-crate pass rewrites files the PR must not carry. And
`cargo clippy -- -D warnings` fails on warnings only local master has fixed
(e.g. `BackendRegistry`'s `new_without_default`); run clippy without `-D` and
judge your change by the warning set against the base commit.

The C++/TSF text service and the NSIS installer build here as well, in two
scripts that are not part of the everyday run because they are slow:

```
bash tests/build_windows_artifacts.sh    # text service (x86/x64/ARM64) + launcher
bash tests/build_windows_installer.sh     # the NSIS installer
```

`build_windows_artifacts.sh` ends by loading the ARM64X forwarder from an
ARM64 process and from an emulated x64 process, and checks that each one
reaches its own backend. What still needs Windows CI is the signed installer
and the text service running inside a live TSF host.

`docs/agents/windows-toolchain.md` has the pinned versions and why each one
(Go 1.25 for `GOARCH=386`, the GNU Rust host, and so on), plus the PATH
helpers for running the tools by hand.

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
