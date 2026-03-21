# QA-Pilot 🚀

> **AI-powered QA Automation Platform** — Production-grade from zero to deployment.
> Built with Django · FastAPI · Selenium · Pytest · LangChain · Gemini AI

---

## 🏗️ Architecture

```
qa_pilot/
├── apps/
│   ├── core/           # User model, TestSuite, TestCase, TestRun, BugReport
│   ├── scraper/        # Selenium scraper engine + Celery tasks + models
│   ├── testrunner/     # Pytest execution engine + Celery tasks
│   └── agents/         # 3 LangChain/Gemini AI agents
├── config/
│   ├── settings/       # base.py · development.py · production.py
│   ├── celery_app.py   # Celery config + beat schedule
│   └── urls.py
├── fastapi_app/
│   └── main.py         # REST API + WebSocket endpoints
├── frontend/
│   ├── static/         # CSS · JS · assets
│   └── templates/      # Dashboard · Scraper · Agents UI
├── tests/
│   ├── unit/           # Pytest unit tests (scraped data as fixtures)
│   ├── integration/    # Django TestClient integration tests
│   ├── e2e/            # Selenium browser tests
│   ├── api/            # FastAPI TestClient endpoint tests
│   └── performance/    # Locust load tests
├── docker/             # Dockerfiles + init.sql
├── .github/workflows/  # GitHub Actions CI/CD
├── docker-compose.yml
├── Makefile
└── pytest.ini
```

## ⚡ Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/qa-pilot.git
cd qa-pilot

# 2. One command setup (copies .env, builds Docker, migrates, seeds)
make setup

# 3. Add your Gemini API key to .env
echo "GEMINI_API_KEY=your_key_here" >> .env

# 4. Open
# Django:  http://localhost:8000       (admin / admin123)
# FastAPI: http://localhost:8001/docs
# Flower:  http://localhost:5555
```

## 🧪 Testing — 5 Types

| Type | Command | What it tests |
|------|---------|---------------|
| Unit | `make test-unit` | Scraper engine, AI agents (mocked) |
| Integration | `make test-integration` | DB ↔ API ↔ Celery pipeline |
| E2E | `make test-e2e` | Full browser UI flows (Selenium) |
| API | `make test-api` | Every FastAPI endpoint |
| Performance | `make test-perf` | Load tests with Locust |

### 🕷️ Web Scraping → Test Fixtures

```python
# Scrape Wikipedia data → store as ScrapedData → use as pytest fixtures
@pytest.mark.parametrize("country", scraped_data.as_pytest_fixtures())
def test_country_data_valid(country):
    assert country["population"] > 0
    assert country["rank"] >= 1
```

## 🤖 AI Agents

| Agent | What it does |
|-------|-------------|
| **Test Generator** | Takes feature description + scraped data → writes pytest code |
| **Failure Analyzer** | Reads test logs → root cause + fix in plain English |
| **Self-Healing Selector** | Broken CSS/XPath → finds new working selector automatically |

## 🚀 Services

- **Django** (`:8000`) — Core app, admin, Celery workers
- **FastAPI** (`:8001`) — REST API + WebSocket live streaming
- **PostgreSQL** (`:5432`) — Primary database
- **Redis** (`:6379`) — Celery broker + results
- **Celery Worker** — Async task execution
- **Celery Beat** — Scheduled scraping (every 6h)
- **Flower** (`:5555`) — Celery task monitoring

## 📋 Key Commands

```bash
make run          # Start all services
make test         # Run all tests
make test-cov     # Tests + coverage report
make scrape       # Trigger manual scrape
make lint         # flake8 + mypy
make format       # black + isort
make logs         # Tail all logs
make clean        # Remove containers
```

## 🔑 Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
GEMINI_API_KEY=your_gemini_key_here     # Required for AI agents
POSTGRES_PASSWORD=your_strong_password
DJANGO_SECRET_KEY=your_secret_key
```

## 📊 Tech Stack

**Backend:** Python 3.12 · Django 5 · FastAPI · Celery · PostgreSQL · Redis

**QA/Testing:** Selenium 4 · Pytest 8 · Allure · Locust · pytest-cov

**AI:** LangChain · Google Gemini API · LangChain Memory

**Scraping:** Selenium · BeautifulSoup4 · fake-useragent

**DevOps:** Docker · Docker Compose · GitHub Actions · Render

**Frontend:** HTML5 · CSS3 · Vanilla JS · Chart.js · WebSockets

---

Built by Tushar Kumar | [GitHub](https://github.com/tushar-kumar-9354) | [Portfolio](https://0tushar-portfolio0.netlify.app/)
