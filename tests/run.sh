#!/bin/sh
# Kit verification: syntax, unit/integration tests, optional linters, control eval.
set -eu
cd "$(dirname "$0")/.."

echo "== build the agent portal"
python3 site/build.py

echo "== python syntax"
python3 -m py_compile lib/eng.py tests/test_eng.py tests/test_site.py evals/run.py evals/agent/run.py evals/agent/stub_agent.py site/build.py

echo "== javascript syntax"
if command -v node >/dev/null 2>&1; then
  node --check site/assets/app.js
else
  echo "skip: node not installed"
fi

echo "== unit and integration tests"
python3 -m unittest discover -s tests -t . -v

echo "== shellcheck"
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck install.sh bin/eng hooks/pre-commit hooks/pre-push
else
  echo "skip: shellcheck not installed"
fi

echo "== actionlint"
if command -v actionlint >/dev/null 2>&1; then
  actionlint ci/agent-verify.yml .github/workflows/ci.yml
else
  echo "skip: actionlint not installed"
fi

echo "== semgrep config validation"
if command -v semgrep >/dev/null 2>&1; then
  semgrep scan --validate --config configs/semgrep.yml >/dev/null
else
  echo "skip: semgrep not installed"
fi

echo "== control evaluation"
./evals/run.py

echo "== agent harness (deterministic stub)"
./evals/agent/run.py

echo "== agent harness (no-op must score zero)"
if ./evals/agent/run.py --agent-cmd true >/tmp/eng-agent-noop.log 2>&1; then
  echo "FAIL: a no-op agent passed the task set"
  exit 1
fi
echo "ok: no-op agent scored zero"
