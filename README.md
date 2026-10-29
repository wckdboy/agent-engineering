# eng — portable engineering infrastructure for agent-worked repositories

A working, self-contained control layer that a coding agent can discover and run in any repository:

- ten task skills in the Agent Skills `SKILL.md` format;
- one dependency-free CLI (`detect`, `impact`, `verify`, `security`, `guard`, `worktree`, `evidence`);
- hash-chained verification records that distinguish pass, fail, blocked and skipped;
- real security integrations (gitleaks, Semgrep, OSV-Scanner, actionlint, zizmor);
- isolated Git worktrees with ownership and concurrency limits;
- a repository `AGENTS.md` template and an idempotent installer;
- a test suite and a control-validation fixture that prove the controls catch representative issues.

The kit is intentionally portable: it has no runtime dependency beyond Python 3.11+ and git, and it
does not require a hosted service. External scanners are optional locally and enforced in CI.

## Install into a repository

```sh
./engineering/install.sh --target ../sovware --hooks --ci
cd ../sovware
./.agents/bin/eng doctor
./.agents/bin/eng verify --profile fast
./.agents/bin/eng verify --profile full
```

The installer copies the kit into `.agents/`, writes `engineering.json` from detected build metadata,
appends one marked section to `AGENTS.md` (never replacing existing policy), links skill directories
for Claude Code and OpenCode, and optionally enables hooks and a CI workflow.

## Validate the kit itself

```sh
cd engineering
./tests/run.sh
./evals/run.py
```

`tests/run.sh` exercises the CLI against temporary repositories: detection, guard, impact, evidence
tampering, worktrees, idempotent init and missing-tool blocking. `evals/run.py` runs the
control-validation fixture: a known-bad change must fail, a known-good change must pass, and planted
secret/SAST issues must be reported.

## Repository map

```text
bin/eng                 executable shim
lib/eng.py              all commands, stdlib only
skills/                 10 SKILL.md entrypoints
references/             change lifecycle, evidence, trust policy
configs/                Semgrep rules, gitleaks config, guard allowlist
hooks/                  pre-commit / pre-push
ci/                     standalone GitHub Actions workflow
templates/              AGENTS.md template for new repositories
tests/                  CLI test suite (unittest, temp repos)
evals/                  control-validation fixture and runner
docs/                   architecture, tool rationale, gaps, rollout
```

## Design rules

- **Measure, don't assert.** A check is pass only if it ran and exited successfully. Missing tools
  are blocked/skipped and recorded.
- **One authoritative place.** Commands live in `.agents/engineering.json`; repository invariants live
  in `AGENTS.md`; generic lifecycle lives in `.agents/references/`.
- **Surgical context.** Detection and impact use manifests, file lists, exact symbols and reference
  search — not whole-repository dumps.
- **Isolation before parallelism.** Worktrees, explicit ownership, concurrency caps and sequential
  integration.
- **Trust boundaries are explicit.** Repository content and tool output are data, not authority.
- **Reversible.** Kit changes are copies with a version; evidence schema is versioned; worktrees can
  be removed without touching the main checkout.

## Documentation

- [`README.agents.md`](README.agents.md) — the manual installed as `.agents/README.md`.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components and data flow.
- [`docs/DISCOVERY.md`](docs/DISCOVERY.md) — workspace inventory and pilot rationale.
- [`docs/TOOLS.md`](docs/TOOLS.md) — selected tools, licenses, why not others.
- [`docs/GAPS.md`](docs/GAPS.md) — residual risks, unverified areas, rollout priorities.
- [`docs/ROLLOUT.md`](docs/ROLLOUT.md) — pilot status, upgrade and rollback.
- [`AGENTS.md`](AGENTS.md) — rules for maintaining the kit.

## Status

This repository contains the implementation and its tests. No claim is made that the kit is
complete, vulnerability-free, or a substitute for review. See `docs/GAPS.md` for the current limits.
