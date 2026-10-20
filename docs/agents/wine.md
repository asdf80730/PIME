# Running the launcher tests under Wine (optional)

`windows-2025` CI is the authoritative Windows check. This recipe is a local
pre-check: it cross-compiles `PIMELauncher` for `i686-pc-windows-gnu` and runs its
15 tests under Wine 8. It does not touch the C++ text service.

## Setup (Debian bookworm, root)

```bash
dpkg --add-architecture i386
apt-get update
apt-get install -y --no-install-recommends \
  wine wine64 wine32:i386 gcc-mingw-w64-i686 binutils-mingw-w64-i686 build-essential

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
```

## Run

```bash
cd PIMELauncher
CARGO_TARGET_I686_PC_WINDOWS_GNU_RUNNER=wine \
WINEDLLOVERRIDES="bcryptprimitives=n;mscoree=;mshtml=" \
/root/.cargo/bin/cargo test --target i686-pc-windows-gnu
```

Done when all 15 pass: 12 unit tests in `src/lib.rs`, 1 in `src/main.rs`, and the
2 integration tests. The integration test spawns `mock_backend.exe`; the shim in
`syswow64` is what lets that child start. `cargo clean` is safe — the shim lives
in the Wine prefix, not the target directory.

## Limits

- Wine 8 is not Windows: ACLs, job objects, named-pipe security descriptors and
  console/service behaviour can differ. Green here is a smoke check; a C++/Rust
  change still needs a green `windows-2025` run.
- The C++ text service needs a real TSF host. It cannot build or run in this
  checkout; see `verification.md`.
