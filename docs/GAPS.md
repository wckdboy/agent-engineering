# Gaps and residual risk

This is an honest inventory. A green `eng verify` means the configured checks ran and passed; it is
not a proof of correctness or security.

## Measured baseline (2026-10-29)

| Measurement | Result |
| --- | --- |
| Pilot (`sovware`) tracked files | 48 |
| Pilot baseline `./scripts/check.sh` | pass, 3.18 s |
| Pilot fast profile | pass, 3.24 s (fmt, clippy, test) |
| Pilot full profile | pass, 5–7 s (check, gitleaks, Semgrep, OSV, actionlint) |
| Kit unit/integration tests | 33 tests, 14.6 s, all pass |
| Control evaluation | 9/9 evaluated checks pass (known-bad fails; fixed passes; planted secret/SAST found; clean passes) |
| Agent harness, deterministic stub | 2/2 tasks pass, 0.93 s |
| Agent harness, no-op agent | 0/2 tasks pass (scoring rejects a non-change) |
| Skills | 10, each with frontmatter and required sections |

## Not implemented / not verified

1. **Build-graph impact.** `eng impact` is textual. Dynamic dispatch, reflection, generated clients and
   external consumers can be missed. No LSP/SCIP/tree-sitter index is used.
2. **Deep SAST.** Eight Semgrep rules cover shell injection, disabled TLS, unsafe YAML, unsafe
   pickle, shell wrappers, `execSync` and `os.system`. No dataflow, taint tracking or CodeQL. Every
   rule has a positive and negative fixture; rules still need expansion with tests.
3. **Secret history.** `gitleaks_history` is `false` in the pilot. The working tree is scanned, not
   every historical commit. Enable per repository after measuring history size; CI checks out full
   history but the scanner is configured for tracked files.
4. **Untracked files.** gitleaks scans tracked files. The pre-commit guard scans staged files. A new
   untracked file with a secret is not scanned until staged.
5. **Dependency coverage.** OSV needs a supported lockfile and network. "No package sources" is
   skipped, not passed. Transitive resolution may differ from the build's resolver.
6. **Artifact security.** `release-check` records supplied artifact, SBOM, signature and provenance
   hashes, but it does not generate an SBOM, verify a signature or produce an attestation. No
   container scan; the pilot produces no release artifact. Cosign/Syft/Trivy remain deferred.
7. **Performance baselines.** The kit records command durations but no benchmark suite or historical
   performance trend. `performance-engineer` defines the method; it has not been exercised on a hot
   path.
8. **Property/fuzz/mutation testing.** No harness or corpus is included. These are repository- and
   language-specific and should be added to full profiles where they pay off.
9. **Platform coverage.** macOS and Linux only. The evidence index uses `fcntl`; Windows is not
   supported.
10. **Evidence authenticity.** Hash chaining detects accidental or casual edits, not a determined
    rewrite of the whole chain. CI artifact retention and branch protection are the external anchors.
    Evidence is not signed.
11. **Ownership enforcement.** `eng worktree` records an owner and caps concurrency, but cannot stop a
    separate process from editing the same files. Integration remains a human/agent discipline.
12. **Hooks are bypassable.** `git commit --no-verify` skips the guard. CI is the enforcement point.
13. **CI has not run on GitHub.** `sovware`'s workflow was edited and validated with local
    `actionlint`; the scanner install commands were exercised locally with Go 1.27.3 and Python
    3.12-compatible Semgrep, and the full gate was run with those binaries on `PATH`. The job itself
    has not executed on a GitHub runner.
14. **Action pinning is uneven.** The kit template pins SHAs, and the pilot's checkout, Rust
    toolchain, cache, setup-python and upload steps are now pinned. Other repositories and the
    vendored actions in some workflows remain unpinned. zizmor was not installed or run; triage it
    before claiming supply-chain hardening.
15. **Agent evaluation is a smoke test.** Two tasks, one deterministic stub and one no-op check. It is
    not a model benchmark, has no statistical power, and does not capture provider cost.
16. **Harness discovery is lightly tested.** The installer creates `.claude/skills` and
    `.opencode/skills` symlinks and an `AGENTS.md` section, but activation was not exercised inside
    each harness. A harness that does not follow directory symlinks would need a copy instead.
17. **Config trust.** `.agents/engineering.json` commands run with CI privileges. A malicious PR can
    change them. Review the config like CI; do not run the kit on untrusted forks with production
    secrets.
18. **No cross-repository metrics store.** Each repository has its own evidence chain. Aggregating
    pass rate, cost, latency and escaped regressions across the workspace is a later step.

## Rollout priorities

1. **Pilot follow-up (sovware).** Push the branch and confirm the new CI job on GitHub. Fix any
   runner/tool installation mismatch. Decide on history scanning and pin the existing actions.
2. **Large-repo validation (polykrom).** Time `detect`, `impact`, `gitleaks` and Semgrep on the 7.3 GB
   tree; confirm `target/` is excluded. Add contract fixtures for the design format and CLI. Add a
   kernel-focused full profile.
3. **Infrastructure repo (platform).** Add zizmor/actionlint gates and pin workflow actions. Use the
   kit to evidence config changes; do not put credentials in the repository.
4. **Language breadth.** Add Node/TypeScript (`autobot-www`), Swift/macOS (`Mosaic`, `omnie-*`) and
   Kotlin (`autobot`) command profiles. Measure whether a shared fast profile is meaningful or each
   repo needs its own.
5. **Release path.** Once an artifact exists, add SBOM, signature verification and a release-verifier
   checklist bound to the artifact digest.
6. **Metrics.** Export evidence summaries to a small local index (not a SaaS) and track accepted
   changes, escaped regressions, median/tail latency and failed integrations. Keep the raw records.
