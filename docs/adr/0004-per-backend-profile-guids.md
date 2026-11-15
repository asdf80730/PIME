# Per-backend profile GUIDs; one `ime.json` per Windows input language

One IME ships one `ime.json` per backend, and each copy is self-contained: its
own `guid` for its one Windows input language profile. Two rules fall out of
that layout, and they differ in scope.

- **Within one file there is exactly one profile GUID.** `langProfileFromJson`
  (`PIMETextService/DllEntry.cpp`, called from `DllRegisterServer`) turns that
  `guid` plus `locale`/`fallbackLocale` into one `AddLanguageProfile` call, and
  `ImeModule::loadImeInfo` stops at the first manifest whose guid matches
  (`PIMETextService/PIMEImeModule.cpp`), so a second profile needs a second
  folder rather than a second entry in the same file.
- **Across files the GUIDs are not equal and are never compared.** Each backend
  is read by its own dispatcher, which loads only its own tree:
  `python/serviceManager.py` walks `base_dir/input_methods`,
  `go-backend/server.go` its `exeDir`, `node/loadServices.js` its `baseDir`, and
  `PIMETextService/PIMEImeModule.cpp` iterates the `backendDirs_` named in
  `backends.json`. So `{9C2D6C68-…}` (python 中州韻) and `{3F6B5A12-…}` (its go
  twin) are two independent registrations that no consumer ever matches against
  each other.

The locale pair is the one invariant that does carry across twins: every copy of
an IME must answer the same `locale`/`fallbackLocale` in the same slot, because
the language list shows one IME once per bucket, while the CLSID→profile map is
per backend and stays local to it.

The rime engine serves two Windows input languages, so it has one folder per
language in each tree that implements it: `input_methods/rime`
(`zh-Hant-TW`/`zh-TW`) and `input_methods/rime-cn` (`zh-CN`/`zh-CN`). Both
folders load the one engine — python from `python/rimebase`, go from
`go-backend/input_methods/rime` — so the module fields repeat verbatim in the
two manifests while the data files (`python/rimebase/data/PIME.yaml`, `icons/`) exist once.

Measured registration data, transcribed from the shipped manifests:

| Folder | python | go | node |
| --- | --- | --- | --- |
| `rime` | `{9C2D6C68-9EA6-4CFB-A769-7E619DB7F267}` | `{3F6B5A12-8D44-4E71-9A2E-6B4F9C1D2A30}` | no copy |
| `rime-cn` | `{53C15256-7A5F-4B54-86E8-0636E0745C3E}` | `{9882E350-9462-4D42-9882-7847044EA725}` | no copy |
| `meow` | `{C5F37DA0-274E-4837-9B7C-9BB79FE85D9D}` | `{7A1C2E93-5B64-4F88-AE21-3D9C6B70F145}` | `{C5F37DA0-274E-4837-9B7C-9BB79FE85D9D}` |
| `emojime` | — | — | `{A381D463-9338-4FBD-B83D-66FFB03523B3}` |

The `rime` rows answer `zh-Hant-TW`/`zh-TW`, the `rime-cn` rows `zh-CN`/`zh-CN`,
every other row `zh-Hant-TW`/`zh-TW`. The python and node `meow` literals
coincide because the node copy was written from the python one — that coincidence
is incidental and no rule requires it.

## Considered options

- **One `ime.json` per language profile** — adopted, and it is upstream's
  original layout, named by the maintainer in the #1021 review:
  `input_methods/rime/ime.json` plus `input_methods/rime-cn/ime.json`, each
  returning one profile from `langProfileFromJson`. It is what the four
  dispatchers already assume — each walks `input_methods/*` and reads one
  `ime.json` per subdirectory — so it costs one extra directory and the
  per-directory fields (`moduleName`, `icon`, `configTool`) repeat verbatim in
  each copy; the shared engine stays in one module folder.
- **One manifest with a flat `guid` plus an `additionalProfiles` array** — the
  shape the first cut of #1021 used, and now retired. Equivalent in
  `AddLanguageProfile` output, but it puts two Windows input languages in one
  folder while every dispatcher reads one manifest per folder, so both sides
  need a second code path: an array walk in each loader and a helper in the C++
  one. With the array gone, each dispatcher compares one flat `guid` again.
- **One GUID per IME, shared by every copy** — rejected: nothing reads two
  trees in one lookup, so equality buys no resolution and only doubles the edit
  surface; a shared literal would have to be changed in three places per IME.
- **Compare the GUIDs across twins in a test** — rejected: it fails today by
  design (the two `rime` copies differ), and the assertion that does hold
  cross-file is the locale pair, which `test_twins_agree_on_one_locale_per_ime`
  already pins.

## Consequences

- The guards in `tests/test_rime_registration_locale.py` are the mechanical
  halves of this decision: `test_every_profile_entry_carries_a_registration_guid`
  pins one named GUID per manifest and rejects a leftover `additionalProfiles`
  key, `test_rime_ships_one_folder_per_language_profile` pins the pair each
  rime folder answers, and `test_twins_agree_on_one_locale_per_ime` pins the
  locale pair across twins. None compares GUIDs across files, and this ADR is
  the reason.
- The table is a transcription of the shipped manifests, not a second source: a
  re-derived literal must be re-read from the `ime.json` it names, and the
  installer ships only those JSON files.
- A third Windows input language joins as a third folder with its own manifest
  and GUID, beside a shared engine folder; no cross-file equality is expected.
