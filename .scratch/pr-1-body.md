refactor(cinbase): collapse the nine cin Service bodies onto one shared module

No separate issue; the nine duplicate Service bodies are the whole story.

The eight classic cin Services were copies of one ~140-line body differing
only in four data points, so a fix landed in one file did not reach the
others. One module now carries that body behind template hooks and each
binding keeps only what is genuinely per-Service.

- `python/cinbase/service.py` owns the shared body: the twelve TSF
  delegations, the ctor order, the holder field names and the loader
  argument order are unchanged.
- Each `python/input_methods/*/*_ime.py` keeps just the class
  serviceManager resolves from its ime.json, its data points
  (`imeDirName`, `maxCharLength`, `cinFileList`, the table-kind set) and its
  three table-holder singletons.
- chephonetic keeps its keyboard-layout extras and `updateCompositionChar`
  as hook overrides; chebihua still rides its own `table_loaders` through a
  `loadMainTable` override; chepinyin reads the loader from its own module.

Validation:

- `python/python3/python.exe` `-m unittest discover -s tests -p "test_cinbase_shift_to_english.py"`
  on the integration tree carrying this diff: `Ran 9 tests ... OK` — the
  shift-letter exits, the lone-candidate space confirm and the ordinary-path
  fallbacks all answer through the shared body.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
