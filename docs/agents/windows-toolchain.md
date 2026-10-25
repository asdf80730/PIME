# Windows local toolchain

PIME ships a Windows-only product, but the repository is developed on Linux
with Wine. This machine is a Windows 11 ARM64 box, so every locally verifiable
layer can run natively here — no Wine, no WSL, no cross-compile dance for the
test suites.

The toolchain is installed **inside the checkout**, under `.tools/`:

- no entry under `Program Files`
- no registry change
- no edit to the system `PATH`

`.tools/` is excluded through `.git/info/exclude` (local only, never upstream),
so it stays out of every commit. Deleting the directory restores the machine's
previous state exactly.

## Install

```
bash tests/install_windows_toolchain.sh
```

The script is idempotent — each component is skipped when it is already
present. It downloads into `.tools/.downloads/` and removes that afterwards.

Then run the layers:

```
bash tests/verify_windows.sh
```

## What gets installed, and why each version

| Component | Version | Reason |
|---|---|---|
| Go | 1.25.14 (windows/arm64) | The shipped backend is 32-bit, so the local run cross-builds `GOOS=windows GOARCH=386`. **Go 1.26 dropped `GOARCH=386`**, and 1.25 is the last line that still supports it. |
| Node | 22.23.4 (win/arm64) | Matches CI's Node 22.x. The repo also ships a 32-bit `node/node.exe`, which the verification runs directly; this host-native build is for `npm test` and tooling. |
| Bun | 1.4.4 (windows/arm64) | `Bun.YAML.parse` is the only parser available here that validates every `.github/**/*.yaml` plus `appveyor.yml` before a push. |
| Rust | stable 1.99.1, host `x86_64-pc-windows-gnu` | `PIMELauncher/.cargo/config.toml` pins `i686-pc-windows-msvc`, which needs Visual Studio. The GNU toolchain runs the same tests natively (x86-64 binaries run under emulation on ARM64). `rustfmt` and `clippy` are added as components. |
| mingw-w64 GCC | 16.2.0 (winlibs, UCRT, posix-seh) | Builds the two pure-C++ helpers: `tests/json_utils_test.cpp` (with the vendored gtest) and `tests/composition_cursor_test.cpp`. Nothing from this toolchain is shipped. |

The Git submodule `libIME2` supplies the vendored gtest, and
`python/input_methods/rime/brise` supplies the Rime data; the installer
initialises both.

## Using the tools by hand

Git Bash:

```sh
source .tools/env.sh
go version
```

`cmd.exe`:

```bat
.tools\pime-env.bat cargo test --target x86_64-pc-windows-gnu
```

Both helpers only prepend the tool directories to `PATH` for the current
process.

## What still needs CI

Two layers cannot run here:

- **C++/TSF text service** — the root `CMakeLists.txt` uses MSVC flags
  (`/MT`, `/D_UNICODE`), and TSF needs a Windows host with a real input method
  framework.
- **NSIS installer** — `installer/installer.nsi` loads vendored Windows-only
  NSIS plugins (for example `StdUtils`), and the installer packages the
  JavaScript input methods that `build.bat` generates.

Both are covered by the `windows-2025` job in
`.github/workflows/build-and-sign.yaml`. Do not claim such a change verified
without a green run there.

## Notes

- `tests/chewing_test.py` drives the Windows desktop and asks for a target
  window interactively; run it by hand, not from a script.
- The Rust suite runs with `--test-threads=1`: the integration tests share the
  machine's pipe and backend slots, and parallel runs starve each other on an
  emulated host.
