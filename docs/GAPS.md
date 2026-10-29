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
| ADAMANT portal tests | 9 tests, 0.4 s, all pass |
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
13. **Only the pilot's CI has run.** `sovware` run 40944146737 (and the follow-up 40946781919) passed
    on GitHub and uploaded evidence. `polykrom` and `platform` changes are on local review branches
    and have not been pushed or run by their CI. The kit's own CI has not run on GitHub.
14. **Action pinning is uneven.** The kit template, `sovware`, and `platform` pin actions by SHA;
    `platform` runs zizmor and `eng audit-actions`. `polykrom` still has some upstream floating
    references, and the WCKDai organization policy does not require SHA pinning (the read-only
    platform audit reports this). Changing that policy is an owner decision.
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

## Rollout findings (2026-10-29)

- **sovware** — two GitHub Actions runs passed (`40944146737`, `40946781919`); the full job installed
  scanners, ran the full gate and uploaded `.agents/evidence/`. Local warm fast/full: 0.8 s / 5–6 s.
- **polykrom** — `eng detect` 1.8 s; fast profile 22 s after the io test binary was built; contract
  fixture `legacy-solvecraft-v1.solidcraft` loads and is re-tagged on save. Gitleaks and Semgrep are
  clean after narrow, documented false-positive suppressions. OSV reports **15 dependency advisories**
  (cgmath, proc-macro-error, rustls-webpki, tokio, ttf-parser, webpki-root-certs, zip, zbus_names,
  zvariant and transitive packages); the authoritative full `cargo xtask ci` was not run.
- **platform** — fast 0.5 s, full 3.2 s; all 9 action references are pinned; zizmor and actionlint
  report no findings. `audit-config.sh` still fails the organization-level "require SHA-pinned
  actions" check; that is outside the repository.
- **kit** — 33 tests, 9/9 control checks, agent stub 2/2, no-op 0/2; release-check and artifact
  hashing have positive and failure fixtures.

## Rollout priorities

1. **Polykrom.** Triage the 15 OSV advisories (upgrade, patch or a dated owner risk acceptance);
   run the authoritative `cargo xtask ci`; push `eng/portable-controls` as a PR. The fast gate and
   contract fixture are already verified locally.
2. **Platform.** Get the organization's "require SHA-pinned actions" policy enabled by the owner;
   push `eng/portable-controls` and confirm the new quality workflow. `audit-config.sh` should join
   the full profile when org access is available.
3. **Release artifacts.** Use `eng release-check` on the first real artifact; add SBOM/signature/
   provenance verification rather than only recording their hashes.
4. **Language breadth.** Add Node/TypeScript, Swift/macOS and Kotlin profiles; measure each fast gate
   instead of copying Rust commands.
5. **Metrics.** Export evidence summaries to a small local index and track accepted changes, escaped
   regressions, median/tail latency and failed integrations. Keep the raw records.
