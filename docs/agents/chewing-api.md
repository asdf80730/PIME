# Chewing backend: the pinned libchewing is the authority

Any claim about what a `chewing_*` call returns is settled by the pinned
libchewing source, not by memory of libchewing docs (which changed across the
Rust rewrite) and not by analogy between neighbouring APIs in the same header.
The pin moves only when the maintainer bumps the submodule.

## Getting the source

`git submodule status` lists `libchewing`; a leading `-` means the checkout is
**uninitialized and empty** — the pin is not on disk until you run:

```sh
git submodule update --init libchewing
git -C libchewing submodule update --init data
```

The second command is not optional from 0.10 on: the dictionary *sources* moved
out of the library tree into the nested `data` submodule
(`chewing/libchewing-data`), and `src/editor/data/mini.dat` is the only table
still carried inline.

At time of writing the pin is `05ae6bcb9309c466a1b32d69c146bc583be04747`
(`set(CMAKE_PROJECT_VERSION 0.12.0)` in its `CMakeLists.txt`, released
2026-04-06). Re-read the pin from `git submodule status`; do not trust this line.

## Which file answers which question

| Question | File at the pin |
| --- | --- |
| What is declared, with what doc comments | `capi/include/chewing.h` (cbindgen-generated; the `@since`/`@return` prose lives here) |
| What an API entry point actually returns | `capi/src/io.rs` (`grep -n 'fn chewing_userphrase_' capi/src/io.rs`) — `capi/src/chewing.c` is empty at this pin, every entry point is Rust |
| Which dictionary files the engine loads, and what each one is for | `src/dictionary/loader.rs` (`DEFAULT_DICT_NAMES`, `ABBREV_FILE_NAME`, `SYMBOLS_FILE_NAME`) |
| How the `syspath` argument is split and searched | `src/path.rs` (`SEARCH_PATH_SEP` is `;` on Windows, `:` elsewhere) |
| The keyboard layouts a `set_KBType` number means | `capi/src/io.rs` (`chewing_KBStr2Num` doc list) and `src/editor/zhuyin_layout/mod.rs` |

`chewing_Init` is a **no-op returning 0** at this pin; the paths that matter are
the ones passed to `chewing_new2`/`chewing_new3`.

## The shipped data payload

`python/libchewing/data/` must carry what `AssetLoader` looks for by name: the
hash pair `word.dat`, `tsi.dat`, the keyboard and symbol tables `swkb.dat`,
`symbols.dat`, and the two names `capi/src/io.rs` puts in the default
dictionary list, `chewing.dat` and `chewing-deleted.dat`. A data dir that
holds only the first four logs `Dictionary file not found: chewing.dat` and
`Dictionary file not found: chewing-deleted.dat` from every init. The
0.5.x trio `dictionary.dat` / `index_tree.dat` / `pinyin.tab` is retired: the
trie is now split into a word and a tsi file, and the pinyin table is compiled
into the library. Regenerate the two dictionaries from the nested submodule with
the library's own tool (run from `libchewing/data/dict/chewing`):

```
chewing-cli init --csv word.csv <out>/word.dat
chewing-cli init --csv tsi.csv  <out>/tsi.dat
```

`swkb.dat` and `symbols.dat` are committed verbatim in the `misc/` directory of
the same submodule and are copied, not converted. Both are also read by the
Python layer directly — `python/input_methods/chewing/chewing_config.py` stats
them for its reload version — so the pair stays in the payload even though
`chewing_new2` never lists them.

`chewing.dat` is the third name in `DEFAULT_DICT_NAMES` and is not shipped, so
each new context logs one `Dictionary file not found: chewing.dat` line from
`src/dictionary/loader.rs`; that line is expected, not a failed load — `word.dat`
and `tsi.dat` carry the system dictionary.

## Building the shipped `chewing.dll`

The bundled interpreter is 32-bit, so the DLL must be `i686`. The verified build
matches upstream's own `CMakeLists.txt` (`corrosion_add_target_rustflags(chewing_capi
-Ctarget-feature=+crt-static)`, lines 96-102, the Windows branch) so the DLL keeps one CRT
with the embedded interpreter; on this Windows checkout it runs through the
vendored toolchain wrapper (`docs/agents/windows-toolchain.md`), where `T` is the
`.tools` directory in Windows form:

```
bash tests/run_windows_tool.sh libchewing \
  "set \"CC_i686_pc_windows_msvc=$T\\mingw64\\bin\\clang-cl.exe\" && \
   set \"CFLAGS_i686_pc_windows_msvc=--target=i686-pc-windows-msvc /MT /DWIN32_LEAN_AND_MEAN /D_MBCS /I$T\\msvc\\crt\\include /I$T\\msvc\\sdk\\include\\shared /I$T\\msvc\\sdk\\include\\um /I$T\\msvc\\sdk\\include\\ucrt\" && \
   set \"CRATE_CC_NO_DEFAULTS=1\" && \
   set \"RUSTFLAGS=-C target-feature=+crt-static -C linker=lld-link.exe -C link-args=/LIBPATH:$T\\msvc\\crt\\lib\\x86 -C link-args=/LIBPATH:$T\\msvc\\sdk\\lib\\ucrt\\x86 -C link-args=/LIBPATH:$T\\msvc\\sdk\\lib\\um\\x86\" && \
   cargo.exe rustc --release --target i686-pc-windows-msvc -p chewing_capi \
     --features chewing_capi/sqlite-bundled -- --crate-type cdylib"
```

`CRATE_CC_NO_DEFAULTS=1` plus the explicit `/I` list is what makes the bundled
`libsqlite3-sys` compile: the MinGW sysroot has no `um/x86` headers, so the SDK
and CRT include directories must be named. `/MT` keeps the C objects on the same
static CRT as the Rust side. The `i686-pc-windows-gnu` triple builds too but its
DLL faults inside `SqliteDictionary::open` when loaded by the embedded
interpreter (mixed CRT), so the `msvc` triple is the one to reproduce.

`sqlite-bundled` is what keeps the user dictionary working: without the `sqlite`
feature `guess_format_and_load` cannot open `chewing.sqlite3`, and the phrase
editor enumerates an empty dictionary.

## userphrase_* return conventions (measured at the pin, 2026-11-12)

Re-derive with the greps above if anything reads wrong.

| Call | Success | Failure |
| --- | --- | --- |
| `userphrase_enumerate` | `0` | `-1` (null ctx) |
| `userphrase_has_next` | `1`, fills `phrase_len`/`bopomofo_len` **including the NUL byte** | `0` (end of rows, or no `enumerate` yet — not distinguishable) |
| `userphrase_get` | `0` | `-1` (null ctx, no live iterator) |
| `userphrase_add` | `1` | `0` (null bopomofo, more than 11 syllables, learn error), `-1` (null ctx or null phrase) |
| `userphrase_remove` | `1` (one row) | `0` (phrase not found, invalid bopomofo, unlearn error), `-1` (null ctx/args) |
| `userphrase_lookup` | `1` (found) | `0` (not found or invalid bopomofo) |

Note the asymmetry: most `chewing_*` setup calls (`chewing_Reset`,
`chewing_set_KBType`, …) return **0 on success**, while the userphrase family
mixes `1 = ok` (add, remove, lookup), `>=1 = rows` (remove) and `0 = ok`
(get, enumerate). Reading one member's convention onto another inverts results
silently. `remove` reports `1` rather than a `sqlite3_changes` count from 0.10
on, which is still `>= 1` for the two callers that threshold on it.

## Other return conventions measured at the pin (2026-11-12)

Same probe file as the table above:
`.scratch/upstream-bug-backlog/sweep_libchewing_21.py` (dual-DLL, prints both columns;
raw dump `sweep-21-raw.txt`).

- `chewing_cand_TotalChoice` and `chewing_cand_TotalPage` read **0** until the list is
  open; `chewing_cand_open` (`capi/src/io.rs:2793`, `editor.start_selecting()`) or
  `chewing_handle_Down` opens it, `chewing_handle_Space` does not, and
  `chewing_cand_Enumerate` alone does not. PIME's own reader at
  `python/input_methods/chewing/chewing_ime.py:634-645` gates on
  `cand_TotalChoice() > 0` before `cand_Enumerate()`, so the count is what drives the loop.
- The deleted cache name is part of the default dictionary-name list —
  `capi/src/io.rs:137` and `:240` both carry
  `word.dat,tsi.dat,chewing.dat,chewing-deleted.dat` — and it sits next to the per-version
  `chewing.sqlite3`, so 0.5.1 and 0.12 pairs do not share one.
- The ASCII tables key on the letter case that arrives: `src/input/keymap.rs:74`
  (`QWERTY_MAP`) and `:172` (`DVORAK_MAP`) are 95-entry tables with one lowercase row
  carrying no key state (`:101` `b's' => (KEY_S, 's', 0)`) and one uppercase row carrying
  `KeyState::Shift` (`:149` `b'S' => (KEY_S, 'S', KeyState::Shift as u32)`), and
  `map_ascii` (`:31`) is a plain lookup that `unwrap_or_default()`s on a miss. The
  bopomofo side is matched per layout in its `key_press`
  (`src/editor/zhuyin_layout/standard.rs:35`, `hsu.rs:73`), so a layout question answered
  from the table alone must say which case it read.
- The 0.12 layout set is 17 (`chewing_kbtype_Total`): the 13 of 0.5.x plus
  `KB_COLEMAK`, `KB_COLEMAK_DH_ANSI`, `KB_COLEMAK_DH_ORTH`, `KB_WORKMAN`.
- The user-phrase store is **per context** at 0.12 and its file **lags** the store:
  rows written by one `ChewingContext` surface in another only after the next
  `chewing_new2` re-reads the file, so a fresh `chewing_new2` sees `[]` for a phrase added
  by the previous context; and after 67 360 `chewing_userphrase_add` calls the in-memory
  enumeration reports 8 420 rows while `chewing.sqlite3` still holds only the 3 rows of the
  deleted cache. 0.5.1 shared one store, committed each add, and showed the row at once.
  Neither is wrong for PIME, which keeps one context for the whole session.
- Easy symbols (`chewing_get_easySymbolInput`) are consulted only on the Shift side of
  `handle_key` (`src/editor/mod.rs:1157`); `chewing_handle_Default` never sets the shift
  state, so with easy input on, `,` commits `ㄝ` rather than `，`. PIME's wrapper calls
  `handle_Default`.
- `chewing_KBStr2Num` is read two ways and the columns differ: the raw `CDLL` answers
  `1` for a known layout name, while `python/libchewing/libchewing.py` answers `0`,
  because its `__getattr__` prefix passes the context first and the name lands in the
  `ctx` slot. Both columns are in `.scratch/upstream-bug-backlog/ticket49_probe.py`,
  the twin of the dual-DLL sweep named above — a probe in that directory is two
  levels under the root, so its `ROOT` is two `os.pardir` steps, and its `drive()` is
  the working tornado-handler stub (`RequestStartLine`, a `Host` header, a connection
  stub carrying `set_close_callback`) to copy into the next probe.

## The Python binding passes the C return through raw

`python/libchewing/libchewing.py` resolves `chewing_*` symbols through
`ChewingContext.__getattr__` with ctypes' default `c_int` restype: negative
values reach Python intact, and no binding layer normalizes them. Consumers:
`python/input_methods/chewing/config_tool.py` (`UserPhraseHandler`) and its
regression seam `tests/test_chewing_user_phrase_editor.py`, which replays
these conventions in its stub.
