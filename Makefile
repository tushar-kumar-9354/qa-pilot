# ============================================================
# QA-PILOT — Makefile
# ============================================================

.PHONY: help setup run stop restart shell migrate makemigrations \
        test test-unit test-integration test-e2e test-api test-perf \
        lint format scrape celery flower logs clean

# ── Default ─────────────────────────────────────────────────
help:
	@echo ""
	@echo "  QA-PILOT — Available Commands"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make setup          — First-time setup (copy .env, build Docker)"
	@echo "  make run            — Start all services"
	@echo "  make stop           — Stop all services"
	@echo "  make restart        — Restart all services"
	@echo ""
	@echo "  make migrate        — Run Django migrations"
	@echo "  make makemigrations — Create new migrations"
	@echo "  make createsuperuser— Create Django admin user"
	@echo "  make shell          — Django shell"
	@echo ""
	@echo "  make test           — Run ALL tests"
	@echo "  make test-unit      — Run unit tests only"
	@echo "  make test-integration — Run integration tests"
	@echo "  make test-e2e       — Run Selenium E2E tests"
	@echo "  make test-api       — Run API tests"
	@echo "  make test-perf      — Run Locust performance tests"
	@echo "  make test-cov       — Run tests with coverage report"
	@echo "  make allure         — Generate Allure report"
	@echo ""
	@echo "  make scrape         — Trigger web scraper manually"
	@echo "  make celery         — Show Celery worker logs"
	@echo "  make flower         — Open Flower monitoring (port 5555)"
	@echo ""
	@echo "  make lint           — Run flake8 + mypy"
	@echo "  make format         — Run black + isort"
	@echo "  make logs           — Tail all service logs"
	@echo "  make clean          — Remove containers + volumes"
	@echo ""

# ── Setup ────────────────────────────────────────────────────
setup:
	@echo "→ Copying .env.example to .env..."
	@cp -n .env.example .env || echo ".env already exists, skipping"
	@echo "→ Building Docker images..."
	docker compose build
	@echo "→ Starting services..."
	docker compose up -d db redis
	@sleep 3
	docker compose up -d django fastapi celery_worker celery_beat flower
	@sleep 5
	@echo "→ Running migrations..."
	docker compose exec django python manage.py migrate
	@echo "→ Creating superuser (admin / admin123)..."
	docker compose exec django python manage.py shell -c \
		"from django.contrib.auth import get_user_model; U=get_user_model(); \
		 U.objects.filter(username='admin').exists() or \
		 U.objects.create_superuser('admin','admin@qapilot.dev','admin123')"
	@echo ""
	@echo "✅ QA-PILOT is ready!"
	@echo "   Django:   http://localhost:8000"
	@echo "   FastAPI:  http://localhost:8001/docs"
	@echo "   Admin:    http://localhost:8000/admin  (admin / admin123)"
	@echo "   Flower:   http://localhost:5555"

# ── Run/Stop ─────────────────────────────────────────────────
run:
	docker compose up -d

stop:
	docker compose stop

restart:
	docker compose restart

# ── Django management ────────────────────────────────────────
migrate:
	docker compose exec django python manage.py migrate

makemigrations:
	docker compose exec django python manage.py makemigrations

createsuperuser:
	docker compose exec django python manage.py createsuperuser

shell:
	docker compose exec django python manage.py shell

# ── Testing ──────────────────────────────────────────────────
test:
	docker compose exec django pytest tests/ -v --tb=short

test-unit:
	docker compose exec django pytest tests/unit/ -v --tb=short -m "unit"

test-integration:
	docker compose exec django pytest tests/integration/ -v --tb=short -m "integration"

test-e2e:
	docker compose exec django pytest tests/e2e/ -v --tb=short -m "e2e"

test-api:
	docker compose exec django pytest tests/api/ -v --tb=short -m "api"

test-perf:
	docker compose exec django locust -f tests/performance/locustfile.py \
		--host=http://fastapi:8001 --headless -u 10 -r 2 --run-time 30s

test-cov:
	docker compose exec django pytest tests/ \
		--cov=apps --cov-report=html --cov-report=term-missing --cov-fail-under=80

allure:
	docker compose exec django pytest tests/ --alluredir=allure-results
	allure serve allure-results

# ── Scraper ──────────────────────────────────────────────────
scrape:
	docker compose exec django python manage.py trigger_scrape

# ── Celery ───────────────────────────────────────────────────
celery:
	docker compose logs -f celery_worker

flower:
	@echo "Flower monitoring: http://localhost:5555"
	@open http://localhost:5555 2>/dev/null || xdg-open http://localhost:5555 2>/dev/null || true

# ── Code Quality ─────────────────────────────────────────────
lint:
	docker compose exec django flake8 apps/ config/ fastapi_app/ --max-line-length=100
	docker compose exec django mypy apps/ --ignore-missing-imports

format:
	docker compose exec django black apps/ config/ fastapi_app/ tests/
	docker compose exec django isort apps/ config/ fastapi_app/ tests/

# ── Logs ────────────────────────────────────────────────────
logs:
	docker compose logs -f

# ── Clean ────────────────────────────────────────────────────
clean:
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov allure-results .coverage
	@echo "✅ Cleaned"
