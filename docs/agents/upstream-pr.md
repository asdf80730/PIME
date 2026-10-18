# Upstream pull requests

A PR to `EasyIME/PIME` carries the product change only. The local harness stays local.

- Branch from `origin/master`. Local `master` is the integration branch; it also carries
  `docs/agents/`, `GLOSSARY.md`, research notes, and CI steps that run local test suites.
- Ship the smallest diff that fixes the issue. Regression tests, CI wiring and HACKING
  entries stay on local `master` unless the maintainer asks for them in the PR.
- Verify before pushing: `cd node && npm test`, the Python suite, and a YAML parse of
  `.github/workflows/build-and-sign.yaml`.
- Commit messages follow `AGENTS.md` §2, including the AI declaration.
- Push the branch to the `fork` remote. The PR itself may need the browser compare URL:
  the personal access token pushes to repos the account owns but cannot create PRs on
  `EasyIME/PIME` (`403 Resource not accessible by personal access token`).
