# Upstream pull requests

A PR to `EasyIME/PIME` carries the product change only. The local harness stays local.

- Branch from `origin/master`. Local `master` is the integration branch; it also carries
  `docs/agents/`, `GLOSSARY.md`, research notes, and CI steps that run local test suites.
- Ship the smallest diff that fixes the issue. Regression tests, CI wiring and HACKING
  entries stay on local `master` unless the maintainer asks for them in the PR.
- Verify before pushing: `cd node && npm test`, the Python suite, and a YAML parse:
  `bun -e 'Bun.YAML.parse(await Bun.file(".github/workflows/build-and-sign.yaml").text())'`
  (`python3` has no PyYAML; Bun's parser throws on invalid YAML).
- Commit messages follow `AGENTS.md` §2, including the AI declaration.
- Deliver: push the branch to `fork`, write the PR body to
  `.scratch/pr-<number>-body.md`, then open the browser compare URL and paste the
  body. The fine-grained token returns 403 for `gh pr create` and `gh pr edit`,
  so those commands are not the delivery path; export a `public_repo` token if
  you need them.
- Done means: branch pushed, body file written, compare URL printed:
  `https://github.com/EasyIME/PIME/compare/master...asdf80730:<branch>?expand=1`.
