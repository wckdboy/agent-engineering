.PHONY: check test eval site serve lint install

check: test

test:
	./tests/run.sh

eval:
	./evals/run.py

site:
	python3 site/build.py

serve: site
	cd site && python3 -m http.server 8080

lint:
	python3 -m py_compile lib/eng.py tests/test_eng.py tests/test_site.py evals/run.py evals/agent/run.py evals/agent/stub_agent.py site/build.py
	shellcheck install.sh bin/eng hooks/pre-commit hooks/pre-push
	actionlint ci/agent-verify.yml .github/workflows/ci.yml

install:
	@echo "usage: ./install.sh --target <repo> [--hooks] [--ci]"
