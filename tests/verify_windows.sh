#!/usr/bin/env bash
# Local verification for this Windows checkout (native, no Wine, no WSL).
#
# Every tool lives under .tools/ inside the project (see .tools/env.sh); this
# script only puts those directories on PATH for the duration of the run and
# touches nothing outside the checkout.
#
# Layers it covers:
#   - GitHub/AppVeyor YAML parse (Bun)
#   - Python backend suite on the shipped interpreter
#   - Node backend suite on the shipped node.exe
#   - Go backend tests + the shipped Windows/386 cross-build
#   - Rust launcher tests, cargo fmt, cargo clippy
#   - C++ pure helpers (JsonUtils gtest, CompositionCursor) via mingw-w64 g++
#
# The C++/TSF text service and the NSIS installer need MSVC and stay in CI
# (docs/agents/verification.md).

set -u

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TOOLS="$ROOT/.tools"
RUN_DIR="$TOOLS/.run"

failures=0
passed=0

pass() { printf 'PASS  %s\n' "$1"; passed=$((passed + 1)); }
fail() { printf 'FAIL  %s\n' "$1"; failures=$((failures + 1)); }

mkdir -p "$RUN_DIR"

# Preflight: the toolchain lives under .tools/ (excluded from git), so a fresh
# clone has to install it before this script can run.
missing=()
for tool in "$TOOLS/go/bin/go.exe" "$TOOLS/node/node.exe" "$TOOLS/bun/bun.exe" \
	"$TOOLS/cargo/bin/cargo.exe" "$TOOLS/mingw64/bin/g++.exe"; do
	[ -x "$tool" ] || missing+=("$tool")
done
if [ ${#missing[@]} -gt 0 ]; then
	printf 'MISSING toolchain files:\n'
	printf '  %s\n' "${missing[@]}"
	printf 'Run: bash tests/install_windows_toolchain.sh\n'
	exit 1
fi

# Native Windows programs need a Windows-style PATH: this shell keeps PATH
# colon-separated, which CreateProcess cannot search. Each step runs through a
# generated .bat that sets the tool directories in Windows form.
# A step's environment: the tool directories plus the per-user homes the
# toolchains look for (cargo is a rustup proxy and needs RUSTUP_HOME).
write_step() {
	local bat="$RUN_DIR/step.bat"
	local win_tools win_root
	win_tools=$(cygpath -w "$TOOLS")
	win_root=$(cygpath -w "$ROOT")
	{
		printf '%s\r\n' '@echo off'
		printf '%s\r\n' "set \"PATH=$win_tools\\mingw64\\bin;$win_tools\\go\\bin;$win_tools\\bun;$win_tools\\node;$win_tools\\cargo\\bin;$win_tools\\bin;%PATH%\""
		printf '%s\r\n' "set \"GOROOT=$win_tools\\go\""
		printf '%s\r\n' "set \"GOPATH=$win_tools\\gopath\""
		printf '%s\r\n' "set \"CARGO_HOME=$win_tools\\cargo\""
		printf '%s\r\n' "set \"RUSTUP_HOME=$win_tools\\rustup\""
		printf '%s\r\n' "cd /d \"$win_root\""
		printf '%s\r\n' "$*"
	} >"$bat"
}

run_native() {
	local label="$1"
	shift
	write_step "$*"
	if "$RUN_DIR/step.bat" >"$RUN_DIR/step.log" 2>&1; then
		pass "$label"
	else
		fail "$label"
		tail -n 15 "$RUN_DIR/step.log" | sed 's/^/      /'
	fi
}

# Same, but keeps the step output visible (for failing or noisy steps).
run_native_verbose() {
	local label="$1"
	shift
	write_step "$*"
	local log
	log=$("$RUN_DIR/step.bat" 2>&1)
	if [ $? -eq 0 ]; then
		pass "$label"
	else
		fail "$label"
	fi
	printf '%s\n' "$log" | tail -n 12 | sed 's/^/      /'
}

printf 'PIME local verification (root: %s)\n' "$ROOT"

# --- YAML -----------------------------------------------------------------
yaml_files=$(find .github -type f \( -name '*.yml' -o -name '*.yaml' \) -print; printf '%s\n' appveyor.yml)
yaml_args=""
for f in $yaml_files; do
	yaml_args="$yaml_args \"$(cygpath -w "$f")\""
done
run_native 'GitHub YAML parses' \
	"bun.exe \"$(cygpath -w "$ROOT/tests/check_yaml.ts")\"$yaml_args"

# --- Python ---------------------------------------------------------------
run_native_verbose 'Python backend tests (bundled python.exe)' \
	'python\python3\python.exe -m unittest discover -s tests -p test_*.py'

# --- Node -----------------------------------------------------------------
run_native 'Node backend tests (bundled node.exe)' \
	'node\node.exe --test node\tests\nimeServer.test.js'
run_native 'Node backend tests (server)' \
	'node\node.exe node\test\server.test.js'
run_native 'Node backend tests (loadServices)' \
	'node\node.exe node\test\loadServices.test.js'

# --- Go -------------------------------------------------------------------
run_native 'Go backend tests' 'cd go-backend && go.exe test ./...'
run_native 'Go backend Windows/386 build' \
	'cd go-backend && set "CGO_ENABLED=0" && set "GOOS=windows" && set "GOARCH=386" && go.exe build ./...'

# --- Rust -----------------------------------------------------------------
# The repo pins i686-pc-windows-msvc (see PIMELauncher/.cargo/config.toml);
# MSVC needs Visual Studio, so the local run uses the GNU toolchain instead.
# One test thread: the integration tests share the machine's pipe and backend
# slots, and parallel runs starve each other on slow or emulated hosts.
run_native 'Rust launcher tests' \
	'cd PIMELauncher && cargo.exe test --target x86_64-pc-windows-gnu -- --test-threads=1'
run_native 'Rust cargo fmt --check' 'cd PIMELauncher && cargo.exe fmt --check'
run_native 'Rust cargo clippy' \
	'cd PIMELauncher && cargo.exe clippy --target x86_64-pc-windows-gnu --all-targets -- -D warnings'

# --- C++ pure helpers -----------------------------------------------------
gtest='libIME2/lib/googletest-release-1.10.0/googletest'
run_native 'C++ JsonUtils tests (gtest, mingw g++)' \
	"g++.exe -std=c++17 -O1 -pthread -I PIMETextService -I json/single_include -I $gtest/include -I $gtest tests\\json_utils_test.cpp $gtest/src/gtest-all.cc $gtest/src/gtest_main.cc -o .tools\\json_utils_test.exe && .tools\\json_utils_test.exe"
run_native 'C++ CompositionCursor test (mingw g++)' \
	'g++.exe -std=c++17 -O1 -static -I PIMETextService tests\\composition_cursor_test.cpp -o .tools\\composition_cursor_test.exe && .tools\\composition_cursor_test.exe'

rm -rf "$RUN_DIR"

printf '\n%d passed, %d failed\n' "$passed" "$failures"
[ "$failures" -eq 0 ]
