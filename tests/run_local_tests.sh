#!/usr/bin/env bash
# Local verification for a Linux checkout (WSL or bare Debian).
#
# Generated with assistance from DeepSeek V4.1 Flash.
#
# Runs every layer that can run without Windows: the GitHub workflow and
# issue-form YAML, the pasted PR bodies, the host and bundled Python backends,
# Node, the pure-C++ helpers (host build + Wine for UTF-16 semantics), the Go
# backend (Linux tests + Windows cross-build), and the Rust launcher (tests under
# Wine, plus fmt/clippy) when the toolchain exists.
# Windows-only layers stay in .github/workflows/build-and-sign.yaml.

set -u

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

BUILD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/pime-local-tests.XXXXXX")
trap 'rm -rf "$BUILD_DIR"' EXIT

failures=0
skipped=0

pass() { printf 'PASS  %s\n' "$1"; }
skip() { printf 'SKIP  %s (%s)\n' "$1" "$2"; skipped=$((skipped + 1)); }

step() {
    local name=$1
    shift
    printf '\n== %s ==\n' "$name"
    if "$@"; then
        pass "$name"
    else
        printf 'FAIL  %s\n' "$name"
        failures=$((failures + 1))
    fi
}

python_syntax() {
    # Bundled runtime under python/python3 is a shipped dependency; checking it
    # only adds noise and time.
    python3 -m compileall -q -x '(^|/)python3(/|$)' python
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

pr_bodies() {
    # AGENTS.md §2 puts the AI declaration at the end of the message, and the
    # body is pasted by hand: a missing last line makes the human add it.
    local files=() bad=0 last
    mapfile -t files < <(find .scratch -maxdepth 1 -type f -name 'pr-*-body.md' -print 2>/dev/null)
    for f in "${files[@]}"; do
        last=$(awk 'NF { line = $0 } END { print line }' "$f")
        case "$last" in
            "Generated with assistance from"*) ;;
            *)
                printf 'missing AI declaration: %s\n' "$f"
                bad=1
                ;;
        esac
    done
    printf 'checked %d PR bodies\n' "${#files[@]}"
    [ "$bad" -eq 0 ]
}

python_tests() {
    python3 -m unittest discover -s tests -p 'test_*.py' -v
}

python_bundled_tests() {
    # The installer ships this interpreter; run the same suite on it.
    WINEDEBUG=-all wine python/python3/python.exe \
        -m unittest discover -s tests -p 'test_*.py' -v
}

node_tests() {
    if command -v npm >/dev/null 2>&1; then
        (cd node && npm test)
    else
        (cd node && node test/server.test.js && node test/loadServices.test.js)
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
    (cd go-backend && "$GO" test ./...)
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

printf 'PIME local verification (root: %s)\n' "$ROOT"

if command -v bun >/dev/null 2>&1; then
    step 'GitHub YAML parses' yaml_parse
else
    skip 'GitHub YAML parses' 'bun missing (Bun.YAML.parse is the only parser here)'
fi

step 'PR bodies carry the AI declaration' pr_bodies

if command -v python3 >/dev/null 2>&1; then
    step 'Python syntax (all input methods)' python_syntax
    step 'Python backend tests' python_tests
else
    skip 'Python backend tests' 'python3 missing'
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

printf '\n%d failed, %d skipped\n' "$failures" "$skipped"
if [ "$failures" -ne 0 ]; then
    exit 1
fi
