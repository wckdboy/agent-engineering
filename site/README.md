# ADAMANT portal

ADAMANT is a static, dependency-free portal generated from the kit's actual skills, references and configs.
It is both a human handbook and an agent handoff.

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

## Adding content

- Add a skill by creating `skills/<name>/SKILL.md`; the portal picks it up. Update `SKILL_META` in
  `build.py` if it needs a phase, risk level, tags or order.
- Add a tool to `content/tools.json` with a status (`adopted`, `conditional`, `candidate`), a reason
  and a verifiable command. Do not list a tool as adopted until it is installed and exercised.
- Add a build path to `content/paths.json`; every step needs a command, a skill and a completion
  statement.
- Keep repository statuses honest: `green`, `review`, `blocked` or `template`.

## Deploy

The site is plain files. Any static host works. GitHub Pages can deploy the `site/` directory with
the workflow in `.github/workflows/pages.yml`; the workflow rebuilds first so the deployed source
metadata is current.

## Design constraints

- No external fonts, scripts, images or analytics. The portal works offline and leaks no referrer.
- Light and dark themes; keyboard navigation; reduced-motion support; visible focus states.
- No framework or bundler. The build uses Python's standard library; the client is one ES module-free
  script.
- Content is escaped; only the repository-owned skill Markdown is rendered as HTML.

## Custom domain — adamant.cc

GitHub Pages is configured with `cname=adamant.cc`; the site artifact contains `CNAME`. The domain
currently uses Cloudflare nameservers but has **no apex A/AAAA or www CNAME records**, so it does not
resolve yet. Add one of these DNS configurations at Cloudflare:

Recommended (apex A/AAAA, DNS-only, not proxied):

```text
A     @    185.199.108.153
A     @    185.199.109.153
A     @    185.199.110.153
A     @    185.199.111.153
AAAA  @    2606:50c0:8000::153
AAAA  @    2606:50c0:8001::153
AAAA  @    2606:50c0:8002::153
AAAA  @    2606:50c0:8003::153
CNAME www  wckdboy.github.io
```

Or, if Cloudflare CNAME flattening is preferred, use a single apex `CNAME @ -> wckdboy.github.io`
plus the `www` CNAME. Leave the proxy **off** (grey cloud) until GitHub has issued the certificate;
then enable HTTPS enforcement in the Pages settings. A proxied record can work, but it adds an SSL
mode and certificate-validation failure mode that is not needed.

After DNS resolves, verify:

```sh
dig +short adamant.cc
curl -sSI https://adamant.cc/ | head
```

The GitHub Pages API reports `cname: adamant.cc`; certificate state remains empty until the DNS
records exist.
