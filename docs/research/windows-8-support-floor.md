# Windows 8/8.1 support floor: can PIME roll back?

> **Status (2026-10-26): decided — the floor stays at Windows 10.** The
> “Recommendation: keep the Windows 10 floor” below is now the decision
> (`docs/adr/0001-windows-support-floor.md`); PR #1005 is retargeted to reject
> Windows 8.1 and older, and PR #1007 is closed. §4 is retained as the record of
> the rejected 8.1 option, not as a plan.

Reference tree: local `master` at `066e12a9a83e79216bf11624aad5c7ce198809cd`
(2026-10-26). PR [#1005](https://github.com/EasyIME/PIME/pull/1005) is open,
non-draft, `mergeStateStatus` `CLEAN`, head
`31b732d69fe415737738d591155b1cf0ab947ac8`; its base is `master`.

## TL;DR

- **Windows 8.0: NO.** The current stack cannot support it, and no plausible
  downgrade combination is supportable. Windows 8 support ended on 2016-01-13
  (extended end). Python 3.12 — the oldest release the
  current Python backend can reasonably target — requires Windows 8.1 or newer.
  Only Python 3.8 (Vista-or-newer, EOL 2024-10) would run on 8.0, alongside
  other unsupported runtimes.
- **Windows 8.1: only as an explicitly unsupported legacy build.** The current
  product cannot simply lower the installer gate. Python 3.15.1 requires
  Windows 10; Go 1.21 requires Windows 10/Server 2016; Node 22 officially
  supports Windows 10/Server 2016 (8.1 is “Experimental”); Rust 1.78 and later
  require Windows 10. A legacy build needs Python 3.12.x, Go 1.20, Rust 1.77
  with a re-pinned dependency graph (or a non-Rust launcher), UCRT/VC++ runtime
  deployment, and a real Windows 8.1 VM in the test loop.
- **PR #1005 does not lower the floor; it raises it to Windows 10.** The
  `${AtLeastWin8}` test is only a precondition. The actual gate is
  `CurrentMajorVersionNumber >= 10`, and a missing value is rejected. Windows 8
  and 8.1 therefore both fail the real check.
- **Two factual corrections are needed in #1005's comment/body.** First,
  `vcruntime140.dll` is not an in-box Windows 10 component; only the UCRT is.
  `vcruntime140` is a Visual C++ redistributable/app-local DLL, and PIME's
  Python payload carries its own copy. Second, NSIS 3.08 **does** provide
  `${AtLeastWin10}` (and `${AtLeastWin8.1}`); the PR body's “no
  `${AtLeastWin10}` test” rationale is false. The registry check is still a
  defensible manifest-independent gate, but it is not the only available
  method.
- **Recommendation:** keep the Windows 10 floor. Do not ship an 8.1 legacy
  build without a separate, clearly labelled artifact, a clean-VM matrix, and
  an explicit “no security support” statement.

## 1. Compatibility matrix

“Current” means the versions actually present in this checkout, not
`HACKING.txt` (see §7).

| Component | Current repo state | Primary-source minimum OS | Windows 8.0 | Windows 8.1 |
|---|---|---|---|---|
| Python backend | **3.15.1** embeddable (`python315.dll`; bumped in `eda0bc8`; `docs/agents/verification.md:45`) | Python 3.15: **Windows 10+**; Python 3.12: **Windows 8.1+** ([3.15 docs](https://docs.python.org/3.15/using/windows.html), [3.12 docs](https://docs.python.org/3.12/using/windows.html)) | No | No on 3.15; 3.12 only |
| Node backend | **22.23.4** 32-bit (`node/node.exe`; `docs/agents/verification.md:81`; `eda0bc8`) | Tier 1: **Windows 10/Server 2016**; Windows 8.1/Server 2012 listed as **Experimental** ([v22.23.4 BUILDING.md](https://github.com/nodejs/node/blob/v22.23.4/BUILDING.md)) | No | Experimental only |
| Go backend | `go 1.21` (`go-backend/go.mod:3`) | Go 1.21: **Windows 10/Server 2016+**; Go 1.20 is the last release that runs on Windows 7/8/Server 2008/2012 ([Go 1.21 notes](https://go.dev/doc/go1.21), [Go 1.20 notes](https://go.dev/doc/go1.20)) | Go 1.20 only | Go 1.20 only |
| Rust launcher | CI uses floating `stable` and target `i686-pc-windows-msvc` (`.github/workflows/build-and-sign.yaml:39-43`; `appveyor.yml:13-14`) | Rust 1.77: **Windows 7+**; Rust 1.78: **Windows 10+** ([1.77 platform support](https://doc.rust-lang.org/1.77.0/rustc/platform-support.html), [1.78 platform support](https://doc.rust-lang.org/1.78.0/rustc/platform-support.html)) | 1.77 only | 1.77 only |
| C++ TSF / libIME2 | C++17, `/MT`, `_WIN32_WINNT=0x0600` (`CMakeLists.txt:6-7,26`; `PIMETextService/CMakeLists.txt:7`) | TSF is “Windows XP or later” ([Microsoft TSF docs](https://learn.microsoft.com/en-us/windows/win32/tsf/text-services-framework)); PIME’s own compile target is Vista (`0x0600`) | Compile target yes; not tested on 8.0 | Compile target yes; not tested on 8.1 |
| Installer / UCRT / VC++ runtime | NSIS 3.08 (`installer.nsi`; CI pins 3.08 at `.github/workflows/build-and-sign.yaml:83-86`); `ensureVCRedist` removed in #976; launcher static since #975 | UCRT in-box **Windows 10+**; older systems via Windows Update/KB2999226 or app-local ([UCRT deployment](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-170)). Latest v14 redist supports **Windows 10/11 and Server 2016+** ([latest VC++ redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)) | No supported UCRT/redist path; needs app-local and EOL runtime | App-local UCRT + VC++ runtime required |
| Windows lifecycle | n/a | Windows 8: extended end **2016-01-13**; Windows 8.1: extended end **2023-01-10** ([Windows 8 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-8), [Windows 8.1 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-81)) | EOL since 2016 | EOL since 2023 |

The matrix is the whole answer: only the C++ layer still carries a Vista-era
compile target. The shipped Python, Go, Rust and Node runtimes do not officially
support Windows 8.1, and Node is only “experimental” there.

## 2. What PR #1005 actually enforces

Master still gates only on Vista (`installer/installer.nsi:184-188`):

```
${IfNot} ${AtLeastWinVista}
    MessageBox MB_ICONSTOP|MB_OK $(AtLeastWinVista_MESSAGE)
    Quit
${EndIf}
```

#1005 deletes that block and adds, after the existing `SetRegView 64` block
(PR head, `installer/installer.nsi:194-211`):

```
${IfNot} ${AtLeastWin8}
    MessageBox MB_ICONSTOP|MB_OK $(AtLeastWin10_MESSAGE)
    Quit
${EndIf}
ClearErrors
ReadRegDWORD $0 HKLM "SOFTWARE\Microsoft\Windows NT\CurrentVersion" "CurrentMajorVersionNumber"
${If} ${Errors}
${OrIf} $0 < 10
    MessageBox MB_ICONSTOP|MB_OK $(AtLeastWin10_MESSAGE)
    Quit
${EndIf}
```

The `${AtLeastWin8}` test is **not** a claim that Windows 8 is supported. It is
a cheap precondition: on Vista/7 it fails immediately, so the registry read is
not reached. Windows 8 and 8.1 pass it, then fail the real floor,
`CurrentMajorVersionNumber >= 10`. The PR makes the installer reject the same
systems the runtimes already reject, instead of installing a broken tree.

The two existing `${AtLeastWin8}` feature gates (the `cheeng` section at
`installer/installer.nsi:342` and `hideSection` at `:415`) are left alone and
are unrelated to the support floor.

### 2.1 NSIS macro correction

The PR body says “NSIS 3.08 WinVer.nsh has no `${AtLeastWin10}` test.” That is
false. The v3.08 header defines `WINVER_10` (`Include/WinVer.nsh:161`) and
generates `AtLeastWin10` through
`__WinVer_DefineOSTest` / `__WinVer_DefineOSTests AtLeast` at
`Include/WinVer.nsh:529-553`:
<https://github.com/nsis-dev/nsis/blob/v308/Include/WinVer.nsh>.

I verified this against the locally installed `makensis` 3.08
(`v3.08-3+deb12u1`) by compiling a minimal script containing
`${If} ${AtLeastWin8}`, `${If} ${AtLeastWin8.1}` and `${If} ${AtLeastWin10}`:
exit status 0. So the macro exists and compiles in exactly the NSIS version the
CI pins.

There is a real caveat, but it is different: `WinVer.nsh` warns that Windows
8.1 and later are detected as Windows 8 unless the executable manifest sets
`ManifestSupportedOS` correctly (`Include/WinVer.nsh:45`), and NSIS’s default
manifest is Win7+8+8.1+10 when `RequestExecutionLevel` is not `none`
([NSIS 4.8.1.31](https://nsis.sourceforge.io/Docs/Chapter4.html#amanifestsupportedos)).
`installer.nsi:62` uses `RequestExecutionLevel admin`, so the default manifest
applies. In other words, the PR’s registry check is **manifest-independent**,
which is a good property, but not for the reason stated in the PR body:
`AtLeastWin10` is not missing. The registry check is an alternative, not the
only available test.

The PR’s `AtLeastWin8` + registry shape is therefore correct in effect; the
comment and PR body should be reworded to say “we prefer a manifest-independent
check,” not “NSIS 3.08 has no `AtLeastWin10`.”

One residual risk: the check treats a missing `CurrentMajorVersionNumber` as
unsupported. That value is present on Windows 10/11, but this note did not test
every Windows 10 release (notably 1507/1511). `[INFERENCE]` It is present on
current Windows 10 builds, but this should be confirmed on the oldest Windows
10 build the project intends to accept before merging.

## 3. CRT/UCRT/VC++ dependency truth

The #1005 comment says “Since Windows 10, ucrtbase.dll and vcruntime140.dll
ship in-box” (`installer/installer.nsi:194-195` at PR head). The first half is
right; the second half is wrong.

- **UCRT is in-box on Windows 10+.** Microsoft: “The Universal CRT (UCRT) is a
  Microsoft Windows operating system component. It’s included as part of the
  operating system in Windows 10 or later, and Windows Server 2016 or later.”
  Older systems get it through Windows Update (initial KB2999226) or by
  app-local deployment
  ([UCRT deployment](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-170)).
- **`vcruntime140.dll` is not an OS component on any Windows release.** It is
  the Visual C++ runtime DLL. Microsoft’s “Determine which DLLs to
  redistribute” page separates the UCRT (a system component on Windows 10+)
  from `vcruntime[version].dll` (a redistributable DLL for native startup and
  termination), and says deployment to earlier systems may require
  redistributing the UCRT
  ([Microsoft docs](https://learn.microsoft.com/en-us/cpp/windows/determining-which-dlls-to-redistribute?view=msvc-170)).
  The latest v14 redistributable explicitly supports only Windows 10/11 and
  Server 2016+
  ([latest VC++ redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)).

PIME’s current payload happens not to need a system-wide `vcruntime140.dll`, for
four separate reasons:

1. **The launcher is static since #975.** `PIMELauncher/CMakeLists.txt:3-5`
   adds `-Ctarget-feature=+crt-static`, and CI rejects a launcher that imports
   `VCRUNTIME140` or `MSVCP140`
   (`.github/workflows/build-and-sign.yaml:94-110`).
2. **PIMETextService/libIME2 are `/MT`.** `CMakeLists.txt:6-7` sets
   `CMAKE_MSVC_RUNTIME_LIBRARY` to `MultiThreaded…` for all targets.
3. **The Python embed carries its own `vcruntime140.dll`.**
   `python/python3/vcruntime140.dll` is tracked, and the Python 3.12.9
   embeddable ZIP was also checked and contains `vcruntime140.dll`. Python’s
   own embedded-distribution docs put the Microsoft C runtime responsibility on
   the application installer, even though the 3.12 ZIP includes the vcruntime
   ([Python 3.12 docs](https://docs.python.org/3.12/using/windows.html)).
4. **The remaining dynamic import is covered by the Python directory.**
   `python/libchewing/chewing.dll` imports `VCRUNTIME140.dll` and the UCRT API
   sets (verified with `objdump -p`). When `python.exe` loads it,
   `$INSTDIR\python\python3` is the executable directory on the DLL search
   path, so the Python-bundled `vcruntime140.dll` satisfies it. This is not a
   system-runtime guarantee; it is a payload-local one
   ([Windows DLL search order](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order)).

`node/node.exe` imports neither `VCRUNTIME140.dll` nor the UCRT API sets
(`objdump -p`), and #976 removed `ensureVCRedist`, its download macro, and
`installer/inetc` entirely. So the accurate installer comment is:

> Windows 10 provides the UCRT in-box. PIME does not ship a VC++ redistributable:
> the launcher and C++ DLLs are statically linked, and the Python embed carries
> its own vcruntime140.dll. Windows 8.1 would need an app-local UCRT (and the
> Python/VC++ runtime) instead.

That correction matters for the 8.1 option: on 8.1, `ucrtbase.dll` and the
`api-ms-win-crt-*.dll` forwarders are not guaranteed to be present. Microsoft
supports app-local deployment but recommends against it; the safe layout is to
put the DLL set beside the main executable
([UCRT deployment](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-170)).
For PIME that means `$INSTDIR\python\python3`; the TSF DLLs do not need it
because they are `/MT`.

## 4. Windows 8.1 legacy build option

This is a sketch of the **minimum** work, not a supported plan. Everything in
this section is untested on Windows 8.1.

### 4.1 Installer

- Replace the #1005 Windows 10 registry gate with an 8.1-accepting gate. NSIS
  3.08 has both `${AtLeastWin8}` and `${AtLeastWin8.1}`; either can be used.
  If 8.0 is deliberately excluded, `${AtLeastWin8.1}` is the cleaner
  precondition. Keep the existing `cheeng` and `hideSection` gates.
- Do **not** ship one installer that accepts 8.1 and 10 but silently installs
  the wrong Python. A legacy build needs a separate artifact, version suffix,
  and release note, because the payload differs.

### 4.2 Python 3.12.x

- Downgrade the embeddable runtime from 3.15.1 to a 3.12.x release. Python 3.12
  docs say “Python 3.12 supports Windows 8.1 and newer”; Python 3.15 says
  “Windows 10 and newer” and explicitly points 8.1 users at 3.12
  ([3.15 docs](https://docs.python.org/3.15/using/windows.html),
  [3.12 docs](https://docs.python.org/3.12/using/windows.html)).
- Keep the embeddable ZIP layout (`python312.dll`, `python.exe`,
  `vcruntime140.dll`) and the current `python/python3` directory, so the
  launcher and installer paths do not change.
- Verify the current Python backend on 3.12. A targeted scan found no
  3.13+/3.14+-only syntax in `python/` or `tests/`, but the suite was not run
  under 3.12. `[INFERENCE]` Most of the code is plain 3.x, but this is
  unproven.
- Python 3.12 is in security-only status: source-only fixes until October 2028
  ([PEP 693](https://peps.python.org/pep-0693/)). Plan to build or vendor a fixed
  interpreter yourself if a CVE lands after the last binary release.

### 4.3 Go 1.20

- Change `go-backend/go.mod:3` from `go 1.21` to `go 1.20` and build with Go
  1.20. Go 1.20 is the last release that runs on Windows 8/8.1; Go 1.21
  requires Windows 10/Server 2016
  ([Go 1.20 notes](https://go.dev/doc/go1.20),
  [Go 1.21 notes](https://go.dev/doc/go1.21)).
- A quick source scan found no obvious Go 1.21-only features (`min`/`max`/
  `clear`, `slices`, `maps`, `log/slog`), so the code is a plausible build.
  But the directive itself blocks Go 1.20, and no Go 1.20 build was run.
- Go 1.20 is unsupported: each Go release is supported only until two newer
  majors exist
  ([Go release policy](https://go.dev/doc/devel/release#policy)), so 1.20 has
  been out of support since Go 1.22 shipped.

### 4.4 Rust: 1.77 with a re-pinned lock, or replace the launcher

Rust 1.77 is the last toolchain whose platform-support page says the MSVC
targets support Windows 7+; 1.78 changes the same entries to Windows 10+
([1.77](https://doc.rust-lang.org/1.77.0/rustc/platform-support.html),
[1.78](https://doc.rust-lang.org/1.78.0/rustc/platform-support.html)).

The current lock is not 1.77-compatible on its face:

- `uuid 1.23.1` (`PIMELauncher/Cargo.lock:612-613`) declares
  `rust-version = 1.85.0` on crates.io
  ([uuid 1.23.1](https://crates.io/crates/uuid/1.23.1)).
- `getrandom 0.4.2` (`Cargo.lock:152-153`) declares `rust-version = 1.85`
  ([getrandom 0.4.2](https://crates.io/crates/getrandom/0.4.2)).
- `indexmap 2.14.0` and `hashbrown 0.17.0` (`Cargo.lock:192-193,174-175`)
  declare 1.85, and several `wasm-*` crates declare 1.81+.

So a 1.77 build needs a regenerated or pinned lock, at minimum
[`uuid` 1.20.0](https://crates.io/crates/uuid/1.20.0) (MSRV 1.63) and
[`tempfile` 3.20.0](https://crates.io/crates/tempfile/3.20.0) (which uses
`getrandom 0.3` rather than 0.4). `PIMELauncher/Cargo.toml:14` currently allows any `uuid 1.x`
and `:24` any `tempfile 3.x`, so the resolver will otherwise pick the new
MSRVs. This is a real, concrete downgrade cost, not just “install an old
toolchain.”

Alternative: replace the Rust launcher with a small C++/Win32 launcher built
`/MT` with the same static CRT policy. That removes the Rust toolchain and
dependency-pinning problem entirely, but it is a rewrite of
`PIMELauncher/src` and its tests, not a build-flag change.

### 4.5 Node: best-effort or drop

Node 22.23.4 is the newest 32-bit runtime line and is supported upstream until
2027-04-30
([Node release schedule](https://raw.githubusercontent.com/nodejs/Release/main/schedule.json)),
but its own BUILDING table lists Windows 8.1/Server 2012 as **Experimental**,
not Tier 1; the supported floor is Windows 10/Server 2016
([v22.23.4 BUILDING.md](https://github.com/nodejs/node/blob/v22.23.4/BUILDING.md)).
For an 8.1 legacy build, either:

- ship Node 22.23.4 as best-effort and accept that the Node-only IMs
  (`McBopomofo`, `McFoxim`, `McTabim`, `emojime`) may fail, or
- drop the Node backend/sections from the legacy installer.

Do not describe the Node backend as supported on 8.1.

### 4.6 C++ and the toolset

- Keep `_WIN32_WINNT=0x0600` and `/MT`. The TSF API is documented as XP-or-later,
  and the build target is Vista, so there is no source-level Windows 10
  dependency in the code this note inspected. A repo-wide search found no
  `IsWindows10OrGreater`, `SetProcessDpiAwarenessContext`, `GetDpiForWindow`,
  `PathCch*`, `RoInitialize`, or `WIN32_WINNT >= 0x0A00` use in the C++ tree.
- The current build uses Visual Studio 18 2026 (`build.bat:1`) and Windows
  Server 2025 CI (`.github/workflows/build-and-sign.yaml:22`). Static linking
  avoids a redistributable, but it does **not** prove that the VS2026 static CRT
  avoids Windows 10-only APIs or that the toolset still targets 8.1. A legacy
  build should use an older toolset known to target 8.1, or the project must
  accept an unvalidated toolchain. `[INFERENCE]` This is the largest unknown
  after Python/Go/Rust.
- Windows 8.1 has no ARM64 edition. A legacy build only needs x86 and x64; the
  ARM64 installer branches can be omitted or left unreachable.

### 4.7 UCRT/VC++ deployment

- Bundle the UCRT DLL set (`ucrtbase.dll` plus `api-ms-win-crt-*.dll`) in
  `$INSTDIR\python\python3`, beside `python.exe`. Microsoft supports local
  deployment, but not for Windows 10 (the system copy wins) and it must be in
  the main executable’s directory
  ([UCRT deployment](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-170)).
- Keep `vcruntime140.dll` next to `python.exe` (the 3.12 embed already contains
  it). `chewing.dll`’s `VCRUNTIME140.dll` import resolves through the
  executable directory, as it does today.
- Alternatively, install a pinned older v14 redistributable whose documented
  support list still includes 8.1, offline. The **latest** v14 package does not:
  Microsoft says the VS2026 v14 redistributable supports only Windows 10/11 and
  Server 2016+
  ([latest VC++ redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)).
  Using an older redist is another EOL dependency to pin and audit.
- Windows Update is not a reliable delivery path for an EOL OS. Treat this as
  “ship the DLLs” or “ship the offline MSU,” not “the user probably has it.”

### 4.8 Clean-VM and CI cost

There is no Windows 8.1 GitHub-hosted runner. CI is `windows-2025`
(`.github/workflows/build-and-sign.yaml:22`) and AppVeyor uses the Visual Studio
2026 image (`appveyor.yml:6`). A legacy build therefore needs either a
self-hosted 8.1 VM or a manual test pass for every release. The minimum matrix:

1. clean 8.1 x86 and x64 installs (no Python/Node/VC++ preinstalled);
2. TSF registration and activation in a 32-bit and 64-bit TSF client;
3. Python backend, Node backend (if kept), Go backend, and chewing/rime DLL
   loading;
4. uninstall/upgrade, including the “files in use” reboot path;
5. re-run after every runtime or dependency update.

That is a permanent second platform, not a one-line gate. Add VM licensing,
snapshot maintenance, and the inability to reproduce CI failures on a hosted
runner.

### 4.9 Security/EOL cost

Windows 8.1 stopped receiving security updates in January 2023; Windows 8
support ended in January 2016. A legacy installer would be advertising an OS that no longer
gets platform fixes. Python 3.12 is security-only, Go 1.20 is out of support,
Rust 1.77 is an old toolchain, and Node 22 is only experimental on 8.1. The
honest label is “unsupported legacy build, no security guarantees,” and the
release notes must say so. That is a product/security decision, not just a
build-matrix cost.

## 5. Windows 8.0 is a separate, worse case

Do not fold 8.0 into the 8.1 discussion.

- Windows 8 support ended in January 2016 (extended end 2016-01-13); it is not
  a supported platform today
  ([Windows 8 lifecycle](https://learn.microsoft.com/en-us/lifecycle/products/windows-8)).
- Python 3.12 requires Windows 8.1 or newer. Python 3.8 is the last release that
  supports Vista-or-newer and would run on 8.0, but 3.8 reached EOL in October
  2024
  ([Python 3.8 docs](https://docs.python.org/3.8/using/windows.html),
  [PEP 569](https://peps.python.org/pep-0569/)).
- Go 1.20 runs on 8.0, but it is EOL; Go 1.21+ requires Windows 10.
- Node 22’s support table has no Windows 8.0 row at all; only 8.1 is listed as
  experimental.
- Rust 1.77’s target support says Windows 7+, so a launcher could theoretically
  run, but that does not make the Python/Node/Go stack viable.

A Windows 8.0 build would require Python 3.8, Go 1.20, an old Node (if any), and
Rust 1.77 — four EOL runtimes on an OS that has been unpatched since 2016. It is
not a supportable product.

## 6. What #1005 should do before merge

The gate itself is sound. Recommended non-code cleanup:

1. Reword the installer comment and PR body: UCRT is in-box on Windows 10;
   `vcruntime140.dll` is not. The launcher/C++ are static, and the Python embed
   carries vcruntime.
2. Remove “NSIS 3.08 has no `${AtLeastWin10}`”; it does. Say the registry check
   was chosen to be manifest-independent, or simplify to
   `${IfNot} ${AtLeastWin10}` if that is acceptable.
3. Keep the `${AtLeastWin8}` precondition only if the manifest-independent
   registry check is retained. It is not a Win8 support claim.
4. If the registry check is kept, verify `CurrentMajorVersionNumber` on the
   oldest Windows 10 build the project accepts, and state that a missing value
   is treated as unsupported.

No code change is required to keep Windows 8/8.1 out. The only code change
worth considering is replacing the two-step gate with `${AtLeastWin10}` after
confirming the manifest behavior; that is a simplification, not a support
change.

## 7. Stale documentation found

`HACKING.txt:90` still says the embedded runtime is “python 3.12 32-bit
(`python312.dll`).” The checkout actually carries Python 3.15.1
(`python/python3/python315.dll`; bump commit `eda0bc8`; also
`docs/agents/verification.md:45`). This note does not fix it, because the task
scope is this research file only, but it should be corrected separately. The
same section’s Node description does not pin a version; `docs/agents/verification.md:81`
records 22.23.4.

## 8. Remaining uncertainty

- **No clean Windows 8.1 VM test.** Nothing in this note was installed,
  registered, or launched on 8.1. All 8.1 behavior is inference from version
  support tables and binary imports.
- **No older-runtime build of the current code.** Python 3.12 was not used to
  run `tests/`; Go 1.20 was not used to build `go-backend`; Rust 1.77 was not
  used to build `PIMELauncher`; VS2026 was not checked for 8.1-targeted output.
- **`CurrentMajorVersionNumber` on old Windows 10 builds.** The #1005 gate
  rejects a missing value; the oldest Windows 10 build that writes it was not
  tested here.
- **App-local UCRT layout.** Microsoft documents the restrictions, but the
  exact DLL set for Python 3.12 + `chewing.dll` on 8.1 was not assembled or
  tested.
- **Latest MSVC static CRT.** Static linking avoids `vcruntime140.dll`, but it
  does not prove the VS2026 CRT avoids Windows 10-only API calls. A real 8.1
  smoke test (or an import/API audit with an older toolset) is still required.
- **Node on 8.1.** Upstream calls it experimental; no run was attempted.
- **No proof that Python 3.12 passes the current tests.** A syntax/feature scan
  is not a test run.

## 9. Sources consulted

Primary sources:

- Python 3.15 Windows support:
  <https://docs.python.org/3.15/using/windows.html>
- Python 3.12 Windows support and embedded distribution:
  <https://docs.python.org/3.12/using/windows.html>
- Python 3.8 Windows support:
  <https://docs.python.org/3.8/using/windows.html>
- Python 3.12 support window (PEP 693):
  <https://peps.python.org/pep-0693/>
- Node.js v22.23.4 platform support:
  <https://github.com/nodejs/node/blob/v22.23.4/BUILDING.md>
- Node.js release schedule:
  <https://raw.githubusercontent.com/nodejs/Release/main/schedule.json>
- Go 1.21 release notes:
  <https://go.dev/doc/go1.21>
- Go 1.20 release notes:
  <https://go.dev/doc/go1.20>
- Go release policy:
  <https://go.dev/doc/devel/release#policy>
- Rust 1.77 platform support:
  <https://doc.rust-lang.org/1.77.0/rustc/platform-support.html>
- Rust 1.78 platform support:
  <https://doc.rust-lang.org/1.78.0/rustc/platform-support.html>
- TSF overview:
  <https://learn.microsoft.com/en-us/windows/win32/tsf/text-services-framework>
- Windows version numbers:
  <https://learn.microsoft.com/en-us/windows/win32/sysinfo/operating-system-version>
- Universal CRT deployment:
  <https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-170>
- Determine which VC++ DLLs to redistribute:
  <https://learn.microsoft.com/en-us/cpp/windows/determining-which-dlls-to-redistribute?view=msvc-170>
- Latest supported VC++ redistributable:
  <https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170>
- Windows 8 lifecycle:
  <https://learn.microsoft.com/en-us/lifecycle/products/windows-8>
- Windows 8.1 lifecycle:
  <https://learn.microsoft.com/en-us/lifecycle/products/windows-81>
- NSIS 3.08 `WinVer.nsh`:
  <https://github.com/nsis-dev/nsis/blob/v308/Include/WinVer.nsh>
- NSIS `ManifestSupportedOS`:
  <https://nsis.sourceforge.io/Docs/Chapter4.html#amanifestsupportedos>

Repository evidence:

- `installer/installer.nsi:184-188` — master’s Vista gate.
- `installer/installer.nsi:194-211` at PR #1005 head — Windows 10 gate.
- `installer/installer.nsi:255,470,489` — launcher installed and launched.
- `installer/installer.nsi:342,415` — existing `AtLeastWin8` feature gates.
- `PIMELauncher/CMakeLists.txt:3-5` — static Rust CRT.
- `CMakeLists.txt:6-7,26` — `/MT` and `_WIN32_WINNT=0x0600`.
- `PIMETextService/CMakeLists.txt:7` — C++17.
- `.github/workflows/build-and-sign.yaml:22` — `windows-2025`.
- `.github/workflows/build-and-sign.yaml:39-43` — stable Rust and
  `i686-pc-windows-msvc`.
- `.github/workflows/build-and-sign.yaml:83-86` — NSIS 3.08.
- `.github/workflows/build-and-sign.yaml:94-110` — launcher CRT import gate.
- `appveyor.yml:6,13-14` — Visual Studio 2026 image and stable Rust MSVC target.
- `build.bat:1` — Visual Studio 18 2026.
- `go-backend/go.mod:3` — `go 1.21`.
- `PIMELauncher/Cargo.lock:152-153,174-175,192-193,612-613` — locked
  `getrandom 0.4.2`, `hashbrown 0.17.0`, `indexmap 2.14.0`, `uuid 1.23.1`.
- `python/python3/vcruntime140.dll`, `python/python3/python315.dll` — current
  embedded payload.
- `python/libchewing/chewing.dll`, `python/input_methods/rime/rime.dll`,
  `python/opencc/opencc.dll` — import tables checked with `objdump -p`.
- `docs/agents/verification.md:45,81` — bundled Python 3.15.1 and Node 22.23.4.
- `HACKING.txt:90` — stale Python 3.12 claim.

Commands actually run:

```
gh pr view 1005 --repo EasyIME/PIME --json ...
gh pr diff 1005 --repo EasyIME/PIME
git show 31b732d69fe415737738d591155b1cf0ab947ac8:installer/installer.nsi
git diff 2439db0a6df49c4735a6e5f65e8522aa46165446^1 2439db0a6df49c4735a6e5f65e8522aa46165446
git show 3dbea11097370b5fc0170b28404d2311b552ba09 -- installer/installer.nsi
objdump -p python/python3/python.exe
objdump -p python/python3/python315.dll
objdump -p python/libchewing/chewing.dll
objdump -p python/input_methods/rime/rime.dll
objdump -p python/opencc/opencc.dll
objdump -p node/node.exe
makensis -V2 /tmp/winver-test.nsi   # NSIS 3.08; AtLeastWin8/8.1/10 all compile
curl https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-win32.zip
```

No MSVC build, no Rust 1.77 build, no Python 3.12 test run, and no Windows 8.1
VM were available; those are listed as uncertainty above, not observed results.
