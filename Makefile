.PHONY: help install dev test lint format clean build deploy docs

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development Setup
install: ## Install dependencies
	poetry install --with dev,test

dev-install: ## Install development dependencies
	poetry install --with dev,test --extras all

update: ## Update dependencies
	poetry update

# Code Quality
lint: ## Run linting
	poetry run black --check .
	poetry run isort --check-only .
	poetry run flake8 .
	poetry run mypy .
	poetry run bandit -r src/ apps/

format: ## Format code
	poetry run black .
	poetry run isort .

type-check: ## Run type checking
	poetry run mypy src/ apps/

security-check: ## Run security checks
	poetry run bandit -r src/ apps/

# Testing
test: ## Run all tests
	poetry run pytest

test-unit: ## Run unit tests only
	poetry run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	poetry run pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	poetry run pytest tests/e2e/ -v

test-coverage: ## Run tests with coverage
	poetry run pytest --cov=src --cov=apps --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode
	poetry run pytest-watch

# Development Server
dev-api: ## Run development API server
	poetry run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8080

dev-frontend: ## Run development frontend server
	cd frontend && npm run dev

dev-full: ## Run full development stack
	docker-compose -f deployment/docker/docker-compose.yml up

# Database
db-migrate: ## Run database migrations
	poetry run python -m apps.cli.commands db migrate

db-upgrade: ## Upgrade database to latest migration
	poetry run python -m apps.cli.commands db upgrade

db-downgrade: ## Downgrade database by one migration
	poetry run python -m apps.cli.commands db downgrade

# Build & Deploy
build: ## Build the application
	poetry build

build-docker: ## Build Docker images
	docker-compose -f deployment/docker/docker-compose.prod.yml build

deploy-staging: ## Deploy to staging environment
	./deployment/scripts/deploy.sh staging

deploy-prod: ## Deploy to production environment
	./deployment/scripts/deploy.sh production

# Documentation
docs: ## Generate documentation
	poetry run mkdocs serve

docs-build: ## Build documentation
	poetry run mkdocs build

# Utilities
clean: ## Clean build artifacts
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/

pre-commit: ## Run pre-commit hooks
	poetry run pre-commit run --all-files

setup-hooks: ## Setup git hooks
	poetry run pre-commit install

# Environment
env-example: ## Create example environment file
	cp .env.example .env

# Performance
benchmark: ## Run performance benchmarks
	poetry run locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 30s

# Monitoring
health-check: ## Check application health
	curl -f http://localhost:8080/health || exit 1

logs: ## View application logs
	docker-compose -f deployment/docker/docker-compose.yml logs -f api

# Version Management
version-patch: ## Bump patch version
	poetry run cz bump --increment PATCH

version-minor: ## Bump minor version
	poetry run cz bump --increment MINOR

version-major: ## Bump major version
	poetry run cz bump --increment MAJOR

# CI/CD
ci-test: ## Run CI tests
	poetry run pytest --cov=src --cov=apps --cov-report=xml --junitxml=test-results.xml

ci-lint: ## Run CI linting
	poetry run black --check .
	poetry run isort --check-only .
	poetry run flake8 . --format=junit-xml --output-file=flake8-results.xml
	poetry run mypy . --junit-xml=mypy-results.xml

ci-security: ## Run CI security checks
	poetry run bandit -r src/ apps/ -f json -o bandit-results.json

# Development Utilities
shell: ## Open Python shell with app context
	poetry run python -c "from apps.api.main import app; import IPython; IPython.embed()"

routes: ## Show all API routes
	poetry run python -c "from apps.api.main import app; from fastapi.routing import APIRoute; [print(f'{route.methods} {route.path}') for route in app.routes if isinstance(route, APIRoute)]"

config: ## Show current configuration
	poetry run python -c "from src.infinitum.infrastructure.config.settings import get_settings; import json; print(json.dumps(get_settings().dict(), indent=2, default=str))"

# Migration
migrate-old-to-new: ## Run migration from old structure to new
	@echo "🔄 Starting migration from old structure to new clean architecture..."
	@echo "📋 Step 1: Backup current structure"
	cp -r backend/ backup_backend_$(shell date +%Y%m%d_%H%M%S)/
	cp -r InfinitiumX/ backup_frontend_$(shell date +%Y%m%d_%H%M%S)/
	@echo "✅ Backup completed"
	@echo "📋 Step 2: Install new dependencies"
	poetry install --with dev,test
	@echo "✅ Dependencies installed"
	@echo "📋 Step 3: Run structure validation"
	poetry run python -c "from src.infinitum.infrastructure.di.container import get_container; print('✅ DI Container loads successfully')"
	@echo "📋 Step 4: Run tests"
	poetry run pytest tests/ -v
	@echo "🎉 Migration completed! Check docs/MIGRATION_GUIDE.md for detailed information"

validate-structure: ## Validate new project structure
	@echo "🔍 Validating new project structure..."
	@echo "📋 Checking domain layer..."
	@test -f src/infinitum/domain/entities/user.py && echo "✅ User entity exists" || echo "❌ User entity missing"
	@test -f src/infinitum/domain/value_objects/price.py && echo "✅ Price value object exists" || echo "❌ Price value object missing"
	@test -f src/infinitum/domain/repositories/user_repository.py && echo "✅ User repository interface exists" || echo "❌ User repository interface missing"
	@echo "📋 Checking application layer..."
	@test -f src/infinitum/application/use_cases/chat/send_message.py && echo "✅ Send message use case exists" || echo "❌ Send message use case missing"
	@test -f src/infinitum/application/commands/chat_commands.py && echo "✅ Chat commands exist" || echo "❌ Chat commands missing"
	@echo "📋 Checking infrastructure layer..."
	@test -f src/infinitum/infrastructure/config/settings.py && echo "✅ Settings configuration exists" || echo "❌ Settings configuration missing"
	@test -f src/infinitum/infrastructure/di/container.py && echo "✅ DI container exists" || echo "❌ DI container missing"
	@echo "📋 Checking API layer..."
	@test -f apps/api/main.py && echo "✅ FastAPI main exists" || echo "❌ FastAPI main missing"
	@echo "📋 Checking configuration files..."
	@test -f pyproject.toml && echo "✅ Poetry configuration exists" || echo "❌ Poetry configuration missing"
	@test -f Makefile && echo "✅ Makefile exists" || echo "❌ Makefile missing"
	@echo "🎉 Structure validation completed!"