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
```

At time of writing the pin is `452f6221fbad90c0706a3963b17e226216e40dd7`
(`set(LIBCHEWING_VERSION 0.5.1)` in its `CMakeLists.txt`). Re-read the pin
from `git submodule status`; do not trust this line.

## Which file answers which question

| Question | File at the pin |
| --- | --- |
| What is declared, with what doc comments | `include/chewingio.h` (the `userphrase_*` family carries no `@return` docs at this pin) |
| What an API entry point actually returns | `src/chewingio.c` (`grep -n 'CHEWING_API int chewing_userphrase_' src/chewingio.c`) |
| What the sqlite backend returns through those entry points | `src/userphrase-sql.c` (`UserRemovePhrase` returns `sqlite3_changes`, `UserUpdatePhrase` returns a `USER_UPDATE_*` action) |

## userphrase_* return conventions (measured at the pin, 2026-10-30)

Re-derive with the greps above if anything reads wrong.

| Call | Success | Failure |
| --- | --- | --- |
| `userphrase_enumerate` | `0` | `-1` (null ctx / sqlite reset fail) |
| `userphrase_has_next` | `1`, fills `phrase_len`/`bopomofo_len` **including the NUL byte** | `0` (end of rows or error — not distinguishable) |
| `userphrase_get` | `0` | `-1` (null args, buffer smaller than reported) |
| `userphrase_add` | `1` | `0` (phrase/bopomofo length mismatch, invalid bopomofo, update fail), `-1` (null ctx, OOM) |
| `userphrase_remove` | rows deleted `>= 1` | `0` (phrase not found, invalid bopomofo, bind fail — all indistinguishable), `-1` (null ctx/args) |
| `userphrase_lookup` | `1` (found) | `0` (not found or invalid bopomofo) |

Note the asymmetry: most `chewing_*` setup calls (`chewing_Reset`,
`chewing_set_KBType`, …) return **0 on success**, while the userphrase family
mixes `1 = ok` (add), `>=1 = rows` (remove) and `0 = ok` (get, enumerate).
Reading one member's convention onto another inverts results silently.

## The Python binding passes the C return through raw

`python/libchewing/libchewing.py` resolves `chewing_*` symbols through
`ChewingContext.__getattr__` with ctypes' default `c_int` restype: negative
values reach Python intact, and no binding layer normalizes them. Consumers:
`python/input_methods/chewing/config_tool.py` (`UserPhraseHandler`) and its
regression seam `tests/test_chewing_user_phrase_editor.py`, which replays
these conventions in its stub.
