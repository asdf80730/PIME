# 10: Cut the twelve product PR branches from the split table

**What to build:** every row of the `spec.md` split table exists as a branch on the
fork off the product remote's master, each with its body file and printed compare URL.

Status: ready-for-agent
Category: enhancement
Blocked by: 01, 02, 03

- [ ] Rows 1-12 each carry a `pr/<topic>` branch with only product paths
- [ ] `bash <integration-checkout>/tests/check_pr_scope.sh <branch>`, `check_pr_commit_claims.sh`,
      `check_pr_commit_declarations.sh` and `check_fork_ci_noise.sh` all answer before the push
- [ ] Each body file `.scratch/pr-<n>-body.md` passes `bash tests/check_pr_bodies.sh`
- [ ] Rows 5 and 6 reuse the existing `pr/cinbase-per-ime-config` and
      `pr/chewing-userphrase-393` rather than opening twins
- [ ] Row 4 waits on upstream #1004, so it stays un-pushed until that merges

## Comments

Form per `docs/agents/upstream-pr.md`: title `type(scope): what it does (#<issue>)`,
body `Fixes #<issue>`, why, bullets, `Validation:`, declaration last.

*(Comment generated with AI assistance from omp (tensorfold/Qwen3.8-Flash-Next))*
