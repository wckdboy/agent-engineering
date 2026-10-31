# CREED — creed.sh

CREED is a static, dependency-free portal generated from the kit's actual skills, references and configs.
It is both a human handbook and an agent handoff.

Canonical agent entrypoint: <https://creed.sh/creed.md>. The former ADAMANT domains redirect to
Creed. The CLI, schemas, skill frontmatter and download paths are unchanged.

## Run locally

```sh
cd engineering
python3 site/build.py
cd site && python3 -m http.server 8080
```

Open <http://localhost:8080>. Opening `index.html` directly with `file://` will not work because the
UI fetches `data/site.json`; the error message tells you to serve the directory.

## What is generated

| Output | Purpose |
| --- | --- |
| `data/site.json` | Full UI payload: phases, principles, skill bodies, tools, paths, repositories, limits |
| `data/skills.json` | Raw skill records for agents |
| `data/tools.json` | Capability catalog |
| `agents.json` | Machine-readable entrypoint, start commands and compact catalog |
| `llms.txt` | Compact text brief for an agent with no UI |
| `creed.md` | Values, lifecycle, trust boundaries and raw skill URLs |
| `skills/*/SKILL.md`, `references/*.md` | Byte-identical authoritative sources |
| `docs/*.html` | Rendered operating manual, evidence reference and gap register |
| `downloads/eng-kit.zip` | Installable kit with a SHA-256 manifest |
| `downloads/manifest.json` | Zip digest, size and file list |

The build is deterministic for a given source tree. The zip uses fixed timestamps and sorted entries,
so a rebuild does not produce meaningless binary churn.

## Source of truth

- Skills: `../skills/*/SKILL.md` (frontmatter, activation and body are parsed directly).
- Tool catalog: `content/tools.json`.
- Lifecycle: `content/phases.json`.
- Principles: `content/principles.json`.
- Guardrails: `content/guardrails.json`.
- Build paths: `content/paths.json`.
- Repository status: `content/repos.json`.

Do not edit `data/`, `agents.json`, `llms.txt`, `docs/` or `downloads/` by hand. Edit the source and
rebuild. A test (`tests/test_site.py`) checks determinism, local links, the machine handoff and the
download manifest.

Browser regression checks use an existing Chrome and `playwright-core` installation (no runtime
dependency is added to the site):

```sh
PLAYWRIGHT_MODULE=/absolute/path/to/playwright-core/index.mjs node tests/test_browser.mjs
```

Set `CHROME_BIN` for another Chrome/Chromium executable and `QA_SHOTS` for screenshots. The check
covers both themes at seven widths, including the tablet navigation boundary, readable skip links
and code blocks, inline-link cues, documentation overflow and skill-dialog dismissal. It is a
separate browser gate, not a claim that the Python suite performs browser testing.

## Adding content

- Add a skill by creating `skills/<name>/SKILL.md`; the portal picks it up. Update `SKILL_META` in
  `build.py` if it needs a phase, risk level, tags or order.
- Add a tool to `content/tools.json` with a status (`adopted`, `conditional`, `candidate`), a reason
  and a verifiable command. Do not list a tool as adopted until it is installed and exercised.
- Add a build path to `content/paths.json`; every step needs a command, a skill and a completion
  statement.
- Keep repository statuses honest: `green`, `review`, `blocked` or `template`. They describe a
  recorded observation, **not live CI**. Keep summaries and release/issue claims in the past tense.

### Repository provenance

`content/repos.json` accepts two optional fields per repository without changing the
`agent-engineering-site/v1` schema or existing status values:

```json
"last_observed": "2026-10-30",
"evidence_links": [
  {"label": "Recorded run 123", "url": "https://example.org/actions/runs/123"}
]
```

`last_observed` is an author-recorded calendar date (`YYYY-MM-DD`), not the site build date or an
automatically determined CI timestamp. Omit it when unknown; do not infer it from a content edit.
Undated historical rollout records stay undated; a newer measured baseline may supply its own
observation date. The dated PolyCore baseline was measured during alpha verification, not fetched
by the portal, and covers only the named fast checks on its linked source revision.
Prefer specific run, commit, artifact or review links, not a mutable "latest" badge. A linked PR or
rollout note is context for the recorded claim, not proof that a check passed or remains green.

Links require a nonempty text label and an absolute HTTPS URL with a plain hostname or IP address,
an optional valid port, and no credentials, whitespace, control characters or backslashes. The
builder rejects invalid provenance before writing generated output; the UI ignores malformed
optional values if a payload bypasses the builder. Labels and URLs are HTML-escaped. Legacy records
still render with "Last observed: not recorded" and "No linked evidence recorded" when absent.
An empty `evidence_links` array is also valid. These fields are copied into `data/site.json` and `agents.json` and
included in its existing content hash; no source-integrity rules are changed.

The portal never fetches evidence links, checks their availability, or polls CI. It remains static
and offline-capable; only a user following a link contacts its host. Opened evidence links use
`noopener noreferrer`. Verification of their content, retention and access permissions is external.

Dependency-free renderer checks run via `python3 -m unittest tests.test_site -v` when Node is on
`PATH`, or directly with `node --test tests/test_repos.mjs` after a build. They check legacy payloads,
dated evidence, escaping, unsafe/malformed values and the absence of evidence-network requests.

## Design constraints

- No external fonts, scripts, images or analytics. The portal works offline and leaks no referrer.
- Light and dark themes; keyboard navigation; reduced-motion support; visible focus states.
- No framework or bundler. The build uses Python's standard library; the client is one ES module-free
  script.
- Content is escaped; only the repository-owned skill Markdown is rendered as HTML.

## Hosting — Cloudflare Workers

The portal is deployed with Wrangler as a Workers static-assets project. `wrangler.jsonc` points at
`site/` and attaches the canonical and legacy custom domains. `worker.mjs` runs before static
assets, redirecting only exact legacy hosts and `www.creed.sh` to `https://creed.sh`, with HTTP 308:

```jsonc
"name": "adamant",
"main": "worker.mjs",
"assets": { "directory": "site", "binding": "ASSETS", "run_worker_first": true },
"routes": [
  { "pattern": "creed.sh", "custom_domain": true },
  { "pattern": "www.creed.sh", "custom_domain": true },
  { "pattern": "adamant.cc", "custom_domain": true },
  { "pattern": "www.adamant.cc", "custom_domain": true }
]
```

Deploy:

```sh
python3 site/build.py
./tests/run.sh
npx wrangler deploy --dry-run
npx wrangler deploy
```

Keep the worker name `adamant` to preserve its deployment identity. Wrangler attaches the custom
domains; verify DNS, TLS, agent endpoints and redirects live, not only against a local cache:

```sh
dig +short @1.1.1.1 creed.sh
curl -sSI https://creed.sh/creed.md
curl -sSI 'https://adamant.cc/skills/repo-intelligence/SKILL.md?from=agent'
```

`site/CNAME` is intentionally absent: GitHub Pages is not the host. If a local resolver still returns
NXDOMAIN after the records exist, flush it or wait for the negative-cache TTL; `@1.1.1.1` and the
Cloudflare DoH endpoint are authoritative for propagation checks.

## Raw agent endpoints

These are static files; no client JavaScript or model provider is required:

```text
https://creed.sh/creed.md
https://creed.sh/agents.json
https://creed.sh/llms.txt
https://creed.sh/skills/repo-intelligence/SKILL.md
https://creed.sh/data/tools.json
https://creed.sh/downloads/eng-kit.zip
```

Rollback: redeploy the previous Wrangler version; keep both old-domain routes attached. The agent
entrypoint and raw routes are additive; old JSON schemas and package paths remain valid.

The visual authority is WCKD's `autobot-www/brand/kit.json` and `brand/web.css`. `assets/brand.css`
adapts the handbook layout without changing its search, filters, dialogs or raw endpoints.
