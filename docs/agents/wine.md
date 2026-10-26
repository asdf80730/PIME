# Running the launcher tests under Wine (optional)

`windows-2025` CI is the authoritative Windows check. This recipe is a local
pre-check: it cross-compiles `PIMELauncher` for `i686-pc-windows-gnu` and runs its
tests under Wine 8. It does not touch the C++ text service.

## Setup (Debian bookworm, root)

```bash
dpkg --add-architecture i386
apt-get update
apt-get install -y --no-install-recommends \
  wine wine64 wine32:i386 gcc-mingw-w64-i686 binutils-mingw-w64-i686 \
  build-essential ca-certificates curl

curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --default-toolchain stable
/root/.cargo/bin/rustup target add i686-pc-windows-gnu
```

`build-essential` supplies the host `cc` that proc-macro build scripts need; the
target's linker is `i686-w64-mingw32-gcc`. Initialise the prefix once with
`wine cmd /c echo ok`.

## The `bcryptprimitives` shim

Modern Rust links `ProcessPrng` from `bcryptprimitives.dll`; Wine 8 ships only
`bcrypt.dll`, so a 32-bit shim forwards the call. The exports must be undecorated
(`--kill-at`), and the DLL belongs in the prefix's 32-bit system directory so
spawned backends find it too.

```c
/* /tmp/bcryptprimitives.c */
#include <windows.h>
#include <bcrypt.h>

BOOL WINAPI ProcessPrng(PBYTE pbData, SIZE_T cbData) {
    return BCryptGenRandom(NULL, pbData, (ULONG)cbData,
                           BCRYPT_USE_SYSTEM_PREFERRED_RNG) == 0;
}

BOOL WINAPI SystemPrng(PBYTE pbData, SIZE_T cbData) {
    return ProcessPrng(pbData, cbData);
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved) {
    (void)instance; (void)reason; (void)reserved;
    return TRUE;
}
```

```bash
i686-w64-mingw32-gcc -shared -O2 -Wl,--kill-at \
  -o /tmp/bcryptprimitives.dll /tmp/bcryptprimitives.c -lbcrypt
cp /tmp/bcryptprimitives.dll ~/.wine/drive_c/windows/syswow64/
i686-w64-mingw32-objdump -p ~/.wine/drive_c/windows/syswow64/bcryptprimitives.dll \
  | grep -E 'ProcessPrng|SystemPrng'
```

Both names must appear without an `@8` suffix; a decorated name means the build
missed `--kill-at` and the exe will bind to Wine's unimplemented stub instead.

## Run

```bash
cd PIMELauncher
CARGO_TARGET_I686_PC_WINDOWS_GNU_RUNNER=wine \
WINEDLLOVERRIDES="bcryptprimitives=n;mscoree=;mshtml=" \
/root/.cargo/bin/cargo test --target i686-pc-windows-gnu
```

Done when every suite `cargo test` prints ends green — the lib, `src/main.rs`, and
the integration tests, whose counts the run reports itself. The integration test
spawns `mock_backend.exe`;
the shim in `syswow64` is what lets that child start. `cargo clean` is safe — the
shim lives in the Wine prefix, not the target directory.

## When a step hangs

Wine answers an unimplemented import by starting `winedbg` and waiting, so the
call never returns; a local run that hit one sat until its 25-minute deadline.
`tests/run_local_tests.sh` bounds every step (`STEP_TIMEOUT`, default 600s) and
prints `HANG` with the function to rerun; a hand-run Wine command needs its own
bound, `timeout 60 wine …`.

Bisect by writing the probe before the guesses: log each import to stderr, since
stderr survives the abort, then run the whole probe once under `timeout`. The
last line printed names the import that triggered it. That is how
`propsys.dll.VariantToString` surfaced — reaching it through `cinbase` is why the
`cinbase` test modules skip themselves under Wine.

## Limits

- Wine 8 is not Windows: ACLs, job objects, named-pipe security descriptors and
  console/service behaviour can differ. Green here is a smoke check; a C++/Rust
  change still needs a green `windows-2025` run.
- The C++ text service needs a real TSF host. It cannot build or run in this
  checkout; see `verification.md`.
- The bundled Python can abort in `init_sys_streams` with `WinError 6` when its
  stdout is a regular file, so `wine python/python3/python.exe … > log` can fail
  while a pipe passes; `tests/run_local_tests.sh` pipes that step through `cat` for
  this reason.
