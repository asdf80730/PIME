#!/usr/bin/env bash
# Local verification for a Linux checkout (WSL or bare Debian).
#
# Generated with assistance from DeepSeek V4.1 Flash.
#
# Runs every layer that can run without Windows: the GitHub workflow and
# issue-form YAML, the repo's own conventions (PR base, AI declarations, tracker
# layout), the pasted PR bodies, the host and bundled Python backends,
# Node, the pure-C++ helpers (host build + Wine for UTF-16 semantics), the Go
# backend (Linux tests + Windows cross-build), and the Rust launcher (tests under
# Wine, plus fmt/clippy) when the toolchain exists.
# Windows-only layers stay in .github/workflows/build-and-sign.yaml.

set -u

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

BUILD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/pime-local-tests.XXXXXX")

# A step runs in its own session; if the run is interrupted (Ctrl-C, or the
# harness's job deadline) the step's session has to go with it, or a Wine prefix
# stays busy for the next run.
ACTIVE_STEP=
ACTIVE_WATCHDOG=
cleanup() {
    if [ -n "$ACTIVE_STEP" ]; then
        kill -TERM -- "-$ACTIVE_STEP" 2>/dev/null
        ACTIVE_STEP=
    fi
    if [ -n "$ACTIVE_WATCHDOG" ]; then
        kill -TERM -- "-$ACTIVE_WATCHDOG" 2>/dev/null
        ACTIVE_WATCHDOG=
    fi
    rm -rf "$BUILD_DIR"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

failures=0
skipped=0

# The run is long: a file edited while it goes leaves every PASS above
# predating that edit, invisibly. Snapshot the tree the run speaks for so the
# tally can say which layers the reader may no longer trust. Mirrors
# tests/verify_windows.sh.
HEAD_BEFORE=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)
STATUS_BEFORE=$(git -C "$ROOT" status --porcelain 2>/dev/null || echo unknown)

pass() { printf 'PASS  %s\n' "$1"; }
skip() { printf 'SKIP  %s (%s)\n' "$1" "$2"; skipped=$((skipped + 1)); }

# Wine answers an unimplemented import by starting winedbg and waiting, so a
# single new test can hold the whole run: 25 minutes of CI budget went into one
# such hang. Bound every step, and take the step's whole session with it, since
# the hung program is a grandchild (wine -> winedbg) that a plain `timeout`
# would leave behind holding the Wine prefix.
STEP_TIMEOUT=${STEP_TIMEOUT:-600}

run_bounded() {
    local seconds=$1
    shift

    if ! command -v setsid >/dev/null 2>&1; then
        "$@"
        return
    fi

    setsid bash -c 'set -u; "$@"' _ "$@" &
    local pid=$!
    local marker="$BUILD_DIR/hung.$$"
    local watchdog

    # The watchdog gets its own session too: killing it with `kill $watchdog`
    # would leave its `sleep` child holding the run's stdout, so the pipeline
    # that started the suite would not finish until the deadline passed.
    setsid bash -c '
        sleep "$1"
        : >"$2"
        kill -TERM -- "-$3" 2>/dev/null
        sleep 5
        kill -KILL -- "-$3" 2>/dev/null
    ' _ "$seconds" "$marker" "$pid" &
    watchdog=$!

    local status=0
    ACTIVE_STEP=$pid
    ACTIVE_WATCHDOG=$watchdog
    wait "$pid" || status=$?
    ACTIVE_STEP=
    ACTIVE_WATCHDOG=
    kill -TERM -- "-$watchdog" 2>/dev/null
    wait "$watchdog" 2>/dev/null

    if [ -e "$marker" ]; then
        rm -f "$marker"
        return 124
    fi
    return "$status"
}

step() {
    local name=$1
    shift
    printf '\n== %s ==\n' "$name"
    local status=0
    run_bounded "$STEP_TIMEOUT" "$@" || status=$?
    case "$status" in
        0)
            pass "$name"
            ;;
        124)
            printf 'HANG  %s (killed after %ss; rerun by hand: %s)\n' \
                "$name" "$STEP_TIMEOUT" "$*"
            failures=$((failures + 1))
            ;;
        125)
            skip "$name" 'not applicable here'
            ;;
        *)
            printf 'FAIL  %s (exit %s)\n' "$name" "$status"
            failures=$((failures + 1))
            ;;
    esac
}

python_cmd() {
    # `command -v python3` is fooled by the Microsoft Store stub, which
    # resolves and then exits 49; the gate must be a real run. Prefer the
    # bundled python/python3/python.exe — the shipped runtime CI exercises —
    # and fall back to a PATH python3 that actually executes.
    if [ -f "$ROOT/python/python3/python.exe" ] &&
       "$ROOT/python/python3/python.exe" -c 'import sys' >/dev/null 2>&1; then
        printf '%s\n' "$ROOT/python/python3/python.exe"
    elif command -v python3 >/dev/null 2>&1 &&
         python3 -c 'import sys' >/dev/null 2>&1; then
        printf 'python3\n'
    else
        return 1
    fi
}

python_syntax() {
    # Bundled runtime under python/python3 is a shipped dependency; checking it
    # only adds noise and time. A zero-write compile() sweep replaces
    # compileall, which exists to write .pyc and ignores
    # PYTHONDONTWRITEBYTECODE, leaving __pycache__ trees for a later git add
    # to sweep into a commit. tokenize.open honors each file's PEP 263 cookie.
    "$PY" - "$ROOT/python" <<'PYEOF'
import pathlib
import sys
import tokenize

base = pathlib.Path(sys.argv[1])
failed = 0
for path in sorted(base.rglob("*.py")):
    if "python3" in path.parts:
        continue
    try:
        with tokenize.open(path) as source:
            compile(source.read(), str(path), "exec")
    except (SyntaxError, UnicodeDecodeError) as exc:
        print(f"{path}: {exc}", file=sys.stderr)
        failed = 1
sys.exit(failed)
PYEOF
}

yaml_parse() {
    # python3 has no PyYAML, and GitHub only reports a broken workflow or issue
    # form after a push (forms are parsed when rendered from the default branch),
    # so parse every hand-written YAML with Bun before it gets that far.
    local files=()
    mapfile -t files < <(find .github -type f \( -name '*.yml' -o -name '*.yaml' \) -print
                         printf '%s\n' appveyor.yml)
    bun -e 'for (const f of process.argv.slice(1)) Bun.YAML.parse(await Bun.file(f).text())' \
        "${files[@]}" &&
        printf 'parsed %d files\n' "${#files[@]}"
}

shellcheck_all() {
    # The harness scripts gate every other check in this repo; a misquoted
    # expansion turns one into a silent no-op (scalar used as an array,
    # word-split path). Error severity only: definite bugs, not style.
    shellcheck -S error tests/*.sh
}

nsis_smoke() {
    # Linux makensis (3.08 here) preprocesses and assembles installer.nsi; what
    # it lacks is build.bat's Windows output, which shows up only as "File: ...
    # no files found". Make every File directive non-fatal in a scratch copy and
    # compile, so the script, its includes and its LogicLib blocks are checked
    # locally. Packaging and signing stay in Windows CI.
    local tmp status
    tmp=$(mktemp -d)
    cp -r "$ROOT/installer" "$tmp/"
    cp "$ROOT/version.txt" "$ROOT/LGPL-2.0.txt" "$ROOT/PSF.txt" "$ROOT/LICENSE.txt" "$tmp/"
    sed -E -i 's/^([[:space:]]*)File /\1File \/nonfatal /' "$tmp/installer/installer.nsi"
    (cd "$tmp" && makensis -V1 installer/installer.nsi) >"$tmp/makensis.log" 2>&1
    status=$?
    if [ "$status" -ne 0 ]; then
        printf 'makensis failed:\n'
        tail -20 "$tmp/makensis.log"
    fi
    rm -rf "$tmp"
    return "$status"
}

python_tests() {
    "$PY" -m unittest discover -s tests -p 'test_*.py' -v
}

python_bundled_tests() {
    # The installer ships this interpreter; run the same suite on it.
    # The bundled Python under Wine can abort in `init_sys_streams` with
    # WinError 6 when stdout is a regular file, so `tests/run_local_tests.sh >
    # log` would fail this step alone. A pipe is accepted, hence `| cat` and
    # PIPESTATUS.
    WINEDEBUG=-all wine python/python3/python.exe \
        -m unittest discover -s tests -p 'test_*.py' -v 2>&1 | cat
    return "${PIPESTATUS[0]}"
}

node_tests() {
    if command -v npm >/dev/null 2>&1; then
        (cd node && npm test)
    else
        (cd node && node --test tests/nimeServer.test.js &&
            node test/server.test.js && node test/loadServices.test.js)
    fi
}

cpp_json_test() {
    local gtest=libIME2/lib/googletest-release-1.10.0/googletest
    g++ -std=c++17 -O1 -pthread \
        -I PIMETextService \
        -I json/single_include \
        -I "$gtest/include" -I "$gtest" \
        tests/json_utils_test.cpp \
        "$gtest/src/gtest-all.cc" "$gtest/src/gtest_main.cc" \
        -o "$BUILD_DIR/json_utils_test" &&
        "$BUILD_DIR/json_utils_test"
}

cpp_cursor_wine_test() {
    # Linux wchar_t is 32-bit; the helper indexes a Windows UTF-16 buffer, so
    # cross-compile and run under Wine instead of building for the host.
    i686-w64-mingw32-g++ -std=c++17 -O1 -static \
        -I PIMETextService \
        tests/composition_cursor_test.cpp \
        -o "$BUILD_DIR/composition_cursor_test.exe" &&
        WINEDEBUG=-all wine "$BUILD_DIR/composition_cursor_test.exe"
}

go_all_tests() {
    # -count=1: a cached `ok` is not evidence. The hole was measured on the
    # Windows box, where an installed PIME leaves a live %APPDATA%\Rime and
    # the rime TestRealRime* tests fail a fresh arm64 run while the cache
    # kept reporting ok (docs/agents/verification.md, Go backend). On Linux
    # those tests skip because APPDATA is unset, so fresh runs stay green —
    # measured on go1.21.13: 4 packages ok, re-timed 0.005-0.014s.
    (cd go-backend && "$GO" test -count=1 ./...)
}

go_windows_build() {
    # Tests compile the Linux variants; the shipped binary is Windows/386.
    mkdir -p "$BUILD_DIR/go-windows"
    (cd go-backend &&
        CGO_ENABLED=0 GOOS=windows GOARCH=386 \
            "$GO" build -o "$BUILD_DIR/go-windows/" ./...)
}

rust_tests() {
    (cd PIMELauncher &&
        PATH="$(dirname "$CARGO"):$PATH" \
        CARGO_TARGET_I686_PC_WINDOWS_GNU_RUNNER=wine \
        WINEDLLOVERRIDES="bcryptprimitives=n;mscoree=;mshtml=" \
            "$CARGO" test --target i686-pc-windows-gnu)
}

rust_lint() {
    (cd PIMELauncher &&
        "$CARGO" fmt --check &&
        "$CARGO" clippy --target i686-pc-windows-gnu --all-targets -- -D warnings)
}

# A step runs in a fresh bash so the deadline can take its whole session down;
# the function and everything it reads therefore has to be exported.
export ROOT BUILD_DIR GO CARGO PY
export -f python_syntax yaml_parse nsis_smoke python_tests python_bundled_tests \
    node_tests cpp_json_test cpp_cursor_wine_test go_all_tests go_windows_build \
    rust_tests rust_lint shellcheck_all

printf 'PIME local verification (root: %s)\n' "$ROOT"

if command -v bun >/dev/null 2>&1; then
    step 'GitHub YAML parses' yaml_parse
else
    skip 'GitHub YAML parses' 'bun missing (Bun.YAML.parse is the only parser here)'
fi

if command -v makensis >/dev/null 2>&1; then
    step 'NSIS installer script assembles' nsis_smoke
else
    skip 'NSIS installer script assembles' 'makensis missing; apt-get install nsis'
fi

step 'PR branch starts at origin/master' "$ROOT/tests/check_pr_scope.sh"
step 'PR scope gate self-test' "$ROOT/tests/check_pr_scope_test.sh"
step 'Worktree test driver self-test' "$ROOT/tests/run_worktree_tests_test.sh"
step 'Added files carry an AI declaration' "$ROOT/tests/check_ai_declarations.sh"
step 'Local issue tracker layout' "$ROOT/tests/check_tracker_layout.sh"
step 'Tracked code cites no .scratch/' "$ROOT/tests/check_scratch_refs.sh"
step 'Scratch-ref gate self-test' "$ROOT/tests/check_scratch_refs_test.sh"
step 'PR bodies carry the AI declaration' "$ROOT/tests/check_pr_bodies.sh"
step 'PR body gate self-test' "$ROOT/tests/check_pr_bodies_test.sh"

# Product PR branches carry no tests/, so a commit message carried over by
# `git commit -C` promises a test the upstream reviewer cannot find. The gate
# skips (125) on an integration branch; its contract is pinned either way.
step 'PR commit messages claim only their own diff' "$ROOT/tests/check_pr_commit_claims.sh"
step 'Commit-claims gate self-test' "$ROOT/tests/check_pr_commit_claims_test.sh"
# The gate needs a ref to read, so it runs at delivery time; the contract that
# keeps it able to catch the unhardened workflows lives here.
step 'Fork CI noise gate self-test' "$ROOT/tests/check_fork_ci_noise_test.sh"
step 'Integration ref candidates' "$ROOT/tests/check_integration_ref.sh"

# Scripts committed from a core.filemode=false checkout land 100644, and
# step() executes them directly: exit 126 right here. The gate pins the
# bit in the tree; the pre-commit hook stops it at staging.
step 'Shell scripts carry the exec bit' "$ROOT/tests/check_sh_exec_bits.sh"
step 'Exec-bit gate self-test' "$ROOT/tests/check_sh_exec_bits_test.sh"

if command -v shellcheck >/dev/null 2>&1; then
    step 'Harness shell scripts lint' shellcheck_all
else
    skip 'Harness shell scripts lint' 'shellcheck missing; apt-get install shellcheck'
fi

# compileall and unittest discovery would otherwise leave __pycache__ trees
# inside the checkout, ready for a later `git add` to sweep into a commit
# (the product .gitignore does not cover them).
export PYTHONDONTWRITEBYTECODE=1
PY="$(python_cmd)" || PY=''
if [ -n "$PY" ]; then
    step 'Python syntax (all input methods)' python_syntax
    step 'Python backend tests' python_tests
else
    skip 'Python backend tests' 'no runnable python3 (PATH stub exits 49, bundled exe failed to run)'
fi

if command -v wine >/dev/null 2>&1 && [ -f python/python3/python.exe ]; then
    step 'Python backend tests (bundled Python under Wine)' python_bundled_tests
else
    skip 'Python backend tests (bundled Python)' 'wine or bundled python.exe missing'
fi

if command -v node >/dev/null 2>&1; then
    step 'Node backend tests' node_tests
else
    skip 'Node backend tests' 'node missing'
fi

if command -v g++ >/dev/null 2>&1 &&
   [ -f libIME2/lib/googletest-release-1.10.0/googletest/src/gtest-all.cc ] &&
   [ -f json/single_include/nlohmann/json.hpp ]; then
    step 'C++ JsonUtils tests (host g++)' cpp_json_test
else
    skip 'C++ JsonUtils tests' 'g++ or vendored gtest/nlohmann headers missing'
fi

if command -v i686-w64-mingw32-g++ >/dev/null 2>&1 && command -v wine >/dev/null 2>&1; then
    step 'C++ composition cursor test (Wine)' cpp_cursor_wine_test
else
    skip 'C++ composition cursor test' 'mingw-w64 g++ or wine missing'
fi

if command -v go >/dev/null 2>&1; then
    GO=go
elif [ -x /usr/local/go/bin/go ]; then
    GO=/usr/local/go/bin/go
elif [ -x /opt/go/bin/go ]; then
    GO=/opt/go/bin/go
else
    GO=
fi

if [ -n "$GO" ]; then
    step 'Go backend tests' go_all_tests
    step 'Go backend Windows/386 build' go_windows_build
else
    skip 'Go backend tests' 'go missing'
fi

CARGO=${CARGO_BIN:-$(command -v cargo 2>/dev/null || true)}
if [ -z "$CARGO" ] && [ -x "${CARGO_HOME:-$HOME/.cargo}/bin/cargo" ]; then
    CARGO="${CARGO_HOME:-$HOME/.cargo}/bin/cargo"
fi

if [ -n "$CARGO" ] && command -v wine >/dev/null 2>&1; then
    RUSTUP=$(dirname "$CARGO")/rustup
    if [ -x "$RUSTUP" ] && "$RUSTUP" target list --installed 2>/dev/null | grep -qx 'i686-pc-windows-gnu'; then
        step 'Rust launcher tests (Wine)' rust_tests
        if "$CARGO" fmt --version >/dev/null 2>&1 && "$CARGO" clippy --version >/dev/null 2>&1; then
            step 'Rust formatting and clippy' rust_lint
        else
            skip 'Rust formatting and clippy' 'rustfmt/clippy missing; rustup component add rustfmt clippy'
        fi
    else
        skip 'Rust launcher tests' 'i686-pc-windows-gnu target missing; see docs/agents/wine.md'
    fi
else
    skip 'Rust launcher tests' 'cargo or wine missing; see docs/agents/wine.md'
fi

# Trust anchor: if HEAD or the worktree moved while the layers ran, the PASS
# lines speak for the old tree — say so instead of letting a green tally hide
# the drift; the reader reruns the affected layers on the final bytes.
HEAD_NOW=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)
STATUS_NOW=$(git -C "$ROOT" status --porcelain 2>/dev/null || echo unknown)
if [ "$HEAD_NOW" != "$HEAD_BEFORE" ]; then
    printf 'WARN  HEAD moved during the run (%s -> %s): no layer above validated the new commits\n' "${HEAD_BEFORE:0:7}" "${HEAD_NOW:0:7}"
fi
if [ "$STATUS_NOW" != "$STATUS_BEFORE" ]; then
    printf '%s\n' "$STATUS_BEFORE" >"$BUILD_DIR/status.before"
    printf '%s\n' "$STATUS_NOW" >"$BUILD_DIR/status.now"
    printf 'WARN  worktree changed during the run; these paths may predate your edits:\n'
    comm -3 "$BUILD_DIR/status.before" "$BUILD_DIR/status.now" | sed 's/^/    /'
    rm -f "$BUILD_DIR/status.before" "$BUILD_DIR/status.now"
fi
printf '\n%d failed, %d skipped\n' "$failures" "$skipped"
if [ "$failures" -ne 0 ]; then
    exit 1
fi
