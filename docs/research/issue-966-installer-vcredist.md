# Installer VC++ redistributable check (#966): removal analysis

Reference tree: `origin/master` at `15863744fca71874788939bb3a5d9cdb80509ca3`
(2026-10-19, merge of #970). Line references below are to that SHA. The local
checkout (`fa055ef`) diverges from `origin/master` in CI/tests/docs, but
`git diff HEAD origin/master -- installer python CMakeLists.txt build.bat
PIMELauncher/CMakeLists.txt PIMELauncher/Cargo.toml` is empty, so the installer
and build files cited here are identical in both trees. The issue is
[EasyIME/PIME#966](https://github.com/EasyIME/PIME/issues/966) (PCMan,
2026-10-18, open).

What was executed:

- PE import tables for all 37 tracked `.exe`/`.dll`/`.pyd` files outside the
  NSIS plugin directories, plus the five binaries in the `unsigned-binaries`
  artifact of CI run
  [39360542686](https://github.com/EasyIME/PIME/actions/runs/39360542686)
  (`head_sha` = `15863744…`). Imports were read with a small PE32/PE32+
  `DataDirectory[1]` parser (machine type + import DLL names). x86/x64 results
  were cross-checked with `objdump -p <pe> | awk '/DLL Name/{print $3}'`;
  binutils in this sandbox cannot parse ARM64 import tables, so the ARM64
  results are parser-only.
- `curl https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-win32.zip`
  and a ZIP listing/hash comparison against `python/python3/vcruntime140.dll`.
- `gh api` for the issue body, the CI run, and the libchewing source at its
  pinned SHA (`452f622…`).

What was not executed, and why: `makensis` (needs Windows plugins; the local
note `docs/agents/verification.md:98-102` records that the NSIS compile is
CI-only), any MSVC/Rust build (Linux host), and a clean Windows VM. Anything
that depends on those is marked `[INFERENCE]`.

## TL;DR

- **The literal patch in the issue is a NO-GO.** Removing the check alone
  leaves `PIMELauncher.exe` with an unsatisfied static import of
  `VCRUNTIME140.dll`. The launcher is installed unconditionally
  (`installer/installer.nsi:302-303`) and launched at install time
  (`:533-534`) and at every logon (`:514-515`). The `vcruntime140.dll` in the
  Python package (`python/python3/vcruntime140.dll`) sits in
  `$INSTDIR\python\python3`, which is not on the launcher's DLL search path;
  the installer never adds it to `PATH`.
- The CI-built launcher from the current tree imports `VCRUNTIME140.dll`
  (verified). The other core binaries are self-sufficient:
  `PIMETextService.dll` (x86/x64/ARM64) imports no CRT at all;
  `python/*`, `node.exe`, `opencc.dll` and `rime.dll` either carry the runtime
  locally or import none. No shipped binary imports `msvcp140.dll` or
  `vcruntime140_1.dll`.
- **GO, if bundled with a one-line launcher build fix**:
  `corrosion_add_target_rustflags(PIMELauncher "-Ctarget-feature=+crt-static")`
  in `PIMELauncher/CMakeLists.txt`, then the 92-line deletion in the issue.
  With that flag the launcher needs only in-box Windows 10 components, and
  `inetc` becomes entirely dead.
- The issue's premise is partly wrong: `libchewing`'s shipped `chewing.dll`
  is dynamically linked to `VCRUNTIME140.dll` (not `/MT`), and
  `PIMELauncher.exe` is a Rust binary using the MSVC runtime dynamically
  (Rust's default). Only `PIMETextService.dll`/`libIME2` are `/MT`.
- `installer/inetc` has no other caller after the macro is removed and can be
  deleted with its `!addplugindir` line (39 files, 215 KiB in git). Keeping it
  is not justified by StdUtils (separate plugin directory) or any build script.
- The installer does **not** enforce the issue's "Windows 10 minimum": it only
  rejects pre-Vista (`installer/installer.nsi:188-192`). Removing the UCRT
  check without gating Windows 10 would let 8.1 installs succeed and then fail
  at Python startup. An optional companion change is listed in §6.4.

## 1. What the code does today

### 1.1 The check and the macro

`ensureVCRedist` (`installer/installer.nsi:238-277`) runs at the top of the
main section (`:284-288`):

```
238 Function ensureVCRedist
239 ; TODO(#966): This check is an obsolete relic from Windows 7 / 8.1.
...
246 ${IfNot} ${FileExists} "$SYSDIR\ucrtbase.dll"
247 ${OrIfNot} ${FileExists} "$SYSDIR\msvcp140.dll"
248     ${If} ${RunningX64}
...
259         ${IfNot} ${FileExists} "$SYSDIR\ucrtbase.dll"
260         ${OrIfNot} ${FileExists} "$SYSDIR\msvcp140.dll"
261             !insertmacro DownloadAndInstallVCRedist "https://aka.ms/vs/17/release/vc_redist.x64.exe" "vc_redist.x64.exe"
...
265     ${ElseIf} ${IsNativeARM64}
...
269             !insertmacro DownloadAndInstallVCRedist "https://aka.ms/vs/17/release/vc_redist.arm64.exe" "vc_redist.arm64.exe"
...
273     ${Else}
274         !insertmacro DownloadAndInstallVCRedist "https://aka.ms/vs/17/release/vc_redist.x86.exe" "vc_redist.x86.exe"
275     ${EndIf}
276 ${EndIf}
277 FunctionEnd
```

The macro (`installer/macros.nsh:258-297`) prompts, downloads with
`inetc::get` to `$TEMP`, runs the redist with `/quiet /norestart`, then checks
`$SYSDIR` again:

```
276 MessageBox MB_YESNO|MB_ICONQUESTION $(DOWNLOAD_VCREDIST_QUESTION) IDYES +2
277 Abort
278 inetc::get "${URL}" "$TEMP\${EXE_NAME}"
279 Pop $2
280 IntCmp $2 0 +2
281 MessageBox MB_ICONSTOP|MB_OK $(DOWNLOAD_VCREDIST_FAILED_MESSAGE)
282 Abort
283
284 ExecWait '"$TEMP\${EXE_NAME}" /quiet /norestart' $2
285 ${IfNot} ${FileExists} "$SYSDIR\ucrtbase.dll"
286 ${OrIfNot} ${FileExists} "$SYSDIR\msvcp140.dll"
287 MessageBox MB_ICONSTOP|MB_OK $(INST_VCREDIST_FAILED_MESSAGE)
288 Abort
```

The three localization keys are the only users of those strings:
`installer/locale/English.nsh:19-21`, `SimpChinese.nsh:19-21`,
`TradChinese.nsh:19-21`.

### 1.2 When it runs

`.onInit` calls `uninstallOldVersion` (`installer/installer.nsi:220-221`)
before the main section runs. That function removes the old payload —
unregisters the TSF DLLs, kills the launcher, deletes `python`/`node`, removes
the Run key and the uninstaller (`:117-165`). Only after that does section
`SecMain` call `ensureVCRedist` (`:288`). The installer is started elevated;
the downloaded `vc_redist.*.exe` is executed elevated.

### 1.3 Failure path

On a clean offline machine, `inetc::get` fails, `$2 != 0`, the
`DOWNLOAD_VCREDIST_FAILED_MESSAGE` box appears, and `Abort` ends the
installation. `Abort` from a section invokes `.onInstFailed`
(`installer/installer.nsi:225-236`), which shows
`INST_FAILED_MESSAGE` (`:233`) and aborts again. Because the old-version
removal already ran, an offline **upgrade** ends with the old PIME removed and
the new one not installed.

`MessageBox` at `macros.nsh:276` has no `/SD`, so it is shown even in a silent
install: NSIS's `my_MessageBox` only auto-answers when the type carries a
silent default (`Source/exehead/util.c:126-150` in
[NSIS v3.08](https://github.com/kichik/nsis/blob/v308/Source/exehead/util.c)).
An unattended `/S` install on a clean offline machine therefore blocks on a
dialog; after removal it completes. That is the behavior change the issue is
after.

## 2. Deletion surface

At `1586374`, the complete VCRedist inventory is:

| Location | Use |
| --- | --- |
| `installer/installer.nsi:238-277` | `Function ensureVCRedist` (40 lines) |
| `installer/installer.nsi:286-288` | TODO comment + `Call ensureVCRedist` (3 lines) |
| `installer/macros.nsh:258-297` | macro banner + `DownloadAndInstallVCRedist` (40 lines) |
| `installer/locale/English.nsh:19-21` | `DOWNLOAD_VCREDIST_*`, `INST_VCREDIST_*` (3 lines) |
| `installer/locale/SimpChinese.nsh:19-21` | same (3 lines) |
| `installer/locale/TradChinese.nsh:19-21` | same (3 lines) |
| `installer/installer.nsi:37-39` | `inetc` comment + `!addplugindir` (3 lines) |
| `installer/inetc/**` | vendored plugin, 39 files, 215 KiB stored / 360 KiB on disk |

`git grep -n 'inetc::'` finds exactly one call site: `macros.nsh:278`.
`git grep -n 'inetc'` outside `installer/inetc` and
`installer/StdUtils.2015-11-16` finds only `installer.nsi:37-39` and the macro
at `macros.nsh:262,278`. There is no `inetc` reference in `build.bat`,
`appveyor.yml`, `appveyor.after_build.bat`, `.github/workflows/*`, or
`installer/README.txt`; those scripts only invoke `makensis` on
`installer/installer.nsi` (`build-and-sign.yaml:106-109`,
`appveyor.after_build.bat:3`), and NSIS resolves plugin directories at compile
time.

`StdUtils` is independent: it has its own `!addplugindir`
(`installer.nsi:30-32`) and is used by `StdUtils.ExecShellAsUser`
(`installer.nsi:534`). Nothing else needs `inetc`.

The claim that an unused `!addplugindir` can be left behind as proof of
tolerance is already in the tree: `installer.nsi:34-35` adds
`md5dll\UNICODE`, but `installer/md5dll` does not exist and no `md5dll::`
command remains. The installer from the exact `1586374` tree compiled
successfully in CI run
[39360542686](https://github.com/EasyIME/PIME/actions/runs/39360542686), so
makensis does not fail on that dangling path when no command uses it. Removing
the `inetc` line is still correct for hygiene; deleting the folder without the
line would leave a dead path.

**Recommendation:** delete `installer/inetc/**` and `installer/installer.nsi:37-39`;
update the local note `docs/agents/verification.md:100-102`, which currently
says the Linux makensis step fails because both `inetc` and `StdUtils` are
missing. After the deletion only `StdUtils` is missing, and the note should say
so.

## 3. CRT dependency truth

### 3.1 Method

The PE parser read the import directory of every tracked PE outside the NSIS
plugin directories (37 files), plus the five CI artifacts. The relevant
question is whether any shipped binary has an unsatisfied import on a clean
Windows 10 image: `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll`, `MSVCP140.dll`,
or the in-box UCRT API sets (`api-ms-win-crt-*` / `ucrtbase.dll`).

Result: **no tracked or CI-built binary imports `msvcp140.dll` or
`vcruntime140_1.dll`.** 31 of the 37 tracked PEs import `VCRUNTIME140.dll`,
but every one of them is under `python/` (the bundled CPython distribution);
`python/python3/vcruntime140.dll` is shipped beside them.

### 3.2 Shipped payload

| Binary | Arch | CRT imports | Satisfied on clean Win10? |
| --- | --- | --- | --- |
| `python/python3/python.exe`, `pythonw.exe` | x86 | `VCRUNTIME140`, UCRT API sets | yes: local `vcruntime140.dll`; UCRT in-box |
| `python/python3/python312.dll` | x86 | `VCRUNTIME140`, UCRT API sets | yes: same |
| `python/python3/python3.dll` | x86 | none (forwarder) | yes |
| `python/python3/vcruntime140.dll` | x86 | UCRT API sets | yes; real runtime 14.42.34226.3 |
| `python/python3/{sqlite3,libcrypto-3,libssl-3,libffi-8}.dll`, `*.pyd` | x86 | `VCRUNTIME140`, UCRT API sets | yes: loaded by `python.exe` |
| `python/libchewing/chewing.dll` | x86 | `VCRUNTIME140`, UCRT API sets | yes **only** because `python.exe` already loaded the runtime |
| `python/opencc/opencc.dll` | x86 | none (`KERNEL32` only) | yes |
| `python/input_methods/rime/rime.dll` | x86 | none (`KERNEL32`, `ADVAPI32`, `USER32`) | yes |
| `node/node.exe` | x86 | none | yes |
| `PIMETextService.dll` (x86, x64) | x86/x64 | none | yes |
| `PIMETextService.dll` (ARM64X forwarder) | ARM64 | none | yes |
| `PIMETextService_arm64.dll` | ARM64 | none | yes |
| `PIMELauncher.exe` | x86 | **`VCRUNTIME140`**, UCRT API sets | **no** unless the runtime is installed or shipped |
| NSIS `INetC.dll` / `StdUtils.dll` (build-time only) | x86 | `KERNEL32/USER32/WININET/COMCTL32`; `MSVCRT/SHLWAPI/...` | irrelevant: compiled into the setup EXE, not installed to `$INSTDIR` |

The ARM64X `PIMETextService.dll` has zero imports; its
`PIMETextService_arm64.dll` imports only Win32 DLLs. The x86/x64
`PIMETextService.dll` import lists contain no CRT DLL, which confirms the
`/MT` setting for that target.

`chewing.dll` contradicts reason 2 of the issue: it imports
`VCRUNTIME140.dll` and the UCRT API sets, i.e. it is a dynamic-CRT build. It
still loads because the Python interpreter that loads it
(`python/libchewing/libchewing.py:26-29`, a full-path `CDLL`) has already
loaded `vcruntime140.dll`; the Windows loader checks the loaded-module list by
module name before any search path ([DLL search
order](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order),
step 4). That is `[INFERENCE]` from the loader contract, not something observed
in a process here. It is not a dependency the installer check was providing.

### 3.3 CI-built binaries

The `unsigned-binaries` artifact from run `39360542686` (head SHA `1586374`)
contains the exact files uploaded by `build-and-sign.yaml:63-73`. Import
results:

- `build/PIMELauncher/PIMELauncher.exe` (x86): `VCRUNTIME140.dll` plus
  `api-ms-win-crt-*`, `bcryptprimitives`, `kernel32`, `advapi32`, `ntdll`,
  `oleaut32`. No `MSVCP140`, no `VCRUNTIME140_1`.
- `build/PIMETextService/Release/PIMETextService.dll` (x86): no CRT imports.
- `build64/.../PIMETextService.dll` (x64): no CRT imports.
- `build_arm64/.../PIMETextService.dll` (ARM64X): zero imports.
- `build_arm64/.../PIMETextService_arm64.dll`: no CRT imports.

The launcher is the only shipped binary whose CRT import is not satisfied by
the `python\python3` copy. It is also the only Rust-produced binary in the
payload.

### 3.4 Which build flag decides each binary

- Root `CMakeLists.txt:3-7` sets
  `CMAKE_MSVC_RUNTIME_LIBRARY` to
  `MultiThreaded$<$<CONFIG:Debug>:Debug>` before `project(PIME)` (`:9`) and
  before `add_subdirectory(libIME2)` (`:29`) and
  `add_subdirectory(PIMETextService)` (`:31`).
  [`libIME2/CMakeLists.txt`](https://github.com/EasyIME/libIME2/blob/78e61045956960a511f85eb823e0fd65fa8c94b9/CMakeLists.txt)
  and `libIME2/src/CMakeLists.txt` at the pinned `78e6104` do not set it (the
  only related setting is `gtest_force_shared_crt` for googletest,
  `libIME2/CMakeLists.txt:13`). So the static library and the text service
  inherit `/MT`, matching the import tables.
- `PIMELauncher` is not covered by that variable. It is built by Corrosion
  from `PIMELauncher/Cargo.toml`; `PIMELauncher/CMakeLists.txt:1` only imports
  the crate, and `.cargo/config.toml` sets the `i686-pc-windows-msvc` target.
  Rust's default is a dynamically linked C runtime: "All targets in the
  compiler have a default mode of linking to the C runtime. Typically targets
  are linked dynamically by default" ([Rust Reference, linkage and
  crt-static](https://doc.rust-lang.org/reference/linkage.html)). The CI
  import table confirms the result.
- `libchewing` is a submodule at `452f622`, but PIME never adds it as a CMake
  subdirectory: `build.bat:1-14` builds only the root project, and
  `CMakeLists.txt` has no `libchewing` reference. Its top-level
  [`CMakeLists.txt`](https://github.com/chewing/libchewing/blob/452f6221fbad90c0706a3963b17e226216e40dd7/CMakeLists.txt)
  at that SHA sets no `MSVC_RUNTIME_LIBRARY` (only
  `_CRT_SECURE_NO_WARNINGS`, line 47), so even a local build would use the
  toolset default, not PIME's `/MT`. The shipped `python/libchewing/chewing.dll`
  is a checked-in prebuilt binary (last touched by `9a0ca83`, 2021), and its
  dynamic imports match that.
- `python/*`, `node.exe`, `opencc.dll`, `rime.dll` are vendored upstream
  binaries; their imports are fixed by their own builds. The Python files are
  byte-identical to the official 3.12.9 win32 embeddable ZIP (see §4.3).

## 4. OS guarantee

### 4.1 UCRT is in-box on Windows 10

Microsoft: "The Universal CRT (UCRT) is a Microsoft Windows operating system
component. It's included as part of the operating system in Windows 10 or
later, and Windows Server 2016 or later. The UCRT is available by using Windows
Update on older operating systems that are still in extended support."
([Universal CRT
deployment](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-170)).
The same page says that on Windows 10/11 the system copy "is always used, even
if an application includes an application-local copy", because it is a core
operating-system component.

So on a clean Windows 10 install — including offline — `ucrtbase.dll` and the
`api-ms-win-crt-*` API sets are present in the native system directory and in
the WOW64 directory (`SysWOW64` on x64/ARM64). The check's `ucrtbase.dll`
condition is therefore redundant for the supported OS.

N editions are not an exception: the Media Feature Pack list says N editions
are the same "except for media-related technologies, Windows Media Player, and
certain preinstalled media apps"
([Microsoft support](https://support.microsoft.com/en-us/windows/experience/platform-variants/media-feature-pack-list-for-windows-n-editions)).
The UCRT is not a media technology, so it remains in-box.

### 4.2 What the VC++ redistributable is for

`vcruntime140.dll` and `msvcp140.dll` are listed as *Redistributable* DLLs, not
OS components: "A Visual C++ Redistributable installs Microsoft C and C++
Runtime libraries… a Microsoft Visual C++ Redistributable package at least as
recent as the build tools used to build your app must be installed on the
target system along with the app"
([Latest supported VC++
Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)).
The deployment table distinguishes `vcruntime[version].dll` ("Runtime Library
for native code") and `msvcp[version].dll` ("C++ Standard Library for native
code") from the UCRT, and says the latter "is now a system component in
Windows 10 and later"
([Determine which DLLs to
redistribute](https://learn.microsoft.com/en-us/cpp/windows/determining-which-dlls-to-redistribute?view=msvc-170)).

The same page documents the package split that matters here:
"`vc_redist.x86.exe` installs the 32-bit libraries for both x86 and x64
computers, `vc_redist.x64.exe` installs the 64-bit libraries for x64
computers". The x64 package's notes also say it "contains both ARM64 and X64
binaries", which is why the existing ARM64 branch is unnecessary.

No Microsoft page states that `msvcp140.dll` or `vcruntime140.dll` is in-box on
Windows 10; the deployment model treats them as redistributable payload. A
clean Windows 10 image that never installed a VC++ redist therefore has
neither, which is `[INFERENCE]` from that deployment model (no VM was
available here).

### 4.3 Python 3.12 embeddable

The Python 3.12 docs say: "The embedded distribution does not include the
Microsoft C Runtime and it is the responsibility of the application installer
to provide this. The runtime may have already been installed on a user's
system previously or automatically via Windows Update, and can be detected by
finding ucrtbase.dll in the system directory."
([Using Python on Windows, 4.4 The embeddable
package](https://docs.python.org/3.12/using/windows.html#the-embeddable-package)).
That sentence is about the UCRT; on Windows 10 the installer's responsibility
is already discharged by the OS.

The issue's third premise is nevertheless true for the VC runtime: the
official `python-3.12.9-embed-win32.zip` contains `vcruntime140.dll`
(90,088 bytes). Executed check:

```
curl -sL -o py3129.zip https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-win32.zip
# zipfile listing: 34 entries; vcruntime140.dll = 90088 bytes; no msvcp140*.dll
sha256(zip member) = e72cb60bc3afaed6f38fa28d7111938067a9e4bed38a36f7a1ac6b9c1f16d0e2
sha256(python/python3/vcruntime140.dll) = e72cb60b…d0e2   # identical
```

So PIME's copy is upstream CPython's 32-bit runtime (file version
14.42.34226.3 in the PE version resource), not a hand-added DLL. It is still
only in the Python subdirectory, which is why it does not help
`PIMELauncher.exe`.

### 4.4 PIME does not enforce the Windows 10 floor

The issue says Windows 10 is the minimum, but the installer's only OS gate is
`${AtLeastWinVista}` (`installer/installer.nsi:188-192`), and the message
strings still say "Windows Vista or later" (`installer/locale/*.nsh:14`). The
README does not state a minimum either. Python 3.12 itself supports Windows
8.1 and newer
([same docs page, §4](https://docs.python.org/3.12/using/windows.html)), not
Windows 10 specifically.

Consequence: on Windows 8.1, after this removal, the installer would succeed
but the UCRT would not be present unless KB2999226 or a VC++ redist had been
installed; `python.exe` and the launcher would then fail at load time. The
current check is the only thing that installs the UCRT (via the redist) there.
This is a residual risk, not an argument to keep the check for Windows 10, and
§6.4 proposes the one-line gate that makes the supported-OS claim true.

## 5. Failure mode and logic defects

### 5.1 Current offline behavior (before the patch)

- Clean Windows 10 x64, no redist, offline: the outer test
  (`installer.nsi:246-247`) reads `$SYSDIR`, which under WOW64 is
  `C:\Windows\SysWOW64` (the file's own comment at `:255-257` says so).
  `ucrtbase.dll` is present, `msvcp140.dll` is not, so the check enters. The
  x64 branch disables redirection, tests `System32`, finds no `msvcp140.dll`,
  and runs the x64 redist. If the network is down, the download-failed box
  appears and `Abort` unwinds the installer. Nothing is installed. (Whether
  the x64 redist also installs the x86 runtime is the package-split question
  discussed in §4.2; Microsoft describes the x64 package as the 64-bit
  libraries for x64 systems, so this note assumes it does not. The VM matrix
  in §7.3 verifies it.)
- Same machine online: the x64 redist installs the 64-bit CRT. The
  post-install test (`macros.nsh:285-286`) checks `System32` and passes. The
  x86 `vcruntime140.dll` is still missing, so `PIMELauncher.exe` (x86) cannot
  start. In other words, **the current check is already insufficient for the
  launcher on clean x64**; the removal does not create that particular
  failure, it only stops paying for the useless x64 download.
- Clean Windows 10 x86: the `Else` branch (`installer.nsi:273-274`) downloads
  the x86 redist unconditionally, which installs the x86 CRT. The launcher
  works today; removing the check is a regression here unless the launcher is
  made static.
- Upgrade over an old version offline: `.onInit` removes the old version
  first (`:220-221`, `:117-165`), then the download fails and aborts, leaving
  the user with neither version. This is the failure the issue is reacting to.

### 5.2 Silent installs

`MessageBox` at `macros.nsh:276` has no `/SD`, so `/S` does not suppress it.
The NSIS runtime only auto-answers when a silent default is encoded in the
message type (`Source/exehead/util.c:126-150`, v3.08). A clean offline
unattended install therefore waits for a human. After removal, `/S` completes
without UI. The failure boxes at `:281` and `:287` and `.onInstFailed` at
`:233` are also un-suppressed, so today a failed `/S` install can produce
multiple dialogs.

### 5.3 After removal (literal patch)

- Clean Windows 10 x86 offline: install completes; `PIMELauncher.exe` fails to
  load (`VCRUNTIME140.dll` not found), so the TSF client has no backend; the
  Run-key launch at logon fails the same way. `[INFERENCE]` for the exact
  loader dialog; the import table is observed.
- Clean Windows 10 x64 offline: same launcher failure (it already fails today
  unless the user happened to install the x86 redist).
- Python: fine — `python.exe` loads its local `vcruntime140.dll`, and the UCRT
  is in-box. Node: fine (no CRT imports). Text services: fine (`/MT`).
- The user-visible symptom is PIME installing successfully but not working;
  there is no longer a prompt explaining anything.

### 5.4 The check's logic is also wrong (independent of #966)

- It tests `msvcp140.dll`, which **no shipped PIMELauncher/PIMETextService/
  Python/Node binary imports** (observed over all 37 tracked PEs and the five
  CI artifacts). It never tests `vcruntime140.dll`, which the launcher *does*
  import. So the check is aimed at the wrong DLL.
- The outer test uses `$SYSDIR` = `SysWOW64`; the x64 branch switches to
  `System32`. The comment at `:249-250` says only one architecture needs the
  DLLs, but the code requires the pair in whichever directory it examines.
  A machine with only the x64 redist (both files in `System32`, neither in
  `SysWOW64`) fails the outer test, enters the x64 branch, passes the inner
  test, and downloads nothing. The x86 runtime stays missing — a
  false-negative for the x86 launcher. This is `[INFERENCE]` from reading the
  branch structure plus the documented package split (§4.2), not observed on
  a VM.
- On x86 Windows the `Else` branch downloads unconditionally whenever the
  outer check fired (`:273-274`), with no second look at `System32`; that is
  the correct bitness there, but it still prompts/downloads on a machine where
  only one of the two checked DLLs is missing.
- On ARM64 the `${RunningX64}` test (`:248`) is true for the x86 installer:
  NSIS 3.08's `RunningX64` ORs `IsWow64Process2` with `IsWow64Process`
  ([x64.nsh](https://github.com/kichik/nsis/blob/v308/Include/x64.nsh)), and
  `IsWow64Process2` reports the x86 process as WOW64 on ARM64. The
  `${ElseIf} ${IsNativeARM64}` branch (`:265-271`) is therefore unreachable;
  the x64 bundle is downloaded instead. That happens to work because the x64
  package contains ARM64 binaries (§4.2). `[INFERENCE]` for the runtime
  behavior; the macro source is cited.
- The macro's post-install verification (`macros.nsh:285-290`) checks the
  same redirected/unredirected `$SYSDIR` as the branch that ran, so it cannot
  detect the missing other-bitness runtime.

## 6. Patch shape

### 6.1 Prerequisite: make the launcher's CRT static

This is the only code change that makes the removal safe. In
`PIMELauncher/CMakeLists.txt` (currently one line,
`corrosion_import_crate(MANIFEST_PATH Cargo.toml)`), add:

```cmake
corrosion_add_target_rustflags(PIMELauncher "-Ctarget-feature=+crt-static")
```

- The target is the imported `[[bin]]` target `PIMELauncher`
  (`PIMELauncher/Cargo.toml:6-8`; the artifact path in
  `build-and-sign.yaml:69` is `build/PIMELauncher/PIMELauncher.exe`).
- `corrosion_add_target_rustflags` exists in the pinned Corrosion `v0.6`
  ([`CMake/Corrosion.cmake:1180`](https://github.com/corrosion-rs/corrosion/blob/v0.6/cmake/Corrosion.cmake#L1180))
  and sets `RUSTFLAGS` for the target ([Corrosion
  usage](https://corrosion-rs.github.io/corrosion/usage.html)). Using
  `RUSTFLAGS` matters: Cargo gives the environment variable precedence over
  `.cargo/config.toml` ([Cargo config, build.rustflags](https://doc.rust-lang.org/cargo/reference/config.html#buildrustflags)),
  so putting the flag only in `.cargo/config.toml` would be ignored under
  Corrosion.
- `+crt-static` is the Rust target feature for static CRT linkage; the Rust
  Reference describes the default as dynamic and the feature as the selector
  ([linkage](https://doc.rust-lang.org/reference/linkage.html)).

Acceptance for this line is a Windows build check, not a source review:
`dumpbin /dependents build\PIMELauncher\PIMELauncher.exe` must no longer list
`VCRUNTIME140.dll` (and must still not list `MSVCP140.dll`). That is
`[INFERENCE]` until run on Windows.

Fallback if the Rust build cannot be changed: copy the x86
`vcruntime140.dll` from the *build toolset* (`%VCToolsRedistDir%\x86\...`)
into `build\PIMELauncher\` in `build.bat`, add
`File "..\build\PIMELauncher\vcruntime140.dll"` after
`installer.nsi:303`, add `!insertmacro SafeDeleteFile
"$INSTDIR\vcruntime140.dll"` to `CleanOldBinaries` (`macros.nsh:113-123`) so
upgrades do not leave a stale DLL, and `Delete "$INSTDIR\vcruntime140.dll"`
before `RMDir /REBOOTOK "$INSTDIR"` (`installer.nsi:621`). This is more
invasive, ties the installer to a toolset path, and is not recommended. Using
the Python copy (14.42) is not guaranteed to satisfy a VS 2026 Rust std, so do
not use it as the toolset runtime.

### 6.2 Remove the check and the macro (#966)

| File | Delete | Symbol / keys |
| --- | --- | --- |
| `installer/installer.nsi` | `238-277` (plus one adjacent blank if desired) | `Function ensureVCRedist` |
| `installer/installer.nsi` | `286-288` | TODO comment, `Call ensureVCRedist` |
| `installer/macros.nsh` | `258-297` (plus one adjacent blank) | macro banner + `DownloadAndInstallVCRedist` |
| `installer/locale/English.nsh` | `19-21` | `DOWNLOAD_VCREDIST_QUESTION`, `DOWNLOAD_VCREDIST_FAILED_MESSAGE`, `INST_VCREDIST_FAILED_MESSAGE` |
| `installer/locale/SimpChinese.nsh` | `19-21` | same keys |
| `installer/locale/TradChinese.nsh` | `19-21` | same keys |

Ordering constraints: none between these edits. `LANG_STRING` defines the
keys before the locale files are loaded (`installer.nsi:97-107`), and the
macro is expanded only inside `ensureVCRedist` (`:261,269,274`), which is
deleted in the same change. Deleting a macro while a call remains would make
makensis fail with "macro named … not found"; deleting a key while the macro
remains would make `$(DOWNLOAD_VCREDIST_QUESTION)` an undefined-language
string (makensis warning/error depending on settings). Delete both sides
together.

Encoding: `installer/installer.nsi` and all three `locale/*.nsh` files start
with a UTF-8 BOM (observed: first bytes `ef bb bf`), and the header says the
file must remain BOM'd. `macros.nsh` has no BOM. Keep the existing encoding;
do not convert line endings.

### 6.3 Remove `inetc`

- Delete `installer/installer.nsi:37-39` (comment + `!addplugindir`).
- `git rm -r installer/inetc` (39 files).
- Update `docs/agents/verification.md:100-102` to drop "inetc and".

No build-script or workflow changes are needed. Keeping the plugin has no
justification found: no other `inetc::` call, no packaging reference, no
StdUtils dependency. If a future installer feature needs HTTP, the plugin can
be re-vendored from
[nsis.sourceforge.io/Inetc_plug-in](https://nsis.sourceforge.io/Inetc_plug-in);
leaving 39 dead files in the tree is the worse option.

### 6.4 Optional but recommended: enforce the Windows 10 floor

The issue's safety argument assumes Windows 10. Make that true:

- `installer/installer.nsi:185-187` gates on `${AtLeastWinVista}`. There is no
  `${AtLeastWin10}` to swap in, contrary to an earlier revision of this note:
  NSIS 3.08–3.13 `WinVer.nsh` stop at `${AtLeastWin8}` (checked at tags v308,
  v309, v310, v311, v312, v313), and `master` defines only `${AtLeastWin11}`
  (through `WinVer_BuildNumCheck`). `WINVER_10` exists as a numeric define, but
  the OS-test macro does not.
  A 3.08-compatible floor is a two-part check: `${IfNot} ${AtLeastWin8}` →
  reject, then `ReadRegDWORD` `CurrentMajorVersionNumber` under
  `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion` → reject when it is
  absent or below 10 (only Windows 10+ writes it; 8.1 still reports 6.3). The
  alternative, bumping the CI NSIS (`build-and-sign.yaml:86` pins 3.08) to a
  build that would carry `${AtLeastWin11}`, buys nothing here: 11 is not the
  floor.
- Rename `AtLeastWinVista_MESSAGE` (or at least rewrite its text) in
  `installer/locale/{English,SimpChinese,TradChinese}.nsh:14` to say Windows 10
  or later. The current text says "Windows Vista or later", which is already
  inconsistent with the product claim.

Without this, a Windows 8.1 install succeeds after the removal and then fails
at `ucrtbase.dll`/`vcruntime140.dll` load time unless the machine was fully
updated. With it, unsupported systems are rejected before old-version removal
(the gate is in `.onInit` before `uninstallOldVersion`, `:185-187` vs `:220`).

### 6.5 Diff estimate

- Launcher fix: 1 added line (plus a CI dependency check, ~10 lines).
- Issue deletion: 92 deleted lines across 5 files.
- `inetc`: 3 deleted lines + 39 deleted files (215 KiB in git).
- Docs: 1 edited line.
- Optional OS gate: ~10 lines in `installer.nsi` + 4 locale strings.

Total for the safe version: +1 line, −95 lines, 39 files removed.

## 7. Verification plan

### 7.1 Linux/local (static)

```
git grep -n -E 'VCREDIST|vc_redist' -- installer   # expect no output
git grep -n 'DownloadAndInstallVCRedist' -- installer  # expect no output
git grep -n 'inetc' -- installer build.bat .github appveyor.yml appveyor.after_build.bat  # expect no output after 6.3
git grep -n 'INST_VCREDIST\|DOWNLOAD_VCREDIST' -- installer/locale  # expect no output
tests/run_local_tests.sh                           # unaffected layers must stay green
```

The `-- installer` scope matters because this research note contains the same
words; `git grep` over the whole tree would match the note itself.

`tests/run_local_tests.sh` covers the Python/Node/Go/C++ host layers but not
the installer. The NSIS compile cannot be checked here: `docs/agents/verification.md:98-102`
states that Linux `makensis` cannot preprocess the installer because the
Windows `StdUtils` plugin is unavailable; after §6.3 the note should no longer
blame `inetc`.

### 7.2 Windows CI (must pass)

- `build-and-sign` (every push/PR; `ci.yaml:8-20`) runs `build.bat` and then
  `makensis` (`build-and-sign.yaml:54-58,106-109`). That is the real check for
  the deleted function/macro/strings. AppVeyor's `appveyor.after_build.bat:3`
  also runs makensis and should stay green.
- Add a dependency gate after `build.bat` and before upload:
  locate `dumpbin.exe` (e.g. `vswhere -latest -find "VC\Tools\MSVC\**\bin\Hostx64\x64\dumpbin.exe"`),
  run `dumpbin /dependents build\PIMELauncher\PIMELauncher.exe`, and fail if
  the output matches `VCRUNTIME140|MSVCP140|VCRUNTIME140_1`. This is cheap,
  catches a regression in the static-CRT flag, and is the only reliable
  Windows-side check for the actual gap — CI runners have the VC++ redist
  installed, so a *runtime* smoke there cannot prove clean-machine behavior.
- Optional: scan the five uploaded artifacts with the same gate. Today the
  only allowed `VCRUNTIME140` importer is under `python\` (and that directory
  carries the DLL); the launcher and the text services must be clean.

### 7.3 Manual clean-VM matrix

These are manual because they need a clean, offline image; CI runners are not
clean and are online.

1. **Windows 10 22H2 x64, offline, no VC++ redist.** Before install, record
   that `System32`/`SysWOW64` contain `ucrtbase.dll` but not
   `msvcp140.dll`/`vcruntime140.dll`. Install with `/S`; expect no prompt,
   successful install, `PIMELauncher.exe` running, IME usable. Verify with
   `dumpbin /dependents $INSTDIR\PIMELauncher.exe`.
2. **Windows 10 22H2 x86, offline, no redist.** This is the regression case
   for the removal; expect the same success with the static-CRT launcher.
3. **Windows 11 ARM64, offline.** x86 installer under emulation; verify the
   ARM64X text service loads in ARM64 apps, the x86 service in x86 apps,
   `PIMELauncher` runs, and the Python/node backends start.
4. **Upgrade over PIME 1.3.x, offline.** Confirm the old version is removed,
   no VCRedist prompt appears, the new install completes, and user
   dictionaries/settings survive.
5. **Uninstall.** No files left in `$INSTDIR` (in particular no
   `vcruntime140.dll` if the fallback in §6.1 was used), no Run key, no COM
   registration.
6. **Windows 10 N edition.** UCRT is present; install and launch succeed.
7. **Optional Windows 8.1.** With §6.4, the installer should refuse before
   touching the old version; without it, document that install succeeds but
   Python/launcher fail without the UCRT update.

## 8. GO/NO-GO

**NO-GO for the literal three-task patch.** The removal is correct for the
UCRT, `msvcp140` (no importer) and the Python/Node payload, but it leaves
`PIMELauncher.exe`'s `VCRUNTIME140.dll` import unsatisfied on clean machines;
the Python-bundled copy is not on its search path, and the installer does not
put it there. On clean x86 it is a new regression; on clean x64 the launcher is
already broken today because the check installs only the 64-bit redist.

**GO for the removal bundled with the launcher static-CRT change** (one CMake
line) and the inetc deletion. One-line reason: only one shipped binary still
imports a redistributable CRT DLL, and making that binary `/MT` removes the
last real dependency; everything else either carries its runtime or imports
none, and Windows 10 supplies the UCRT.

Residual risks:

- `msvcp140.dll`: no current binary imports it, but a future third-party DLL
  rebuilt with `/MD` and C++ std would. The CI dependency gate should treat
  `MSVCP140` as a hard failure (outside the Python tree, where none exists
  today).
- `vcruntime140_1.dll`: same treatment; no importer today.
- `chewing.dll` is dynamic-CRT and only works in-process with Python. If the
  Python interpreter stops shipping `vcruntime140.dll` (e.g. a future CPython
  change) or chewing is loaded from a process without the runtime, it breaks.
  Re-check the Python ZIP contents on every runtime upgrade.
- The Python 3.12 embeddable ZIP's `vcruntime140.dll` is version 14.42; it is
  byte-identical to upstream CPython's, but it is not a substitute for the
  launcher's toolset runtime. Do not point the fallback at it.
- Unsupported Windows 7/8.1 installs are not gated. Without §6.4, removing the
  UCRT check makes those installs *look* successful and fail later. With
  §6.4, the product statement and the code agree.
- `inetc` is deleted, so there is no longer any network access during setup.
  Nothing else used it; a future online bootstrap would need a new mechanism.
- ARM64: the `${RunningX64}`/`${IsNativeARM64}` ordering means the ARM64 URL
  is dead code today. The x64 bundle contains ARM64 binaries per Microsoft, so
  behavior is correct by accident; after removal the whole branch disappears,
  which is a cleanup rather than a risk. Verify the ARM64X text service in the
  matrix anyway.
