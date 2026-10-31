"""Tests for the generated Agent Engineering portal."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SITE = KIT / "site"
DATA = SITE / "data" / "site.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    res = subprocess.run(["python3", str(SITE / "build.py")], capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        raise AssertionError(res.stdout + res.stderr)


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("portal_build", SITE / "build.py")
        cls.portal = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.portal)
        build()

    def test_generated_skills_are_complete(self):
        data = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "agent-engineering-site/v1")
        self.assertEqual(len(data["skills"]), 10)
        for skill in data["skills"]:
            self.assertTrue(skill["name"])
            self.assertTrue(skill["description"])
            self.assertIn("<h2>", skill["body_html"], skill["id"])
            self.assertNotIn("<h1>", skill["body_html"])
            self.assertNotIn("---\nname:", skill["body_html"])
            self.assertTrue(skill["activate"])
            self.assertFalse(skill["activate"].startswith("- "))
            self.assertTrue((KIT / skill["source_path"]).exists())

    def test_multi_line_numbered_steps_render_one_ordered_list(self):
        data = json.loads(DATA.read_text(encoding="utf-8"))
        security = next(s for s in data["skills"] if s["id"] == "security-auditor")
        workflow = security["body_html"].split("<h2>Workflow</h2>", 1)[1]
        self.assertEqual(workflow.count("<ol"), 1)
        self.assertEqual(workflow.split("</ol>", 1)[0].count("<li>"), 7)

    def test_handoff_files_and_commands(self):
        agents = json.loads((SITE / "agents.json").read_text(encoding="utf-8"))
        self.assertEqual(agents["schema"], "agent-engineering/v1")
        self.assertIn("AGENTS.md", agents["start"]["read_first"])
        self.assertIn("eng verify --profile fast", agents["start"]["fast"])
        self.assertEqual(len(agents["skills"]), 10)
        self.assertGreaterEqual(len(agents["tools"]), 20)
        self.assertTrue(agents["limits"])
        llms = (SITE / "llms.txt").read_text(encoding="utf-8")
        for skill in agents["skills"]:
            self.assertIn(f"### {skill['id']}", llms)
        self.assertIn("## Commands", llms)
        self.assertIn("## Limits", llms)

    def test_creed_canonical_and_agent_entrypoint(self):
        data = json.loads(DATA.read_text(encoding="utf-8"))
        agents = json.loads((SITE / "agents.json").read_text(encoding="utf-8"))
        self.assertEqual(data["title"], "CREED")
        self.assertEqual(data["homepage"], "https://creed.sh")
        self.assertEqual(agents["creed"], "https://creed.sh/creed.md")
        text = (SITE / "creed.md").read_text(encoding="utf-8")
        for principle in data["principles"]:
            self.assertIn(principle["title"], text)
            for point in principle["points"]:
                self.assertIn(point, text)
        for guardrail in data["guardrails"]:
            self.assertIn(guardrail["body"], text)
        self.assertIn("repository's authoritative policy", text)
        self.assertIn("## Understand", text)
        self.assertIn("https://creed.sh/data/tools.json", text)
        html = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn('rel="canonical" href="https://creed.sh/"', html)
        self.assertIn('href="./creed.md"', html)

    def test_raw_agent_sources_match_authoritative_files(self):
        agents = json.loads((SITE / "agents.json").read_text(encoding="utf-8"))
        for skill in agents["skills"]:
            self.assertEqual(skill["raw_url"], f"https://creed.sh/{skill['source']}")
            self.assertEqual((SITE / skill["source"]).read_bytes(), (KIT / skill["source"]).read_bytes())
        for reference in (KIT / "references").glob("*.md"):
            self.assertEqual((SITE / "references" / reference.name).read_bytes(), reference.read_bytes())

    def test_rebuild_removes_deleted_and_renamed_raw_sources(self):
        spec = importlib.util.spec_from_file_location("portal_build", SITE / "build.py")
        portal = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(portal)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "site"
            (root / "references").mkdir()
            (root / "references/current.md").write_text("current policy\n")
            (output / "references").mkdir(parents=True)
            (output / "references/deleted.md").write_text("obsolete policy\n")
            (output / "skills/renamed").mkdir(parents=True)
            (output / "skills/renamed/SKILL.md").write_text("obsolete skill\n")
            skill = {"id": "current", "source_path": "skills/current/SKILL.md",
                     "description": "current skill", "raw_markdown": "current skill\n"}
            with patch.object(portal, "ROOT", root), patch.object(portal, "SITE", output):
                portal.build_creed([], [], [], [skill], {})
                self.assertFalse((output / "references/deleted.md").exists())
                self.assertFalse((output / "skills/renamed/SKILL.md").exists())
                self.assertEqual((output / "references/current.md").read_text(), "current policy\n")
                self.assertEqual((output / skill["source_path"]).read_text(), skill["raw_markdown"])
                (root / "references/current.md").unlink()
                portal.build_creed([], [], [], [], {})
                self.assertFalse((output / "references/current.md").exists())
                self.assertFalse((output / skill["source_path"]).exists())

    def test_legacy_redirects_preserve_path_and_query(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        res = subprocess.run([node, "--test", str(KIT / "tests" / "test_worker.mjs")], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_paths_and_repositories_are_usable(self):
        data = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(len(data["paths"]), 8)
        for path in data["paths"]:
            self.assertGreaterEqual(len(path["steps"]), 4, path["id"])
            for step in path["steps"]:
                self.assertTrue(step["commands"], f"{path['id']}: {step['title']} has no command")
                self.assertTrue(step["skills"], f"{path['id']}: {step['title']} has no skill")
                self.assertTrue(step["done"])
        statuses = {repo["status"] for repo in data["repos"]}
        self.assertTrue({"green", "review", "template"}.issubset(statuses))

    def test_repository_provenance_is_optional_and_preserved_in_data(self):
        repos = json.loads((SITE / "content/repos.json").read_text())
        legacy = {k: v for k, v in repos[0].items() if k not in ("last_observed", "evidence_links")}
        observed = dict(legacy, id="observed", last_observed="2026-10-30", evidence_links=[
            {"label": "Recorded run", "url": "https://example.org/actions/runs/123?job=4&attempt=1"},
        ])
        fixtures = [legacy, observed]
        read_json = self.portal.read_json
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with patch.object(self.portal, "SITE", output), \
                    patch.object(self.portal, "DOWNLOADS", output / "downloads"), \
                    patch.object(self.portal, "read_json", side_effect=lambda name: fixtures if name == "repos.json" else read_json(name)):
                self.portal.main()
            data = json.loads((output / "data/site.json").read_text())
            self.assertEqual(data["schema"], "agent-engineering-site/v1")
            self.assertEqual(data["repos"], fixtures)
            agents = json.loads((output / "agents.json").read_text())
            self.assertEqual(agents["schema"], "agent-engineering/v1")
            self.assertEqual(agents["repos"], fixtures)
            self.assertIn("Recorded observations, not live CI", (output / "llms.txt").read_text())
            self.assertTrue(any("not live CI" in limit for limit in data["limits"]))
            # Provenance participates in the same content hash as the original fields.
            payload = {key: data[key] for key in ("skills", "tools", "paths", "principles", "phases", "guardrails", "repos")}
            self.assertEqual(data["source"]["content_sha256"],
                             hashlib.sha256(self.portal.canonical(payload).encode()).hexdigest())
            payload["repos"][1]["last_observed"] = "2026-10-29"
            self.assertNotEqual(data["source"]["content_sha256"],
                                hashlib.sha256(self.portal.canonical(payload).encode()).hexdigest())

    def test_repository_provenance_rejects_invalid_dates_and_links(self):
        for value in ("2026-02-30", "2026-1-01", "20261030", "", None, 20261030):
            with self.subTest(last_observed=value), self.assertRaisesRegex(ValueError, "last_observed"):
                self.portal.validate_repo_provenance([{"id": "fixture", "last_observed": value}])
        for value in ("javascript:alert(1)", "http://example.org/run", "//example.org/run",
                      "/run", "https:///run", "https://", "https://[invalid", "https://example.org:bad/run",
                      "https://example.org:99999/run", "https://user:pass@example.org/run", "https://@example.org/run",
                      "https://example.org\\@evil.invalid/run", "https://example.org/\nrun", "https://exa mple.org/run",
                      "https://example.org/\x00run", "https://999.999.999.999/run", None, 123):
            with self.subTest(url=value), self.assertRaisesRegex(ValueError, "evidence_links"):
                self.portal.validate_repo_provenance([{"id": "fixture", "evidence_links": [{"label": "Run", "url": value}]}])
        for value in ("https://127.0.0.1/run", "https://192.0.2.1:8443/run", "https://[2001:db8::1]/run"):
            with self.subTest(url=value):
                self.portal.validate_repo_provenance([{"id": "fixture", "evidence_links": [{"label": "Run", "url": value}]}])
        for value in (None, "https://example.org/run", {}, [None], [{"url": "https://example.org/run"}],
                      [{"label": " ", "url": "https://example.org/run"}], [{"label": 123, "url": "https://example.org/run"}]):
            with self.subTest(evidence_links=value), self.assertRaisesRegex(ValueError, "evidence_links"):
                self.portal.validate_repo_provenance([{"id": "fixture", "evidence_links": value}])

    def test_repository_cards_render_provenance(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        res = subprocess.run([node, "--test", str(KIT / "tests/test_repos.mjs")], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_local_links_exist(self):
        text = (SITE / "index.html").read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("#", "http://", "https://", "mailto:", "data:")):
                continue
            path = href.split("#", 1)[0].split("?", 1)[0]
            if path:
                self.assertTrue((SITE / path).exists(), f"missing link target: {href}")

    def test_no_external_assets(self):
        html = (SITE / "index.html").read_text(encoding="utf-8")
        css = (SITE / "assets" / "styles.css").read_text(encoding="utf-8")
        js = (SITE / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertNotRegex(html, r'<script[^>]+src="https?://')
        self.assertNotRegex(html, r'<link(?![^>]*\brel="canonical")[^>]+\bhref="https?://')
        self.assertNotIn("url(http", css)
        self.assertNotIn("@import url(http", css)
        self.assertNotIn("fetch(\"http", js)

    def test_javascript_syntax(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        res = subprocess.run([node, "--check", str(SITE / "assets" / "app.js")], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_download_kit_is_complete_and_clean(self):
        zip_path = SITE / "downloads" / "eng-kit.zip"
        self.assertTrue(zip_path.exists())
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            self.assertIn("eng-kit/install.sh", names)
            self.assertIn("eng-kit/lib/eng.py", names)
            self.assertIn("eng-kit/AGENTS.md", names)
            self.assertIn("eng-kit/MANIFEST.sha256", names)
            self.assertEqual(sum(1 for n in names if n.endswith("/SKILL.md")), 10)
            self.assertFalse(any("__pycache__" in n or n.endswith(".pyc") for n in names))
            self.assertFalse(any(".agents/evidence" in n for n in names))
            self.assertFalse(any(n.startswith("eng-kit/site/") for n in names))
            manifest = zf.read("eng-kit/MANIFEST.sha256").decode()
            for line in manifest.splitlines()[:5]:
                digest, name = line.split("  ", 1)
                self.assertEqual(hashlib.sha256(zf.read(name)).hexdigest(), digest)
            for name in ("eng-kit/install.sh", "eng-kit/bin/eng", "eng-kit/hooks/pre-commit"):
                info = zf.getinfo(name)
                self.assertTrue((info.external_attr >> 16) & 0o111, f"{name} is not executable")

    def test_build_is_deterministic(self):
        files = [SITE / "data" / "site.json", SITE / "agents.json", SITE / "llms.txt",
                 SITE / "downloads" / "manifest.json", SITE / "downloads" / "eng-kit.zip",
                 SITE / "docs" / "README.agents.html", SITE / "creed.md",
                 SITE / "skills" / "repo-intelligence" / "SKILL.md"]
        before = {str(p): sha(p) for p in files}
        build()
        after = {str(p): sha(p) for p in files}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
