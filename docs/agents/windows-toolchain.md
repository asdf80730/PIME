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

The text service and the installer have their own scripts, because they are
slow — see [Building the text service and the installer](#building-the-text-service-and-the-installer).

## What gets installed, and why each version

| Component | Version | Reason |
|---|---|---|
| Go | 1.25.14 (windows/arm64) | The shipped backend is 32-bit, so the local run cross-builds `GOOS=windows GOARCH=386`. **Go 1.26 dropped `GOARCH=386`**, and 1.25 is the last line that still supports it. |
| Node | 22.23.4 (win/arm64) | Matches CI's Node 22.x. The repo also ships a 32-bit `node/node.exe`, which the verification runs directly; this host-native build is for `npm test` and tooling. |
| Bun | 1.4.4 (windows/arm64) | `Bun.YAML.parse` is the only parser available here that validates every `.github/**/*.yaml` plus `appveyor.yml` before a push. |
| Rust | stable 1.99.1, host `x86_64-pc-windows-gnu` | `PIMELauncher/.cargo/config.toml` pins `i686-pc-windows-msvc`, which needs Visual Studio. The GNU toolchain runs the same tests natively (x86-64 binaries run under emulation on ARM64). `rustfmt` and `clippy` are added as components. |
| mingw-w64 GCC | 16.2.0 (winlibs, UCRT, posix-seh) | Builds the two pure-C++ helpers: `tests/json_utils_test.cpp` (with the vendored gtest) and `tests/composition_cursor_test.cpp`. Nothing from this toolchain is shipped. It also carries `clang-cl`, `lld-link`, `llvm-rc`, `llvm-lib` and `ninja`, which build the text service. |
| CMake | 4.2.8 (portable, x86_64) | Configures the upstream `CMakeLists.txt` for the text service and the launcher. |
| Windows SDK + MSVC CRT | Win11 SDK 10.0.26100, CRT 14.44.17.14 (x86, x64, arm64) | `xwin` splats the redistributable SDK and CRT into `.tools/msvc`, so `clang-cl` can compile against real Windows headers and link against the real import libraries. Only the static release CRT (`libcmt`) is kept. |
| NSIS | 3.08 (portable) | Builds `installer/installer.nsi` into the installer `.exe`. The `StdUtils` plugin is vendored in `installer/`. |

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

`.tools/env.sh` prepends PATH entries in both formats, because some
non-interactive harness shells resolve PATH entries only in Windows form.
If a tool there still reports `command not found`, run it by relative path
(`./.tools/go/bin/go.exe`) or through `cmd.exe /c`.

## Building the text service and the installer

The C++/TSF text service and the NSIS installer used to be CI-only. Both build
here now.

```
bash tests/build_windows_artifacts.sh    # text service (x86/x64/ARM64) + launcher
bash tests/build_windows_installer.sh     # the NSIS installer
```

`build_windows_artifacts.sh` configures the upstream CMake project three times
with the toolchain files in `tests/toolchains/`. They use `clang-cl` and
`lld-link` from `.tools/mingw64` against the SDK and CRT that `xwin` splatted
into `.tools/msvc`, so no Visual Studio installation is needed. The script
also stages the results in the layout `installer/installer.nsi` expects, under
`.tools/stage/`.

### The ARM64X forwarder

One piece of MSVC's `link.exe` has no `lld-link` equivalent: the ARM64X
forwarder DLL (`PIMETextService.dll`). Upstream links it with

```
link /nologo /dll /noentry /nodefaultlib /machine:arm64x
     /defArm64Native:PIMETextService_arm64x_arm64.def
     /def:PIMETextService_arm64x_x64.def
     /out:PIMETextService.dll
```

`link.exe` synthesises the whole ARM64X layout itself: the two export tables
(the native ARM64 one and the emulated x64 one), the CHPE metadata block, the
`.a64xrm` redirection table and the ARM64X dynamic relocations that tell the
loader to swap one export table for the other. `lld-link` only carries ARM64X
metadata that already exists in its inputs, and given nothing but `/def`
files it writes no output at all.

`tests/arm64x/` therefore hands `lld-link` the two metadata objects the
layout needs — a native ARM64 load configuration and an ARM64EC one that also
carries the CHPE metadata block — and the result is a pure forwarder: no code
of its own, just the two export tables.

`tests/arm64x/verify-forwarder.sh` proves the result. It loads the forwarder
from an ARM64 process and from an emulated x64 process, and checks that
`DllGetClassObject` resolves into `PIMETextService_arm64.dll` in the first
and into `PIMETextService_x64.dll` in the second. That routing is the whole
point of the ARM64X image: a 32-bit or emulated x64 host loads the same
registered `InprocServer32` DLL and still reaches the x64 backend.

`tests/arm64x/meta.py` prints the ARM64X metadata of a PE — the export
tables, the load configuration, the CHPE metadata block and the decoded
ARM64X dynamic relocations — which is how the layout was worked out against
a real Windows ARM64X binary.

### The installer

`build_windows_installer.sh` stages the artifacts, the installer sources and
the `python`/`node` payload trees (as directory junctions, so NSIS does not
copy 190 MB) into `.tools/stage/`, then runs `makensis` from
`.tools/stage/installer/`. NSIS resolves the script's `..\build\...` paths
against the **current working directory**, not the script's own directory,
which is why the script is copied next to the staging tree. The upstream
`installer/` directory is never modified.

The result is `.tools/stage/installer/PIME-<version>-setup.exe`. It asks for
elevation, because it installs into `C:\Program Files (x86)\PIME` and
registers the text service with `regsvr32`.

### What still needs CI

- **Signing** — `.github/workflows/build-and-sign.yaml` signs the binaries
  and the installer. The local installer is unsigned.
- **The text service inside a live TSF host** — building it here proves the
  sources compile and link for all three architectures. That the installed
  text service actually loads into an input method is what the CI job
  exercises, and it needs a real IME session.

## Notes

- `tests/chewing_test.py` drives the Windows desktop and asks for a target
  window interactively; run it by hand, not from a script.
- The Rust suite runs with `--test-threads=1`: the integration tests share the
  machine's pipe and backend slots, and parallel runs starve each other on an
  emulated host.
