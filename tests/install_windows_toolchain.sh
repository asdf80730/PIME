#!/usr/bin/env bash
# Install the Windows toolchain for PIME's local verification.
#
# Everything lands under .tools/ inside the checkout: no Program Files entry,
# no registry change, no system PATH edit. Delete .tools/ and the machine is
# back to its previous state.
#
# Usage (Git Bash on Windows):
#   bash tests/install_windows_toolchain.sh
#
# Re-running is cheap: each component is skipped when it is already there.

set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TOOLS="$ROOT/.tools"
DL="$TOOLS/.downloads"

# Versions are pinned on purpose:
#   - Go 1.25 is the last line that still supports GOARCH=386, and PIME ships
#     a 32-bit backend. Go 1.26+ fails the cross-build outright.
#   - Node 22.x matches CI (the repo ships 32-bit node/node.exe; this is the
#     host-native arm64 build used for `npm test` and tooling).
#   - The Rust host triple is x86_64-pc-windows-gnu because
#     PIMELauncher/.cargo/config.toml pins i686-pc-windows-msvc, which needs
#     Visual Studio. Windows 11 ARM64 runs the x86-64 build under emulation.
GO_VERSION=1.25.14
NODE_VERSION=22.23.4
BUN_VERSION=1.4.4
MINGW_URL=https://github.com/brechtsanders/winlibs_mingw/releases/download/16.2.0posix-23.1.3-14.0.0-ucrt-r3/winlibs-x86_64-posix-seh-gcc-16.2.0-llvm-23.1.3-mingw-w64ucrt-14.0.0-r3.zip
RUSTUP_URL=https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe

# Host architecture. `uname -m` is unreliable here: Git for Windows is an
# x86-64 build, so it reports x86_64 even on an ARM64 machine (it runs under
# emulation), and `RuntimeInformation::OSArchitecture` reports the emulated
# process architecture too. Win32_Processor.Architecture is the OS answer:
# 0 = x86, 9 = x64, 12 = ARM64.
detect_arch() {
	local code
	code=$(powershell.exe -NoProfile -Command '(Get-CimInstance Win32_Processor).Architecture' 2>/dev/null |
		tr -d '\r' | tail -n 1)
	if [ "$code" = "12" ]; then
		printf 'arm64'
		return
	fi
	case "$(uname -m)" in
	arm64 | aarch64) printf 'arm64' ;;
	*) printf 'x64' ;;
	esac
}

case "$(detect_arch)" in
arm64) GO_ARCH=arm64; NODE_ARCH=arm64; BUN_ARCH=aarch64 ;;
*) GO_ARCH=amd64; NODE_ARCH=x64; BUN_ARCH=x64 ;;
esac

mkdir -p "$DL"

fetch() {
	local url="$1" out="$2"
	if [ ! -f "$out" ]; then
		printf '  downloading %s\n' "$url"
		curl -sSL --retry 3 -o "$out" "$url"
	fi
}

# --- Go --------------------------------------------------------------------
if [ ! -x "$TOOLS/go/bin/go.exe" ]; then
	printf 'Go %s (%s)\n' "$GO_VERSION" "$GO_ARCH"
	fetch "https://dl.google.com/go/go${GO_VERSION}.windows-${GO_ARCH}.zip" "$DL/go.zip"
	rm -rf "$TOOLS/go" "$TOOLS/.go-tmp"
	mkdir -p "$TOOLS/.go-tmp"
	unzip -q "$DL/go.zip" -d "$TOOLS/.go-tmp"
	mv "$TOOLS/.go-tmp/go" "$TOOLS/go"
	rm -rf "$TOOLS/.go-tmp"
else
	printf 'Go already installed\n'
fi

# --- Node ------------------------------------------------------------------
if [ ! -x "$TOOLS/node/node.exe" ]; then
	printf 'Node %s (%s)\n' "$NODE_VERSION" "$NODE_ARCH"
	fetch "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-win-${NODE_ARCH}.zip" "$DL/node.zip"
	rm -rf "$TOOLS/node" "$TOOLS/.node-tmp"
	mkdir -p "$TOOLS/.node-tmp"
	unzip -q "$DL/node.zip" -d "$TOOLS/.node-tmp"
	mv "$TOOLS/.node-tmp/node-v${NODE_VERSION}-win-${NODE_ARCH}" "$TOOLS/node"
	rm -rf "$TOOLS/.node-tmp"
else
	printf 'Node already installed\n'
fi

# --- Bun -------------------------------------------------------------------
if [ ! -x "$TOOLS/bun/bun.exe" ]; then
	printf 'Bun %s (%s)\n' "$BUN_VERSION" "$BUN_ARCH"
	fetch "https://github.com/oven-sh/bun/releases/download/bun-v${BUN_VERSION}/bun-windows-${BUN_ARCH}.zip" "$DL/bun.zip"
	rm -rf "$TOOLS/bun" "$TOOLS/.bun-tmp"
	mkdir -p "$TOOLS/.bun-tmp"
	unzip -q "$DL/bun.zip" -d "$TOOLS/.bun-tmp"
	mkdir -p "$TOOLS/bun"
	mv "$TOOLS/.bun-tmp/bun-windows-${BUN_ARCH}/bun.exe" "$TOOLS/bun/bun.exe"
	rm -rf "$TOOLS/.bun-tmp"
else
	printf 'Bun already installed\n'
fi

# --- mingw-w64 (only for the two pure-C++ helpers) --------------------------
if [ ! -x "$TOOLS/mingw64/bin/g++.exe" ]; then
	printf 'mingw-w64 GCC (winlibs)\n'
	fetch "$MINGW_URL" "$DL/mingw.zip"
	rm -rf "$TOOLS/mingw64" "$TOOLS/.mingw-tmp"
	mkdir -p "$TOOLS/.mingw-tmp"
	unzip -q "$DL/mingw.zip" -d "$TOOLS/.mingw-tmp"
	mv "$TOOLS/.mingw-tmp/mingw64" "$TOOLS/mingw64"
	rm -rf "$TOOLS/.mingw-tmp"
else
	printf 'mingw-w64 already installed\n'
fi

# --- Rust ------------------------------------------------------------------
if [ ! -x "$TOOLS/cargo/bin/cargo.exe" ]; then
	printf 'Rust (stable, host x86_64-pc-windows-gnu)\n'
	fetch "$RUSTUP_URL" "$DL/rustup-init.exe"
	export RUSTUP_HOME="$TOOLS/rustup"
	export CARGO_HOME="$TOOLS/cargo"
	"$DL/rustup-init.exe" -y --no-modify-path --profile minimal \
		--default-host x86_64-pc-windows-gnu --default-toolchain stable
	"$TOOLS/cargo/bin/rustup.exe" component add rustfmt clippy
else
	printf 'Rust already installed\n'
fi

# --- shims -----------------------------------------------------------------
mkdir -p "$TOOLS/bin"
cat >"$TOOLS/bin/node" <<'SH'
#!/bin/sh
# Shim: `node` on PATH (Git Bash) -> the portable Node build in .tools/node.
exec "$(dirname "$0")/../node/node.exe" "$@"
SH
cat >"$TOOLS/bin/node.cmd" <<'BAT'
@echo off
rem Shim: `node` on PATH -> the portable Node build in .tools\node.
"%~dp0..\node\node.exe" %*
BAT
cat >"$TOOLS/bin/npm" <<'SH'
#!/bin/sh
# Shim: `npm` on PATH (Git Bash) -> the portable Node build in .tools/node.
exec "$(dirname "$0")/../node/npm.cmd" "$@"
SH
cat >"$TOOLS/bin/python3" <<'SH'
#!/bin/sh
# Shim: `python3` on PATH (Git Bash) -> the interpreter PIME ships.
exec "$(dirname "$0")/../../python/python3/python.exe" "$@"
SH
cat >"$TOOLS/bin/python3.cmd" <<'BAT'
@echo off
rem Shim: `python3` on PATH -> the interpreter PIME ships (python\python3).
"%~dp0..\..\python\python3\python.exe" %*
BAT
chmod +x "$TOOLS/bin/node" "$TOOLS/bin/npm" "$TOOLS/bin/python3"

# --- PATH helpers ----------------------------------------------------------
cat >"$TOOLS/env.sh" <<'SH'
# PIME local toolchain, all inside the project checkout (.tools/).
# Source this from Git Bash:  source .tools/env.sh
PIME_TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PIME_TOOLS
export PATH="$PIME_TOOLS/mingw64/bin:$PIME_TOOLS/go/bin:$PIME_TOOLS/bun:$PIME_TOOLS/node:$PIME_TOOLS/cargo/bin:$PIME_TOOLS/bin:$PATH"
export GOROOT="$PIME_TOOLS/go"
export GOPATH="$PIME_TOOLS/gopath"
export CARGO_HOME="$PIME_TOOLS/cargo"
export RUSTUP_HOME="$PIME_TOOLS/rustup"
SH
cat >"$TOOLS/pime-env.bat" <<'BAT'
@echo off
rem PIME local toolchain, all inside the project checkout (.tools\).
rem Nothing here touches the system PATH, the registry, or Program Files.
set "PIME_TOOLS=%~dp0"
set "PATH=%PIME_TOOLS%mingw64\bin;%PIME_TOOLS%go\bin;%PIME_TOOLS%bun;%PIME_TOOLS%node;%PIME_TOOLS%cargo\bin;%PIME_TOOLS%bin;%PATH%"
set "GOROOT=%PIME_TOOLS%go"
set "GOPATH=%PIME_TOOLS%gopath"
set "CARGO_HOME=%PIME_TOOLS%cargo"
set "RUSTUP_HOME=%PIME_TOOLS%rustup"
%*
BAT

# --- submodules the tests need ---------------------------------------------
if [ ! -e "$ROOT/libIME2/lib/googletest-release-1.10.0/googletest/src/gtest-all.cc" ]; then
	printf 'initialising submodules (libIME2, brise)\n'
	git -C "$ROOT" submodule update --init libIME2 python/input_methods/rime/brise
fi

rm -rf "$DL"

printf '\nToolchain ready. Run:\n  bash tests/verify_windows.sh\n'
