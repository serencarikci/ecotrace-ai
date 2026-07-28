.PHONY: help up down build logs migrate migration seed import-sample test test-backend test-frontend lint format clean

SHELL := /bin/bash
COMPOSE := docker compose
API_DIR := apps/api
WEB_DIR := apps/web
PYTHON := python3.12

help:
	@echo "EcoTrace AI — Make targets (v0.4.0)"
	@echo ""
	@echo "  make up              Start all services (docker compose up --build)"
	@echo "  make down            Stop all services"
	@echo "  make build           Build images without starting"
	@echo "  make logs            Tail compose logs"
	@echo "  make migrate         Run Alembic migrations (via API container)"
	@echo "  make migration name= Create a new Alembic revision"
	@echo "  make seed            Seed demo data"
	@echo "  make import-sample   Print sample CSV import template path hint"
	@echo "  make test            Run backend and frontend tests"
	@echo "  make test-backend    Run backend pytest suite"
	@echo "  make test-frontend   Run Angular unit tests (CI mode)"
	@echo "  make lint            Lint backend and frontend"
	@echo "  make format          Format backend and frontend"
	@echo "  make clean           Remove caches and build artifacts"

up:
	@command -v docker >/dev/null || { echo "Error: docker is required"; exit 1; }
	$(COMPOSE) up --build -d
	@echo "Frontend: http://localhost:$${WEB_HOST_PORT:-4200}"
	@echo "API docs: http://localhost:$${API_HOST_PORT:-8000}/docs"
	@echo "If ports conflict, set POSTGRES_HOST_PORT / API_HOST_PORT / WEB_HOST_PORT in .env"

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

migrate:
	$(COMPOSE) exec api alembic upgrade head

migration:
	@test -n "$(name)" || { echo "Usage: make migration name=add_example"; exit 1; }
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(name)"

seed:
	$(COMPOSE) exec api python -m ecotrace.db.seed

import-sample:
	@echo "Download template from: GET /api/v1/organizations/{organizationId}/imports/activity-records/template"
	@echo "Or open Swagger: http://localhost:$${API_HOST_PORT:-8000}/docs"

test: test-backend test-frontend

test-backend:
	@command -v $(PYTHON) >/dev/null || { echo "Error: $(PYTHON) is required"; exit 1; }
	cd $(API_DIR) && $(PYTHON) -m pytest tests/ -v --cov=ecotrace --cov-report=term-missing

test-frontend:
	@command -v npm >/dev/null || { echo "Error: npm is required"; exit 1; }
	cd $(WEB_DIR) && npm test -- --watch=false --browsers=ChromeHeadless

lint:
	cd $(API_DIR) && $(PYTHON) -m ruff check src tests && $(PYTHON) -m ruff format --check src tests && $(PYTHON) -m mypy src
	cd $(WEB_DIR) && npm run lint

format:
	cd $(API_DIR) && $(PYTHON) -m ruff format src tests && $(PYTHON) -m ruff check --fix src tests
	cd $(WEB_DIR) && npx prettier --write "src/**/*.{ts,html,scss,css,json}"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(API_DIR)/.coverage $(API_DIR)/htmlcov $(WEB_DIR)/dist $(WEB_DIR)/.angular 2>/dev/null || true
	@echo "Cleaned caches and build artifacts"
