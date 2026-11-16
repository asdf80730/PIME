refactor(textservice): hooks return their partial reply, the dispatcher merges

No separate issue; the hook return seam is the whole story.

The void setter hooks wrote into the reply through field-peeking reads, so
the reply shape was an implicit contract between seventeen functions. Each
hook now returns its own dict partial and the dispatcher owns the merge; the
wire bytes do not change.

- Each of the 16 setter methods in `python/textService.py` returns the dict
  partial it contributes.
- `CinBaseTextService` answers its void hooks with the per-request merge
  table; `handleRequest` folds hook partials in call order, drains the
  table, then appends return/success/seqNum.
- The 6 value hooks keep their exact pre-change returns, the request-parsing
  form and the seqNum/init/close paths stay as the shared wire reply shape
  pins them.

Validation:

- `python/python3/python.exe` `-m unittest discover -s tests -p "test_text_service.py"`
  on the integration tree carrying this diff: `Ran 15 tests ... OK` — the
  dispatcher merges hook partials in call order and the byte-identical
  request/reply pairs still answer.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
