# Changelog

The kit is installed into repositories and versioned as data: `.agents/VERSION` reports the
release an installed copy came from. Behaviour changes that affect what a gate proves are listed
here, one line per change, with the release that first shipped it.

## 1.0.1

- **osv-scanner runs inside worktrees.** The recursive source scan honours `.gitignore`, and every
  repository using the kit ignores `.worktrees/`, so a worktree checkout was invisible to the walk
  and `eng security` reported `no package sources` — a silent skip exactly where parallel work
  happens. When the walk finds nothing, the known lockfiles are now named explicitly. The walk
  stays the first pass, so inputs outside the lockfile list (SBOMs, `pom.xml`, `bun.lock`) keep
  being scanned in a primary checkout. `-L` arguments carry a leading `:` so a path containing a
  colon is never read as an inline parser type.
- **`install.sh` reads `VERSION`** instead of hardcoding it, so an installed copy cannot report a
  release it is not.

## 1.0.0

- First release: `eng` CLI (detect, init, verify, impact, security, audit-actions, artifact,
  release-check, guard, evidence, worktree, doctor), ten task skills, hash-chained evidence,
  isolated worktrees, hooks and the CI template.
