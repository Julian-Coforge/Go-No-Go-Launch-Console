# Mission Control: one command to start the app, one to run the tests.
#   make dev   start the API on :8000 and the UI on :5173 (Ctrl+C stops both)
#   make test  run every back end and front end test (no network or API key needed)

PYTHON ?= python3
VENV := backend/.venv
BACKEND_STAMP := $(VENV)/.installed
FRONTEND_STAMP := frontend/node_modules/.installed

.PHONY: install dev test test-backend test-frontend

install: $(BACKEND_STAMP) $(FRONTEND_STAMP)

$(BACKEND_STAMP): backend/requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -q -r backend/requirements.txt
	touch $@

$(FRONTEND_STAMP): frontend/package.json frontend/package-lock.json
	cd frontend && npm ci --no-audit --no-fund
	touch $@

dev: install
	@trap 'kill $$(jobs -p) 2>/dev/null' INT TERM; \
	(cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

test: install test-backend test-frontend

test-backend:
	cd backend && .venv/bin/pytest

test-frontend:
	cd frontend && npm test
