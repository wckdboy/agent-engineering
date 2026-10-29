"""Integration tests for the eng kit. Each test builds a disposable git repository."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
ENG = KIT / "bin" / "eng"
CONFIGS = KIT / "configs"


def run(cmd, cwd, timeout=180):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


def eng(root, *args, timeout=180):
    return run([str(ENG), "--root", str(root), *args], cwd=root, timeout=timeout)


class Repo:
    def __init__(self, root: Path):
        self.root = root

    def git(self, *args):
        res = run(["git", *args], cwd=self.root)
        if res.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed: {res.stderr}")
        return res

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content), encoding="utf-8")

    def init(self):
        self.git("init", "-q")
        self.git("config", "user.email", "eng@example.invalid")
        self.git("config", "user.name", "eng test")
        self.git("add", "-A")
        self.git("commit", "-qm", "fixture")

    def stage(self, *names):
        self.git("add", *names)


class EngTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eng-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = Repo(self.tmp)

    def install_config(self, commands, security=None, parallel=None):
        cfg = {
            "schema": "eng-config/v1",
            "project": "fixture",
            "commands": commands,
            "security": security or {"required": [], "optional": []},
            "parallel": parallel or {"max_worktrees": 2},
        }
        self.repo.write(".agents/engineering.json", json.dumps(cfg, indent=2))
        (self.tmp / ".agents" / "config").mkdir(parents=True, exist_ok=True)
        for name in ("semgrep.yml", "gitleaks.toml", "guard-allow.txt"):
            shutil.copy2(CONFIGS / name, self.tmp / ".agents" / "config" / name)

    def init_basic(self):
        self.repo.write("Makefile", "check:\n\t@true\n")
        self.repo.write("src/lib.py", "def add(a, b):\n    return a + b\n")
        self.repo.write("tests/test_lib.py", "from src.lib import add\n\ndef test_add():\n    assert add(1, 2) == 3\n")
        self.repo.init()
        self.install_config({"fast": [{"name": "check", "run": "make check"}],
                             "full": [{"name": "check", "run": "make check"}]})
        self.repo.git("add", "-A")
        self.repo.git("commit", "-qm", "config")


class DetectTests(EngTestCase):
    def test_detects_python_and_tests(self):
        self.init_basic()
        res = eng(self.tmp, "detect", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertIn("Python", [s["language"] for s in data["stacks"]])
        self.assertGreaterEqual(data["tests"]["count"], 1)
        self.assertIn("check", data["build"]["make_targets"])
        self.assertTrue(data["git"]["present"])

    def test_non_git_directory_still_inventories(self):
        self.repo.write("src/lib.py", "print('x')\n")
        res = eng(self.tmp, "detect", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertFalse(data["git"]["present"])
        self.assertEqual(data["file_count"], 1)


class GuardTests(EngTestCase):
    def test_detects_staged_secret(self):
        self.repo.write("clean.py", "print('ok')\n")
        self.repo.init()
        self.repo.write("leak.py", 'KEY = "AKIAQ7Z2X4M9P1L8V3N6"\n')
        self.repo.stage("leak.py")
        res = eng(self.tmp, "guard", "staged")
        self.assertEqual(res.returncode, 1, res.stdout)
        self.assertIn("aws-access-key", res.stdout)

    def test_clean_staged_files_pass(self):
        self.repo.write("clean.py", "print('ok')\n")
        self.repo.init()
        self.repo.write("second.py", "print('second')\n")
        self.repo.stage("second.py")
        res = eng(self.tmp, "guard", "staged")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_sensitive_filename_blocks(self):
        self.repo.write("README.md", "x\n")
        self.repo.init()
        self.repo.write(".env", "TOKEN=not-a-real-token\n")
        self.repo.stage(".env")
        res = eng(self.tmp, "guard", "staged")
        self.assertEqual(res.returncode, 1)
        self.assertIn("sensitive-file", res.stdout)

    def test_allowlist_is_path_scoped(self):
        self.repo.write("README.md", "x\n")
        self.repo.init()
        self.repo.write(".agents/config/guard-allow.txt", "tests/fixtures/fake.py\n")
        self.repo.write("tests/fixtures/fake.py", 'KEY = "AKIAQ7Z2X4M9P1L8V3N6"\n')
        self.repo.stage(".agents/config/guard-allow.txt", "tests/fixtures/fake.py")
        res = eng(self.tmp, "guard", "staged")
        self.assertEqual(res.returncode, 0, res.stdout)


class VerifyTests(EngTestCase):
    def test_pass_writes_verifiable_evidence(self):
        self.init_basic()
        res = eng(self.tmp, "verify", "--profile", "fast")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        path = next((self.tmp / ".agents" / "evidence").glob("*.json"))
        data = json.loads(path.read_text())
        self.assertEqual(data["verdict"]["status"], "pass")
        self.assertEqual(data["commands"][0]["status"], "pass")
        self.assertEqual(data["schema"], "eng-evidence/v1")
        check = eng(self.tmp, "evidence", "verify")
        self.assertEqual(check.returncode, 0, check.stdout)

    def test_failure_is_recorded_not_hidden(self):
        self.init_basic()
        self.repo.write(".agents/engineering.json", json.dumps({
            "schema": "eng-config/v1",
            "commands": {"fast": [{"name": "false", "run": "false"}], "full": [{"name": "false", "run": "false"}]},
            "security": {"required": [], "optional": []},
        }))
        res = eng(self.tmp, "verify", "--profile", "fast")
        self.assertEqual(res.returncode, 1)
        data = json.loads(next((self.tmp / ".agents" / "evidence").glob("*.json")).read_text())
        self.assertEqual(data["verdict"]["status"], "fail")
        self.assertIn("command:false", data["verdict"]["required_failures"])
        self.assertEqual(data["commands"][0]["exit_code"], 1)

    def test_output_is_redacted_in_logs(self):
        self.init_basic()
        self.repo.write(".agents/engineering.json", json.dumps({
            "schema": "eng-config/v1",
            "commands": {"fast": [{"name": "print-secret",
                                    "run": "python3 -c \"print('AKIAQ7Z2X4M9P1L8V3N6')\""}],
                          "full": [{"name": "true", "run": "true"}]},
            "security": {"required": [], "optional": []},
        }))
        res = eng(self.tmp, "verify", "--profile", "fast")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        log = next((self.tmp / ".agents" / "evidence").glob("*/00-print-secret.log"))
        text = log.read_text()
        self.assertNotIn("AKIAQ7Z2X4M9P1L8V3N6", text)
        self.assertIn("REDACTED:aws-access-key", text)

    def test_tampering_is_detected(self):
        self.init_basic()
        self.assertEqual(eng(self.tmp, "verify", "--profile", "fast").returncode, 0)
        path = next((self.tmp / ".agents" / "evidence").glob("*.json"))
        data = json.loads(path.read_text())
        data["verdict"]["status"] = "pass"
        data["commands"] = []
        path.write_text(json.dumps(data, indent=2))
        res = eng(self.tmp, "evidence", "verify")
        self.assertEqual(res.returncode, 1)
        self.assertIn("hash mismatch", res.stdout)

    def test_missing_required_scanner_blocks(self):
        self.init_basic()
        self.repo.write(".agents/engineering.json", json.dumps({
            "schema": "eng-config/v1",
            "commands": {"fast": [{"name": "true", "run": "true"}],
                          "full": [{"name": "true", "run": "true"}]},
            "security": {"required": ["eng-no-such-scanner"], "optional": []},
        }))
        res = eng(self.tmp, "verify", "--profile", "full")
        self.assertEqual(res.returncode, 2, res.stdout)
        data = json.loads(next((self.tmp / ".agents" / "evidence").glob("*.json")).read_text())
        self.assertEqual(data["verdict"]["status"], "blocked")
        self.assertTrue(any("eng-no-such-scanner" in u for u in data["verdict"]["unverified"]))


class ImpactTests(EngTestCase):
    def test_references_and_tests_are_found(self):
        self.repo.write("lib.py", "def divide(a, b):\n    return a / b\n")
        self.repo.write("use.py", "from lib import divide\nprint(divide(1, 0))\n")
        self.repo.write("tests/test_lib.py", "from lib import divide\n\ndef test_divide():\n    assert divide(4, 2) == 2\n")
        self.repo.init()
        self.repo.write("lib.py", "def divide(a, b):\n    if b == 0:\n        raise ValueError('zero')\n    return a / b\n")
        res = eng(self.tmp, "impact", "--base", "HEAD", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertEqual(data["symbols"][0]["name"], "divide")
        refs = {r["file"] for r in data["references"]}
        self.assertIn("use.py", refs)
        self.assertIn("tests/test_lib.py", refs)
        self.assertTrue(data["heuristic"])

    def test_unknown_base_is_an_error(self):
        self.init_basic()
        res = eng(self.tmp, "impact", "--base", "does-not-exist")
        self.assertEqual(res.returncode, 2)
        self.assertIn("cannot diff", res.stderr)


class WorktreeTests(EngTestCase):
    def test_create_list_remove(self):
        self.init_basic()
        res = eng(self.tmp, "worktree", "create", "task-a", "--owner", "agent-a")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        path = self.tmp / ".worktrees" / "task-a"
        self.assertTrue((path / "Makefile").exists())
        listing = eng(self.tmp, "worktree", "list", "--json")
        self.assertEqual(listing.returncode, 0)
        items = json.loads(listing.stdout)
        self.assertEqual(items[0]["owner"], "agent-a")
        removed = eng(self.tmp, "worktree", "remove", "task-a")
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertFalse(path.exists())

    def test_dirty_tree_refused(self):
        self.init_basic()
        self.repo.write("scratch.txt", "uncommitted\n")
        res = eng(self.tmp, "worktree", "create", "task-b")
        self.assertEqual(res.returncode, 2)
        self.assertIn("dirty", res.stderr)


class InitTests(EngTestCase):
    def test_init_is_idempotent_and_preserves_policy(self):
        self.repo.write("AGENTS.md", "# Policy\n\nKeep this invariant.\n")
        self.repo.write("Makefile", "check:\n\t@true\n")
        self.repo.init()
        first = run([str(KIT / "install.sh"), "--target", str(self.tmp)], cwd=KIT)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        second = run([str(KIT / "install.sh"), "--target", str(self.tmp)], cwd=KIT)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        text = (self.tmp / "AGENTS.md").read_text()
        self.assertIn("Keep this invariant.", text)
        self.assertEqual(text.count("<!-- eng:begin -->"), 1)
        self.assertTrue((self.tmp / ".agents" / "engineering.json").exists())
        self.assertTrue((self.tmp / ".agents" / "README.md").exists())
        self.assertTrue((self.tmp / ".agents" / "skills" / "repo-intelligence" / "SKILL.md").exists())
        self.assertTrue((self.tmp / ".claude" / "skills").is_symlink())
        self.assertTrue((self.tmp / ".opencode" / "skills").is_symlink())

    def test_install_without_agents_uses_template(self):
        self.repo.write("Makefile", "check:\n\t@true\n")
        self.repo.init()
        res = run([str(KIT / "install.sh"), "--target", str(self.tmp)], cwd=KIT)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        text = (self.tmp / "AGENTS.md").read_text()
        self.assertIn("Engineering controls", text)
        self.assertIn("make check", text)
        self.assertNotIn("{{PROJECT}}", text)

    def test_hook_blocks_staged_secret(self):
        self.repo.write("Makefile", "check:\n\t@true\n")
        self.repo.init()
        res = run([str(KIT / "install.sh"), "--target", str(self.tmp), "--hooks"], cwd=KIT)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.repo.write("leak.py", 'KEY = "AKIAQ7Z2X4M9P1L8V3N6"\n')
        self.repo.stage("leak.py")
        commit = run(["git", "commit", "-m", "should be blocked"], cwd=self.tmp)
        self.assertNotEqual(commit.returncode, 0)
        self.assertIn("aws-access-key", commit.stdout + commit.stderr)


class SkillTests(unittest.TestCase):
    def test_skills_have_frontmatter_and_required_sections(self):
        skills = sorted((KIT / "skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 10)
        for path in skills:
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), path)
            front, body = text.split("---", 2)[1], text.split("---", 2)[2]
            self.assertIn("name:", front, path)
            self.assertIn("description:", front, path)
            self.assertIn(f"name: {path.parent.name}", front, path)
            self.assertLessEqual(len(text.splitlines()), 150, path)
            for heading in ("## Activate when", "## Permissions", "## Verification", "## Done when"):
                self.assertIn(heading, body, f"{path} missing {heading}")

    def test_scanner_configs_exist(self):
        self.assertTrue((CONFIGS / "semgrep.yml").exists())
        self.assertTrue((CONFIGS / "gitleaks.toml").exists())
        self.assertTrue((KIT / "ci" / "agent-verify.yml").exists())


class ScannerTests(EngTestCase):
    def setUp(self):
        super().setUp()
        if not shutil.which("semgrep"):
            self.skipTest("semgrep not installed")
        self.init_basic()

    def test_semgrep_finds_shell_true(self):
        self.repo.write("bad.py", "import subprocess\nsubprocess.run('echo x', shell=True)\n")
        self.repo.write(".agents/engineering.json", json.dumps({
            "schema": "eng-config/v1",
            "commands": {"fast": [{"name": "true", "run": "true"}], "full": [{"name": "true", "run": "true"}]},
            "security": {"required": ["semgrep"], "optional": []},
        }))
        res = eng(self.tmp, "security", "--json")
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        semgrep = next(r for r in data["results"] if r["tool"] == "semgrep")
        self.assertEqual(semgrep["status"], "findings")
        self.assertGreaterEqual(semgrep["findings"], 1)


class GitleaksTests(EngTestCase):
    def setUp(self):
        super().setUp()
        if not shutil.which("gitleaks"):
            self.skipTest("gitleaks not installed")
        self.init_basic()

    def test_gitleaks_finds_tracked_secret(self):
        self.repo.write("leak.py", 'KEY = "ghp_7Qm2Kd9Xp4Vb8Nz3Rc6Tf1Lw5Hs0Jg2Yd4Ae"\n')
        self.repo.stage("leak.py")
        self.repo.git("commit", "-qm", "leak")
        self.repo.write(".agents/engineering.json", json.dumps({
            "schema": "eng-config/v1",
            "commands": {"fast": [{"name": "true", "run": "true"}], "full": [{"name": "true", "run": "true"}]},
            "security": {"required": ["gitleaks"], "optional": []},
        }))
        res = eng(self.tmp, "security", "--json")
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        gl = next(r for r in data["results"] if r["tool"] == "gitleaks")
        self.assertEqual(gl["status"], "findings")
        self.assertGreaterEqual(gl["findings"], 1)


if __name__ == "__main__":
    unittest.main()
