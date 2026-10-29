# Architecture

The kit has one executable surface (`bin/eng` → `lib/eng.py`), one configuration file per repository
(`.agents/engineering.json`), one evidence chain, and a set of Markdown skills that call the CLI. It
has no daemon, database or model dependency.

## Components

```text
AGENTS.md ─────────────┐
.agents/skills/* ──────┼──> agent chooses a workflow
.agents/engineering.json ──> eng verify/security/impact
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
          commands        scanners         git worktrees
              │               │                │
              └───────────────┴────────────────┘
                              ▼
                    .agents/evidence/<id>.json
                    .agents/evidence/index.jsonl
                              │
                              ▼
                     CI artifact / reviewer
```

### CLI

- `detect` builds a file-based inventory: stacks, manifests, modules, tests, CI run commands,
  interface candidates, ownership. It does not parse a full build graph; the limits are printed.
- `impact` diffs against a base, extracts symbols with per-language regexes, searches references with
  `rg` (fallback `git grep`), marks tests and contract surfaces. It is a checklist, not proof.
- `verify` runs the configured commands sequentially, then required/optional scanners in the full
  profile, and writes one evidence record. Exit codes: `0` pass, `1` fail, `2` blocked.
- `security` runs gitleaks (tracked-file tree), Semgrep (repository rules), OSV-Scanner (lockfiles),
  actionlint (workflows) and zizmor (when installed). Findings fail; missing required tools block.
- `guard` is an offline pre-commit backstop: high-signal credential patterns, sensitive file names,
  merge markers and oversize files. It is intentionally narrower than gitleaks.
- `worktree` creates `.worktrees/<name>` on `eng/<name>`, records the owner, refuses dirty trees by
  default, caps concurrency, and refuses dirty removal without `--force`.
- `evidence` recomputes content hashes and verifies the previous-hash chain.

### Configuration

`.agents/engineering.json` is reviewed code, not untrusted input. It names exact commands, timeouts,
required/optional scanners and the worktree cap. Changing it is a security-relevant change: a
malicious PR can alter the commands CI runs. The existing CI already trusts repository scripts, so
this does not add a new class of trust, but it must be reviewed like CI.

### Evidence

Each record contains the exact command, exit code, duration, output hash, log path, git state, config
hash and scanner versions. `index.jsonl` links each record to the previous hash. This detects
accidental or casual tampering; it does **not** prove authenticity against someone who can rewrite
the whole chain. CI artifact provenance is the external trust anchor.

The schema is versioned (`eng-evidence/v1`). Records are local and gitignored; CI uploads them. A
reviewer can run `eng evidence verify` and read the failing log without trusting a summary.

### Isolation

Worktrees are native git. The CLI does not copy uncommitted changes; it refuses a dirty tree unless
`--allow-dirty` is explicit. It records an owner from `ENG_OWNER`/`USER`, enforces
`parallel.max_worktrees`, and leaves the branch after removal so work is not lost silently.

### Failure model

- Missing config or command → `blocked`, not pass.
- Missing required scanner → `blocked`.
- Scanner findings → `fail`.
- Optional scanner skipped → `unverified`, listed in the record.
- Dirty tree → recorded; the evidence describes the working tree, not a commit.
- Timeout → process group killed, status `timeout`, recorded as a failure.
- Tool crash/no report → `error`, not pass.

## Portability

- Python 3.11+ standard library; git; optional `rg`, `jq`, scanners.
- macOS and Linux (the evidence index uses `fcntl`). Windows is not supported.
- Harness-agnostic: `AGENTS.md` for Codex/OpenCode-style readers, `.claude/skills` and
  `.opencode/skills` symlinks for those harnesses, and the plain CLI for anything else.
- The installer copies files; there is no runtime link to the source kit, so a repository remains
  usable if the kit directory moves.

## What is deliberately absent

No microservice, queue, database, container runtime, LSP server, tree-sitter parser, or model router.
Each would add operational surface without a measured need at this scale. The gaps are recorded in
`GAPS.md`, not hidden behind abstractions.
