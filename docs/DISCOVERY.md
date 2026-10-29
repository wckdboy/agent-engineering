# Repository discovery

Observed on 2026-10-29 from `/Users/dearwolf/wckdboy`. The workspace root is **not** a git
repository; it contains 28 independent git repositories and several scratch directories. The kit was
therefore built as a portable, self-contained directory and installed into one pilot rather than
assuming a monorepo.

## Observed facts

| Fact | Evidence |
| --- | --- |
| 28 git repositories under the workspace root | `find . -maxdepth 2 -type d -name .git` |
| 10 `AGENTS.md` files, several with a `CLAUDE.md` pointer | `find . -maxdepth 2 -name AGENTS.md` |
| 89 GitHub Actions workflow files | `find . -path '*/.github/workflows/*.yml'` |
| No shared engineering skill kit; only product-specific skills | `polykrom/skills/`, `solidcraft/skills/`, `reference/t3code/.agents/skills/` |
| Before this work, no gitleaks or Semgrep configuration outside vendored third-party code | `find` for `.gitleaks.toml`, `semgrep.yml`, `osv-scanner.toml` |
| `sovware`: Rust + Python, 48 tracked files, `make check` = fmt + clippy + tests + demo + eval + ledger checks; ~3.2 s | `sovware/Makefile`, `scripts/check.sh` |
| `polykrom`: ~1,465 JSON, 1,262 Rust files; 14 workflows; 7.3 GB working tree including `target/` | `git ls-files`, `du -sh` |
| `autobot`: Kotlin/Android plus large vendored C/C++ trees | `git ls-files` suffix counts |
| `Mosaic`: Swift/Rust; `harness2`: Python; `tinyrex`: Python/design assets | same |

## Inferred friction (tested where practical)

1. **No common verification record.** Each repository has its own commands and CI, but no portable
   way to say which checks ran, on which revision, with which tool versions. This is the highest-value
   gap and the reason for the evidence schema.
2. **Agent policy is duplicated and uneven.** Strong `AGENTS.md` files exist in the mature repos;
   others have none. There is no shared lifecycle for impact analysis, regression proof, worktree
   isolation or release verification.
3. **Security scanning is mostly absent.** Only a CodeQL workflow and a vendored Trivy ignore were
   found. Dependency and secret scanning are not consistently configured.
4. **Parallel work has no convention.** Worktrees are used ad hoc (for example `solidcraft-wt`,
   `polykrom-step/repo`), without ownership records, a concurrency cap or an integration rule.
5. **Large working trees punish naive context loading.** `polykrom` is 7.3 GB with `target/`; any
   default whole-repository scan or dump is wasteful. The kit uses tracked-file inventories, exact
   symbol search and capped output.
6. **CI actions are not uniformly pinned.** The new kit template pins SHAs; the existing `sovware`
   workflow still uses floating major tags for checkout/toolchain/cache/setup-python. This is a
   recorded gap, not silently changed.

## Assumptions (not proven)

- The same maintainer controls the repositories and intends changes to be portable across them.
- GitHub Actions is the CI system for the active projects; self-hosted runners and Coolify are
  described in `platform/` but were not exercised.
- Python 3.11+ and git are available on developer machines and Linux runners. The kit avoids
  third-party Python packages; this was exercised on Python 3.15 and is written for 3.11+.
- The pilot (`sovware`) is representative enough for control validation but not for performance or
  security claims about other repositories.

## Pilot choice

`sovware` was chosen because it has a fast, offline `make check`, a real GitHub Actions gate, a
small tracked surface, and an existing evidence/ledger culture that makes an inaccurate "pass"
especially costly. It is a low-blast-radius place to prove the controls before rolling them into
`polykrom` (large Rust workspace) or `platform` (infrastructure policy).
