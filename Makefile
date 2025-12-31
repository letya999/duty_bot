.PHONY: help setup dev test test-cov lint format clean docker-build docker-up docker-down db-migrate db-seed

# ==================
# Colors for output
# ==================
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Display this help screen
	@echo "$(BLUE)=== Duty Bot - Make Commands ===$(NC)"
	@echo ""
	@grep -h -E '^\s*[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sed 's/: \(.*\)## /: /' | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make setup         # Initial project setup"
	@echo "  make dev           # Run dev servers"
	@echo "  make test          # Run all tests"
	@echo "  make docker-up     # Start Docker containers"
	@echo ""

# ==================
# Setup & Installation
# ==================

setup: ## Setup development environment (venv, deps, keys)
	@echo "$(BLUE)Setting up development environment...$(NC)"
	bash scripts/setup-dev.sh

install-deps: ## Install Python and Node dependencies
	pip install --upgrade pip
	pip install -r requirements.txt
	cd webapp && npm install && cd ..

install-dev-deps: ## Install development dependencies (includes test dependencies)
	pip install --upgrade pip
	pip install -r requirements.txt
	cd webapp && npm install && cd ..

# ==================
# Development
# ==================

dev: ## Run backend and frontend dev servers concurrently
	@echo "$(BLUE)Starting development servers...$(NC)"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo "$(YELLOW)Press Ctrl+C to stop$(NC)"
	@(trap 'kill 0' SIGINT; \
		python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & \
		cd webapp && npm run dev -- --host 0.0.0.0 & \
		wait)

backend: ## Run backend dev server with auto-reload
	@echo "$(BLUE)Starting backend server...$(NC)"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/api/docs"
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Run frontend dev server
	@echo "$(BLUE)Starting frontend server...$(NC)"
	@echo "App: http://localhost:5173"
	cd webapp && npm run dev -- --host 0.0.0.0

# ==================
# Testing
# ==================

test: ## Run all tests
	pytest tests/

test-unit: ## Run unit tests only
	pytest tests/ -m unit -v

test-integration: ## Run integration tests only
	pytest tests/ -m integration -v

test-cov: ## Run tests with coverage report
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)Coverage report generated: htmlcov/index.html$(NC)"

test-watch: ## Run tests in watch mode (requires pytest-watch)
	ptw tests/

test-fast: ## Run quick tests (skip slow tests)
	pytest tests/ -m "not slow" -v

# ==================
# Code Quality
# ==================

lint: ## Run linters (flake8, mypy, ruff)
	@echo "$(BLUE)Running linters...$(NC)"
	-flake8 app tests --max-line-length=120 --extend-ignore=E203,W503
	-mypy app --ignore-missing-imports
	-ruff check app tests

format: ## Format code with Black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	black app tests
	isort app tests

format-check: ## Check code formatting without changes
	black --check app tests
	isort --check-only app tests

# ==================
# Database
# ==================

db-init: ## Initialize database from schema
	@echo "$(BLUE)Initializing database...$(NC)"
	alembic upgrade head

db-migrate: ## Create a new migration
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-downgrade: ## Rollback to previous migration
	alembic downgrade -1

db-seed: ## Seed database with sample data
	@echo "$(BLUE)Seeding database...$(NC)"
	python -m app.scripts.seed

db-reset: ## Reset database (WARNING: destructive)
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		alembic downgrade base && alembic upgrade head; \
		echo "$(GREEN)Database reset complete$(NC)"; \
	else \
		echo "Cancelled"; \
	fi

# ==================
# Docker
# ==================

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build

docker-up: ## Start Docker containers
	@echo "$(BLUE)Starting Docker containers...$(NC)"
	@echo "App: http://localhost:8000"
	@echo "Admin: http://localhost:8000/api/admin"
	@echo "Frontend: http://localhost:5173"
	docker-compose up -d
	@echo "$(GREEN)Containers started. Check logs with: make docker-logs$(NC)"

docker-down: ## Stop Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-logs-app: ## View app container logs only
	docker-compose logs -f app

docker-logs-db: ## View database logs only
	docker-compose logs -f postgres

docker-shell: ## Open shell in app container
	docker-compose exec app /bin/bash

docker-shell-db: ## Open psql in database container
	docker-compose exec postgres psql -U $(shell grep POSTGRES_USER .env 2>/dev/null | cut -d= -f2) -d $(shell grep POSTGRES_DB .env 2>/dev/null | cut -d= -f2)

docker-clean: ## Remove all Docker containers and volumes (WARNING: destructive)
	@echo "$(RED)WARNING: This will delete all containers and volumes!$(NC)"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker-compose down -v; \
		echo "$(GREEN)Cleaned up$(NC)"; \
	else \
		echo "Cancelled"; \
	fi

# ==================
# Utilities
# ==================

clean: ## Clean up generated files and cache
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	find . -type f -name '.coverage' -delete 2>/dev/null || true
	rm -rf htmlcov/ .pytest_cache/ .mypy_cache/ dist/ build/ *.egg-info 2>/dev/null || true
	cd webapp && npm run clean 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete$(NC)"

health: ## Check service health
	@echo "$(BLUE)Checking service health...$(NC)"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "$(RED)Service not responding$(NC)"

health-detailed: ## Get detailed health information
	@echo "$(BLUE)Getting detailed health info...$(NC)"
	@curl -s http://localhost:8000/health/detailed | python -m json.tool || echo "$(RED)Service not responding$(NC)"

env-check: ## Validate environment configuration
	@echo "$(BLUE)Checking environment configuration...$(NC)"
	python scripts/validate_env.py

version: ## Show project version
	@grep -E "^version|^__version__" app/config.py | head -1 || echo "Version not found"

.DEFAULT_GOAL := help
