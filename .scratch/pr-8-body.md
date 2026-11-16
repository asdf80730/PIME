fix(rime): give each Windows input language its own ime.json folder (#481)

Fixes #481

One manifest is one Windows language profile. The rime engine serves
zh-Hant-TW and zh-CN, so each backend ships one input_methods folder per
language, each with its own profile GUID, and the readers go back to
comparing the flat guid only.

- `python/input_methods/rime` and `python/input_methods/rime-cn` each carry
  their own ime.json; the rime-cn twin re-exports the shared
  `python/rimebase/rime_service.py` through its own thin wrapper.
- `PIMETextService/PIMEImeModule.cpp` matches the flat guid through the
  header-only helper in `PIMETextService/ImeProfileGuids.h`;
  `PIMETextService/DllEntry.cpp` documents the one-manifest shape.
- `go-backend/input_methods/rime-cn/ime.json` joins the go tree and
  `go-backend/server.go` registers both folders against the same rime
  implementation; `node/loadServices.js` compares the directory's own guid.
- `python/serviceManager.py` records the flat guid per directory and the
  `installer/installer.nsi` rime section installs the shared engine from
  `python/rimebase` plus one folder per language.

Validation:

- `go test ./...` in `go-backend`: the two shipped rime manifests each name
  one profile guid and the meow manifest stays one manifest, one profile.
- `python/python3/python.exe` `-m unittest discover -s tests -p "test_service_manager.py"`
  on the integration tree carrying this diff: `Ran 14 tests ... OK` — both
  rime folders resolve to distinct GUIDs.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
