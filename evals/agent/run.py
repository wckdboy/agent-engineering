#!/usr/bin/env python3
"""Agent evaluation harness.

Runs a task set in isolated git worktrees, scores each result with the task's
verification command, and reports pass rate, latency and diff size. The agent is
an arbitrary command; no model or provider is assumed. The built-in stub proves
the harness itself works and that a no-op agent scores zero.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
ENG = KIT / "bin" / "eng"
FIXTURE = Path(__file__).resolve().parent / "fixture"
TASKS = Path(__file__).resolve().parent / "tasks"
STUB = Path(__file__).resolve().parent / "stub_agent.py"


def run(cmd, cwd, timeout=600, env=None):
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=str(cwd), shell=isinstance(cmd, str),
                          capture_output=True, text=True, timeout=timeout, env=merged)


def git(cwd, *args):
    return run(["git", *args], cwd=cwd)


def task_list():
    tasks = []
    for path in sorted(TASKS.glob("*/task.json")):
        tasks.append(json.loads(path.read_text(encoding="utf-8")))
    return tasks


def diff_stats(cwd):
    res = git(cwd, "diff", "--numstat")
    added = removed = files = 0
    for line in res.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            added += int(parts[0])
            removed += int(parts[1])
            files += 1
    return {"files": files, "added": added, "removed": removed}


def run_task(base, task, agent_cmd, keep):
    tid = task["id"]
    wt = base / ".worktrees" / tid
    result = {
        "task": tid, "prompt": task["prompt"], "baseline_failed": None,
        "agent_exit": None, "verify_exit": None, "passed": False,
        "duration_s": 0.0, "diff": {}, "notes": [],
    }
    created = run([str(ENG), "--root", str(base), "worktree", "create", tid,
                   "--owner", "eval-agent"], cwd=base)
    if created.returncode != 0:
        result["notes"].append(f"worktree create failed: {created.stderr.strip()[:300]}")
        return result
    try:
        # Baseline must fail; otherwise the task does not measure a change.
        baseline = run(task["verify"], cwd=wt, timeout=120)
        result["baseline_failed"] = baseline.returncode != 0
        if not result["baseline_failed"]:
            result["notes"].append("task already passes before the agent; result is invalid")
            return result

        started = time.perf_counter()
        env = {"ENG_TASK": tid, "ENG_PROMPT": task["prompt"], "ENG_REPO": str(wt)}
        if agent_cmd:
            cmd = agent_cmd.replace("{worktree}", str(wt)).replace("{task}", tid)
            agent = run(cmd, cwd=wt, timeout=1800, env=env)
        else:
            agent = run([sys.executable, str(STUB)], cwd=wt, timeout=120, env=env)
        result["agent_exit"] = agent.returncode
        if agent.returncode != 0:
            result["notes"].append(f"agent exited {agent.returncode}: {agent.stderr.strip()[:300]}")

        verified = run(task["verify"], cwd=wt, timeout=180)
        result["verify_exit"] = verified.returncode
        result["passed"] = verified.returncode == 0 and result["baseline_failed"]
        result["duration_s"] = round(time.perf_counter() - started, 2)
        result["diff"] = diff_stats(wt)
        if not result["passed"]:
            result["notes"].append((verified.stdout + verified.stderr).strip()[-500:])
        return result
    finally:
        if not keep:
            removed = run([str(ENG), "--root", str(base), "worktree", "remove", tid, "--force"], cwd=base)
            if removed.returncode != 0:
                result["notes"].append(f"worktree remove failed: {removed.stderr.strip()[:200]}")


def main():
    parser = argparse.ArgumentParser(description="Run agent tasks in isolated worktrees and score them.")
    parser.add_argument("--agent-cmd", help="shell command run in the worktree; {worktree} and {task} are substituted")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--keep", action="store_true", help="keep worktrees (temporary repo is still removed)")
    parser.add_argument("--task", action="append", help="run only this task id (repeatable)")
    args = parser.parse_args()

    tasks = task_list()
    if args.task:
        wanted = set(args.task)
        tasks = [t for t in tasks if t["id"] in wanted]
    if not tasks:
        print("agent eval: no tasks found", file=sys.stderr)
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="eng-agent-eval-"))
    started = time.perf_counter()
    try:
        shutil.copytree(FIXTURE, tmp, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        assert git(tmp, "init", "-q").returncode == 0
        git(tmp, "config", "user.email", "eng@example.invalid")
        git(tmp, "config", "user.name", "eng eval")
        assert git(tmp, "add", "-A").returncode == 0
        assert git(tmp, "commit", "-qm", "agent-eval fixture").returncode == 0

        results = [run_task(tmp, task, args.agent_cmd, args.keep) for task in tasks]
        passed = [r for r in results if r["passed"]]
        report = {
            "schema": "eng-agent-eval/v1",
            "agent": args.agent_cmd or "built-in stub",
            "tasks": results,
            "passed": len(passed),
            "total": len(results),
            "pass_rate": round(len(passed) / len(results), 3) if results else None,
            "duration_s": round(time.perf_counter() - started, 2),
            "cost_usd": None,
            "note": "Pass rate is over this task set only; it is not a model benchmark.",
        }
        print("agent evaluation")
        for r in results:
            mark = "ok" if r["passed"] else "FAIL"
            diff = r.get("diff", {})
            print(f"  {mark:<4} {r['task']:<16} {r['duration_s']:>6.2f}s  "
                  f"diff={diff.get('files', 0)}f/{diff.get('added', 0)}+/{diff.get('removed', 0)}-"
                  + (f"  {'; '.join(r['notes'])}" if r["notes"] else ""))
        print(f"  {len(passed)}/{len(results)} passed")
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if len(passed) == len(results) else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
