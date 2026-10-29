# Control fixture

This is not a product. It is a known-bad repository used to prove that the controls detect a
representative failure, a planted credential and a planted SAST issue, and that the controls do not
report false positives after the issues are fixed.

- `calc.py` — `divide(1, 0)` silently returns `0`; `fix.patch` changes it to raise.
- `tests/test_calc.py` — a passing test and a failing test that describes the bug.
- `runner.py` — `subprocess.run(..., shell=True)` for the Semgrep rule.
- `leak.py` — a fake GitHub token for gitleaks/guard.

`evals/run.py` copies this directory to a temporary git repository, commits the known-bad state,
runs the controls, applies the fix and removes the planted issues, then re-runs the controls.
