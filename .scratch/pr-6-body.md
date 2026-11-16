Fixes #393 — the user-phrase editor on the chewing page.

The phrase editor answered every POST through one complete handler that had
to unpack the status by hand. The maintainer asked for the success and error
arms the jQuery API offers instead, so each POST now answers its toast in
the arm that actually ran.

- `python/input_methods/chewing/js/user_phrase.js` reads the `{"result": 1}`
  the server reports (success only when every libchewing call succeeded) in
  the success arm, and the non-200 in the error arm.
- The toasts, their icons and the reload on close are unchanged.

Validation:

- `python -m compileall python` clean on the bundled 32-bit interpreter.
- The three node harnesses stay green on the tree carrying this diff (23
  fixture cases), and the phrase-editor delete dialog still reports the
  truth after each arm's own toast.

Architecture and design by asdf80730. Implementation generated with AI assistance from omp (Qwen3.8-Flash-Next).
