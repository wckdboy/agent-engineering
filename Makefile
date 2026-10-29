.PHONY: check test eval lint install

check: test

test:
	./tests/run.sh

eval:
	./evals/run.py

lint:
	python3 -m py_compile lib/eng.py tests/test_eng.py evals/run.py evals/agent/run.py evals/agent/stub_agent.py
	shellcheck install.sh bin/eng hooks/pre-commit hooks/pre-push
	actionlint ci/agent-verify.yml .github/workflows/ci.yml

install:
	@echo "usage: ./install.sh --target <repo> [--hooks] [--ci]"
