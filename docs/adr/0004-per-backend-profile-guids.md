# Per-backend profile GUIDs; the locale pair is the only cross-twin invariant

One IME ships one `ime.json` per backend, and each copy is self-contained: its
own `guid` for the default profile plus its own `additionalProfiles[].guid` for
each extra locale bucket. Two rules fall out of that layout, and they differ in
scope.

- **Within one file the GUIDs must be distinct.** `langProfileFromJson`
  (`PIMETextService/DllEntry.cpp:87`, called at `:192`) turns `guid` and each
  `additionalProfiles[].guid` into one `AddLanguageProfile` call under the same
  CLSID, and `ImeModule::loadImeInfo` stops at the first entry whose guid
  matches (`PIMETextService/PIMEImeModule.cpp:126-131`), so a value repeated inside
  one file makes two buckets answer with a single entry's fields.
- **Across files the GUIDs are not equal and are never compared.** Each backend
  is read by its own dispatcher, which loads only its own tree:
  `python/serviceManager.py:115` walks `base_dir/input_methods`,
  `go-backend/server.go:367` its `exeDir`, `node/loadServices.js:9` its
  `baseDir`, and `PIMETextService/PIMEImeModule.cpp:101` iterates the
  `backendDirs_` named in `backends.json`. So `{9C2D6C68-…}` (python 中州韻) and
  `{3F6B5A12-…}` (its go twin) are two independent registrations that no
  consumer ever matches against each other.

The locale pair is the one invariant that does carry across twins: every copy of
an IME must answer the same `locale`/`fallbackLocale` in the same slot, because
the language list shows one IME once per bucket, while the CLSID→profile map is
per backend and stays local to it.

Measured registration data, transcribed from the shipped manifests:

| IME | python | go | node |
| --- | --- | --- | --- |
| `rime` | `{9C2D6C68-9EA6-4CFB-A769-7E619DB7F267}` + `{53C15256-7A5F-4B54-86E8-0636E0745C3E}` | `{3F6B5A12-8D44-4E71-9A2E-6B4F9C1D2A30}` + `{9882E350-9462-4D42-9882-7847044EA725}` | no copy |
| `meow` | `{C5F37DA0-274E-4837-9B7C-9BB79FE85D9D}` | `{7A1C2E93-5B64-4F88-AE21-3D9C6B70F145}` | `{C5F37DA0-274E-4837-9B7C-9BB79FE85D9D}` |
| `emojime` | — | — | `{A381D463-9338-4FBD-B83D-66FFB03523B3}` |

Every row answers `zh-Hant-TW`/`zh-TW` in its first slot; the two `rime` copies
each add a `zh-CN`/`zh-CN` second profile of its own. The python and node `meow`
literals coincide because the node copy was written from the python one — that
coincidence is incidental and no rule requires it.

## Considered options

- **One GUID per IME, shared by every copy** — rejected: nothing reads two
  trees in one lookup, so equality buys no resolution and only doubles the edit
  surface; a shared literal would have to be changed in three places per IME.
- **Compare the GUIDs across twins in a test** — rejected: it fails today by
  design (the two `rime` copies differ), and the assertion that does hold
  cross-file is the locale pair, which `test_twins_agree_on_one_locale_per_ime`
  already pins.
- **Merge both rules into one per-file check** — rejected: the subjects differ,
  a file's own entry list versus the set of copies, so one loop cannot judge
  both without silently dropping the cross-twin half.
- **Leave the cross-tree duplicate unrecorded** — bounded instead:
  `loadImeInfo` breaks out of the backend scan at the first match
  (`PIMETextService/PIMEImeModule.cpp:139-140`), so with the python and node `meow`
  copies equal only the first-scanned tree (`python`, per `backends.json`)
  answers. Tolerable today because neither copy carries a `configTool` key; a
  duplicate that later grows differing fields is resolved by making the two
  literals differ, not by reordering `backends.json`.

## Consequences

- The two guards in `tests/test_rime_registration_locale.py` are the mechanical
  halves of this decision: `test_every_profile_entry_carries_a_registration_guid`
  pins the within-file rule per file, `test_twins_agree_on_one_locale_per_ime`
  pins the locale pair across twins. Neither compares GUIDs across files, and
  this ADR is the reason.
- The table is a transcription of the shipped manifests, not a second source: a
  re-derived literal must be re-read from the `ime.json` it names, and the
  installer ships only those JSON files.
- A fourth backend joins by adding a column and its own tree; no cross-file
  equality is expected of it.
