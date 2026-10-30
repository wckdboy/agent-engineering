# Rollout and rollback

## Phase 1 — pilot (complete, pushed)

Target: `sovware` at `87fdfd6b1889` (working tree already had a user edit to `README.md`; it was not
touched).

Installed:

```text
.agents/                     kit copy (bin, lib, skills, references, config, hooks, ci, templates)
.agents/engineering.json     fast: cargo fmt/clippy/test; full: make check
.agents/config/              gitleaks, Semgrep, guard allowlist
.agents/hooks/               pre-commit guard, pre-push fast verify (core.hooksPath set)
.claude/skills -> ../.agents/skills
.opencode/skills -> ../.agents/skills
AGENTS.md                    one appended "Engineering controls" section
.gitignore                   .agents/evidence/ and .worktrees/
.github/workflows/ci.yml     scanner install, full verify, evidence artifact
```

Validation actually executed:

```sh
./.agents/bin/eng doctor
./.agents/bin/eng verify --profile fast     # pass, 3.24 s
./.agents/bin/eng verify --profile full     # pass, 7.11 s first run; 5 s later
./.agents/bin/eng evidence verify           # pass
actionlint .github/workflows/ci.yml         # pass
```

CI installation commands were exercised locally with Go 1.27.3 and the same pinned versions; the full
profile passed with those binaries on `PATH`. Not executed: the modified GitHub Actions workflow on a
GitHub runner. The local `actionlint` result is syntax/static validation only.

### Rollback

All pilot changes are additive and uncommitted. Roll back with:

```sh
cd sovware
git checkout -- AGENTS.md .gitignore .github/workflows/ci.yml
git config --unset core.hooksPath
rm -rf .agents .claude/skills .opencode/skills .worktrees
```

The user's pre-existing `README.md` edit is untouched. Evidence records are under `.agents/evidence/`
and are removed with `.agents/`; preserve them before rollback if they are needed as an audit trail.

## Phase 2 — large repository (`polykrom`, local branch `eng/portable-controls`)

Installed with a bounded fast profile (`fmt`, layers, lists, assets, io tests) and an authoritative
but unrun full profile (`cargo xtask ci`). `eng detect` took 1.8 s and the fast gate 22 s once the io
test binary was built. A legacy `solvecraft/1` fixture was added at
`crates/io/tests/fixtures/legacy-solvecraft-v1.solidcraft` with a test that loads and re-tags it.
Gitleaks/Semgrep pass after narrow suppressions. Four dependency advisories were patched; eight
unique unmaintained/transitive advisories remain documented in PR #281, which is open with every
check passing.

1. Install without hooks first; run `eng detect` and `eng impact` only (read-only).
2. Configure fast commands from the existing `plan/` and CI; avoid a full `cargo test` in the fast
   loop if it exceeds the budget.
3. Time gitleaks and Semgrep on the tracked tree; confirm `target/` and generated assets are excluded.
4. Add contract fixtures for the design format, CLI and file compatibility before enabling full.
5. Enable hooks only after the fast profile is reliably under the budget.

## Phase 3 — infrastructure (`platform`, local branch `eng/portable-controls`)

Installed the read-only quality gate: all 9 action references are pinned, zizmor and actionlint pass,
and the fast/full profiles run in 0.5 s / 3.2 s. `scripts/audit-config.sh` still reports an
organization-level failure: WCKDai does not require SHA-pinned actions. That policy change is an
owner decision; the repository itself passes. Keep the environment gates (`*_CONFIGURED`) as the
authorization boundary; the kit is not a substitute for them.

## Phase 4 — other languages

Generate commands per repository, then measure the fast profile. Do not copy a Rust profile into a
Swift or Kotlin repository. Add language-specific scanner rules with positive/negative fixtures.

## Upgrade procedure

```sh
./engineering/install.sh --target <repo>          # replaces kit code/skills
./engineering/install.sh --target <repo> --force  # also replaces scanner configs (not allowlist)
```

`engineering.json` and `guard-allow.txt` are preserved by default. Re-run `eng verify --profile fast`
and `--profile full`, then `eng evidence verify`. If a new kit version changes evidence semantics,
keep the previous `.agents/` directory until the old records are no longer needed.

## Rollback of a kit upgrade

The installer is a file copy; use git:

```sh
cd <repo>
git checkout -- .agents AGENTS.md .gitignore .github/workflows/ci.yml
```

If `.agents/` was never committed, restore from the previous kit copy or re-install the previous
tag/commit. Evidence chain integrity is independent of the code version because records carry their
own schema and hashes.
