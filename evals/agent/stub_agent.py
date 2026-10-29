#!/usr/bin/env python3
"""Deterministic stub agent for harness validation. Applies the task's known patch."""

import os
import subprocess
import sys
from pathlib import Path

task = os.environ.get("ENG_TASK")
if not task:
    print("stub_agent: ENG_TASK is not set", file=sys.stderr)
    sys.exit(2)
patch = Path(__file__).resolve().parent / "tasks" / task / "patch.diff"
if not patch.exists():
    print(f"stub_agent: no patch for {task}", file=sys.stderr)
    sys.exit(2)
res = subprocess.run(["git", "apply", str(patch)], cwd=os.getcwd())
sys.exit(res.returncode)
