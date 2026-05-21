PYTHON ?= python3
COMPOSE ?= docker-compose
DATASET ?= data/eval/questions.yaml
REPORT_DIR ?= reports/evaluation
PIP_AUDIT_CACHE_DIR ?= .cache/pip-audit

.PHONY: help build up down init-db ingest ingest-synthetic ingest-public eval eval-agentic eval-tools demo-walkthrough audit test-local test-docker smoke

help:
	@echo "Agentic Knowledge Assistant commands"
	@echo ""
	@echo "  make build            Build the API image"
	@echo "  make up               Start API and Postgres"
	@echo "  make down             Stop Docker Compose services"
	@echo "  make init-db          Initialize tables, PGVector, and demo rows"
	@echo "  make ingest           Ingest synthetic and public demo docs"
	@echo "  make eval             Run baseline and agentic evaluation"
	@echo "  make eval-agentic     Run agentic evaluation only"
	@echo "  make eval-tools       Run focused agentic tool tests and write JSON report"
	@echo "  make demo-walkthrough Print the interview/demo API walkthrough"
	@echo "  make audit            Run Bandit and pip-audit security checks"
	@echo "  make test-local       Run local compile and whitespace checks"
	@echo "  make test-docker      Run mounted test suite inside the API container"
	@echo "  make smoke            Build, initialize, ingest, and run agentic eval"

build:
	$(COMPOSE) build api

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

init-db:
	$(COMPOSE) run --rm api python -m app.db.init_db

ingest-synthetic:
	$(COMPOSE) run --rm api python -m app.ingestion.pipeline --path data/synthetic

ingest-public:
	$(COMPOSE) run --rm api python -m app.ingestion.pipeline --path data/raw/public_mws

ingest: ingest-synthetic ingest-public

eval:
	$(COMPOSE) run --rm api python -m app.evaluation.run_eval --dataset $(DATASET) --mode both

eval-agentic:
	$(COMPOSE) run --rm api python -m app.evaluation.run_eval --dataset $(DATASET) --mode agentic

eval-tools:
	$(COMPOSE) run --rm -v "$(CURDIR)/reports:/app/reports" api python -m app.evaluation.run_eval --dataset $(DATASET) --mode agentic --tag tool --output $(REPORT_DIR)/tool-agentic.json

demo-walkthrough:
	$(PYTHON) scripts/demo_walkthrough.py

audit:
	$(PYTHON) -m bandit -q -c pyproject.toml -r app scripts
	$(PYTHON) -m pip_audit --cache-dir $(PIP_AUDIT_CACHE_DIR) --skip-editable --progress-spinner off

test-local:
	$(PYTHON) scripts/smoke_check.py

test-docker: build
	$(COMPOSE) run --rm -v "$(CURDIR)/tests:/app/tests:ro" api python tests/manual_runner.py

smoke: build init-db ingest eval-agentic
