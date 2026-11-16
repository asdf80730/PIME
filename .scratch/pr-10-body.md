fix(rime): keep the shared service manager in the shape the local suite pins (#481)

Fixes #481 — follow-up on the per-language folder split.

The mirrored copies of the dispatcher and the launcher protocol drifted when
the per-language folders landed: an unused import and a newer rustfmt
wrapping returned with them.

- `python/serviceManager.py` drops the unused sys import again.
- `PIMELauncher/src/protocol.rs` and `PIMELauncher/src/elevation.rs` keep
  the wrapping the pinned protocol shape expects.
- `python/input_methods/rime/rime_ime.py` keeps its declaration header
  beside the moved engine module.

Validation:

- `python/python3/python.exe` `-m unittest discover -s tests -p "test_service_manager.py"`
  on the integration tree carrying this diff: `Ran 14 tests ... OK` — the
  dispatcher still resolves every shipped manifest.
- `cargo fmt --check` and `cargo clippy` stay clean on `PIMELauncher`.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
