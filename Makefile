.PHONY: setup test check agent-dev website-dev website-build playground
PYTHON ?= python3
PY := .venv/bin/python
PNPM := npx --yes pnpm@10.11.0

setup:
	$(PYTHON) -m venv .venv
	$(PY) -m pip install -r requirements-dev.txt
	$(PY) -m playwright install chromium

# Test runner installs dummy settings and blocks external sockets.
test:
	$(PY) -m scripts.run_tests

check:
	$(PY) -m ruff check apps/agent/src apps/playground/src packages tests scripts
	$(PY) -m scripts.check_repository
	$(MAKE) test

agent-dev:
	$(PY) -m uvicorn aisha.app:app --reload --port 8000

website-dev:
	cd apps/website && $(PNPM) dev

website-build:
	cd apps/website && CI=true $(PNPM) install --frozen-lockfile && $(PNPM) build

playground:
	@test -n "$(ZIP)" || (echo 'Use make playground ZIP="/path/export.zip"'; exit 2)
	$(PY) -m aisha_playground.cli "$(ZIP)" $(ARGS)
