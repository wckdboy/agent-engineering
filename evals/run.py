#!/usr/bin/env python3
"""Control evaluation for the eng kit.

Copies a known-bad fixture into a temporary git repository, proves the controls
detect the planted issues, fixes them, and proves the controls pass. This is a
test of the controls, not a model benchmark.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
ENG = KIT / "bin" / "eng"
FIXTURE = KIT / "evals" / "control-fixture"
CONFIGS = KIT / "configs"


def run(cmd, cwd, timeout=180):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)


def eng(root, *args):
    return run([str(ENG), "--root", str(root), *args], cwd=root)


def git(root, *args):
    return run(["git", *args], cwd=root)


def latest_evidence(root):
    files = sorted((root / ".agents" / "evidence").glob("*.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(files[-1].read_text()) if files else {}


def main():
    started = time.perf_counter()
    tmp = Path(tempfile.mkdtemp(prefix="eng-eval-"))
    checks = []
    notes = []
    try:
        shutil.copytree(FIXTURE, tmp, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
        (tmp / ".agents" / "config").mkdir(parents=True, exist_ok=True)
        for name in ("semgrep.yml", "gitleaks.toml"):
            shutil.copy2(CONFIGS / name, tmp / ".agents" / "config" / name)
        (tmp / ".agents" / "config" / "guard-allow.txt").write_text("", encoding="utf-8")
        assert git(tmp, "init", "-q").returncode == 0
        git(tmp, "config", "user.email", "eng@example.invalid")
        git(tmp, "config", "user.name", "eng eval")
        git(tmp, "add", "-A")
        assert git(tmp, "commit", "-qm", "known-bad fixture").returncode == 0

        def record(name, expected, observed, ok):
            checks.append({"name": name, "expected": expected, "observed": observed, "ok": ok})

        # 1. Known-bad behavior must fail the configured test gate.
        res = eng(tmp, "verify", "--profile", "fast")
        evidence = latest_evidence(tmp)
        record("known-bad change fails", "fail", f"exit {res.returncode}",
               res.returncode == 1 and evidence.get("verdict", {}).get("status") == "fail")
        if res.returncode == 0:
            notes.append(res.stdout[-1000:])

        # 2. The staged/committed credential must be caught by the offline guard.
        res = eng(tmp, "guard", "all")
        record("planted secret is caught", "finding", f"exit {res.returncode}",
               res.returncode == 1 and ("github-token" in res.stdout or "secret" in res.stdout))

        # 3. Semgrep and gitleaks must find the planted issues.
        res = eng(tmp, "security", "--require", "--json")
        try:
            sec = json.loads(res.stdout)
        except json.JSONDecodeError:
            sec = {"results": []}
        by_tool = {r["tool"]: r for r in sec.get("results", [])}
        for tool in ("semgrep", "gitleaks"):
            r = by_tool.get(tool)
            if r is None or r.get("status") == "blocked":
                record(f"{tool} planted issue", "finding", "scanner unavailable", None)
                notes.append(f"{tool} was unavailable; install it to run this control")
            else:
                record(f"{tool} planted issue", "finding", f"{r.get('status')} ({r.get('findings')})",
                       r.get("status") == "findings" and (r.get("findings") or 0) >= 1)

        # 4. Change-impact should locate the changed symbol and its test.
        res = eng(tmp, "impact", "--base", "HEAD", "--json")
        impact_ok = False
        if res.returncode == 0:
            data = json.loads(res.stdout)
            names = {s["name"] for s in data.get("symbols", [])}
            files = {r["file"] for r in data.get("references", [])}
            impact_ok = "divide" in names and "tests/test_calc.py" in files
        record("impact finds symbol and test", "found", "found" if impact_ok else "missing", impact_ok)

        # 5. Apply the fix and remove the planted issues.
        res = run(["git", "apply", "fix.patch"], cwd=tmp)
        if res.returncode != 0:
            notes.append(f"fix.patch failed: {res.stderr}")
        (tmp / "leak.py").unlink(missing_ok=True)
        (tmp / "runner.py").unlink(missing_ok=True)
        git(tmp, "add", "-A")
        git(tmp, "commit", "-qm", "fixed fixture")

        res = eng(tmp, "verify", "--profile", "fast")
        record("known-good change passes", "pass", f"exit {res.returncode}",
               res.returncode == 0 and latest_evidence(tmp).get("verdict", {}).get("status") == "pass")

        # 6. No false positives after the issues are removed.
        res = eng(tmp, "guard", "all")
        record("clean tree passes guard", "pass", f"exit {res.returncode}", res.returncode == 0)

        res = eng(tmp, "security", "--require", "--json")
        try:
            sec = json.loads(res.stdout)
        except json.JSONDecodeError:
            sec = {"results": []}
        clean = all(r["status"] in ("pass", "skipped") for r in sec.get("results", []))
        record("clean tree passes scanners", "pass", f"exit {res.returncode}", res.returncode == 0 and clean)

        # 7. The evidence chain covering these runs must verify.
        res = eng(tmp, "evidence", "verify")
        record("evidence chain verifies", "pass", f"exit {res.returncode}", res.returncode == 0)

        evaluated = [c for c in checks if c["ok"] is not None]
        passed = [c for c in evaluated if c["ok"]]
        failed = [c for c in checks if c["ok"] is False]
        skipped = [c for c in checks if c["ok"] is None]
        report = {
            "schema": "eng-eval/v1",
            "checks": checks,
            "passed": len(passed),
            "evaluated": len(evaluated),
            "failed": len(failed),
            "skipped": len(skipped),
            "detection_rate": round(len(passed) / len(evaluated), 3) if evaluated else None,
            "duration_s": round(time.perf_counter() - started, 2),
            "notes": notes,
        }
        print("control evaluation")
        for c in checks:
            mark = "ok" if c["ok"] else ("skip" if c["ok"] is None else "FAIL")
            print(f"  {mark:<4} {c['name']:<32} expected={c['expected']:<8} observed={c['observed']}")
        print(f"  {len(passed)}/{len(evaluated)} evaluated controls passed"
              + (f"; {len(skipped)} skipped" if skipped else ""))
        if "--json" in sys.argv:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if not failed else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
