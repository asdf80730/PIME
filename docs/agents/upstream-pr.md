# Upstream pull requests

A PR to `EasyIME/PIME` carries the product change only. The local harness stays local.

- Branch from `origin/master`. Local `master` is the integration branch; it also carries
  `docs/agents/`, `GLOSSARY.md`, research notes, and CI steps that run local test suites.
  The PR branch carries none of `docs/`, `tests/` or `AGENTS.md`, so read those and run the
  checks on `master` before branching, then switch back after pushing.
- Ship the smallest diff that fixes the issue. Regression tests, CI wiring and HACKING
  entries stay on local `master` unless the maintainer asks for them in the PR.
- Title: `type(scope): what it does (#<issue>)`. Body: `Fixes #<issue>` (or `Closes`), a
  short paragraph of why, bullets for the change, a `Validation:` list, then
  `Generated with assistance from omp (DeepSeek V4.1 Flash).` as the last line. The merged
  PRs here carry no `Summary`/`Evidence`/`Merge Danger` headings; do not import a generic
  template.
- The first workflow run from a fork PR sits in `action_required` until a maintainer
  approves it. Check `gh api repos/EasyIME/PIME/commits/<sha>/check-runs` before claiming
  CI evidence, and ask for the approval in the PR conversation.
- Verify on `master`: `tests/run_local_tests.sh` runs the Python, Node, C++ helper, Go and
  Rust layers plus the GitHub YAML parse, skipping toolchains this machine lacks. Use the
  narrow command in `docs/agents/verification.md` when that loop is too slow.
- Commit messages follow `AGENTS.md` §2, including the AI declaration.
- Deliver: push the branch to `fork`, write the PR body to
  `.scratch/pr-<number>-body.md`, then open the browser compare URL and paste the
  body. The fine-grained token cannot write: `addComment`, label, close, `gh pr create`
  and `gh pr edit` all return 403, so the delivery is the compare URL plus a body file.
  Rerun `tests/run_local_tests.sh` after writing the body: its `PR bodies carry the AI
  declaration` step fails when the last line is missing.
- Done means: branch pushed, body file written, compare URL printed:
  `https://github.com/EasyIME/PIME/compare/master...asdf80730:<branch>?expand=1`.
