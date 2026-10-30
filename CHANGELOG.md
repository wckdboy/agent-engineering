# Changelog

## 1.1.1 — 2026-10-30

- `security.osv_lockfile` lets a repository with historical nested vendor lockfiles scan only
  the workspace lockfile that is actually built.
- Record the Polykrom #281 merge, the open #282/#287 quality and security PRs, and PolyCore PR
  #28 on the ADAMANT repository status.
- No product behavior change; site and release artifact stay in sync.


## 1.1.0 — 2026-10-30

- ADAMANT portal generated from the kit, with `agents.json`, `llms.txt`, a skill explorer,
  build paths, a tool catalog, a hash-chained evidence model and a downloadable kit.
- `eng perf-check` and a release performance gate: higher/lower-is-better metrics are compared
  with an accepted baseline; a regression beyond the tolerance blocks the release.
- `eng release-check` now records and enforces performance alongside clean HEAD, full evidence,
  version, notes, rollback and artifact hashes.
- `eng audit-actions` requires full commit-SHA pins; the kit and pilot workflows are pinned.
- Node 24 action releases for checkout, setup-python and upload-artifact.
- Expanded Semgrep rules for `os.system`, `pickle.loads` and `execSync`, with positive and
  negative fixtures.

## 1.0.1 — 2026-10-29

- OSV scans inside worktrees; `install.sh` reads `VERSION`.
