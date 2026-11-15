# 08: Land the `McBopomofoWeb` pin without a dirty submodule

**What to build:** `git submodule status` answers a plain SHA for `McBopomofoWeb`,
so the integration ref's tree is reproducible.

Status: ready-for-agent
Category: bug
Blocked by: None

- [ ] `git submodule status` prints no dirty marker for `McBopomofoWeb`
- [ ] The submodule's own commit is pushed to its remote, and the superproject pin
      matches that SHA exactly
- [ ] `python/python3/python.exe tests/run_worktree_tests.py tests/test_js_ime_options.py .`
      stays green on the committed bytes

## Comments

`docs/agents/verification.md` records the layout: the payload sits in
`<submodule>/output/pime/` with `index.js` rebuilt by `build.bat`.

- Push to `openvanilla/McBopomofoWeb.git` was refused (403, no credentials), so
  the submodule commit `c0c99b2c1e14e0991b09d138c4a280b1d7798204` (answered by
  `git -C McBopomofoWeb rev-parse HEAD` in `tax-08`; the superproject pin of
  `omp/tax-08` matches it) travels as
  `.scratch/mcbopomofoweb-pin-c0c99b2c1e14e0991b09d138c4a280b1d7798204.patch`
  until upstream can take it.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
