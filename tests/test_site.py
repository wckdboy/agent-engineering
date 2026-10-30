"""Tests for the generated Agent Engineering portal."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import unittest
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
