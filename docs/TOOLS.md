# Tool selection

All versions below were installed and exercised on 2026-10-29 (macOS arm64). Release dates and
licenses were read from the projects' GitHub metadata. The kit calls scanners as separate processes;
it does not link their code.

## Selected

| Tool | Version | Latest release | License | Role | Why it is necessary |
| --- | --- | --- | --- | --- | --- |
| Python standard library | 3.15 (3.11+ target) | — | PSF | CLI, JSON, hashing, subprocess | No install step on a bare runner; no dependency supply chain. |
| git worktrees | 2.55 | — | GPL-2.0 | Isolation | Native, cheap, no extra service; each unit gets a real checkout and branch. |
| ripgrep (`rg`) | 15.2 | — | MIT/Unlicense | Reference search | Fast exact search with ignore handling; fallback to `git grep`. |
| gitleaks | 8.30.1 | 2026-03-21 | MIT | Secret scanning | High-signal, maintained rules; scans a tracked-file tree so build output is excluded. |
| Semgrep CE | 1.182.0 | 2026-10-20 | LGPL-2.1 | SAST | Local and CI, language-aware, custom rules; invoked as a separate executable. |
| OSV-Scanner | 2.7.0 | 2026-10-12 | Apache-2.0 | Dependency vulnerabilities | Uses OSV data; lockfile-driven; no account or vendor agent. |
| actionlint | 1.7.12 | 2026-03-30 | MIT | Workflow correctness | Catches invalid expressions, shell mistakes and known workflow bugs before merge. |
| zizmor (optional) | 1.31.1 not installed | 2026-10-15 | MIT | Workflow security | High-value for `pull_request_target`, permissions and unpinned actions; not adopted until installed, tested and its findings triaged. |

### Why these, not alternatives

- **CodeQL** — strong dataflow analysis, but GitHub-hosted setup, longer runs and a heavier query
  model. Semgrep covers the local loop and the five high-signal rules we can test. CodeQL remains a
  candidate for scheduled deep analysis, not the default gate.
- **Trivy / Grype / Syft** — image, filesystem and SBOM scanners. The pilot has no container image or
  release artifact to scan; OSV covers Rust/Python lockfiles. Revisit when a release pipeline produces
  images or archives.
- **Cosign** — only useful once there is an artifact and a signing policy. Adding it now would be
  ceremony without a verified artifact.
- **ast-grep / tree-sitter / SCIP / LSP** — would improve impact precision, but each adds a parser or
  index to maintain. Current `rg`-based impact is explicitly heuristic and has a caveat. Adopt only
  after measuring false negatives on real changes.
- **Property/fuzz/mutation testing** — valuable per language and per kernel, but not portable
  defaults. They belong in a repository's full profile once a harness and corpus exist.
- **OpenTelemetry / hosted observability** — the evidence JSON is the audit unit. Aggregating metrics
  across repositories is a later need; a collector would add infrastructure without a current
  consumer.
- **Temporal / orchestration frameworks** — the workspace already has `platform/` for runner and
  agent infrastructure. The kit is a library and CLI, not another control plane.

## Installation used in the pilot

```sh
brew install gitleaks semgrep osv-scanner actionlint
```

CI installs pinned versions with `pip` (Semgrep) and `go install` (gitleaks, OSV, actionlint), which
uses the Go checksum database. The standalone workflow pins GitHub Actions to commit SHAs.

## Update policy

1. Read the release notes and license; check for a security advisory.
2. Update the version in `ci/agent-verify.yml` and the local tool expectations in `docs/TOOLS.md`.
3. Re-run `./tests/run.sh` and `./evals/run.py`; confirm the positive fixtures still produce findings
   and the clean fixture stays clean.
4. For a new scanner, add both a positive and a negative fixture before enabling it as required.
5. Keep the previous version in the rollout notes for rollback.

## Licensing notes

- Semgrep CE is LGPL-2.1. The kit invokes the installed `semgrep` executable; it does not import,
  link or vendor it. Distributing the kit does not distribute Semgrep.
- gitleaks (MIT), OSV-Scanner (Apache-2.0) and actionlint (MIT) are permissive.
- Git is GPL-2.0; the kit invokes it as a separate program.
- No new dependency was added to any product repository by this work.
