# QA-Pilot 🚀

![CI](https://github.com/tushar-kumar-9354/qa-pilot/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Django](https://img.shields.io/badge/Django-5.0-green)
![Gemini](https://img.shields.io/badge/AI-Gemini%202.0-orange)
![Tests](https://img.shields.io/badge/Tests-60%2B%20passing-brightgreen)

> **AI-powered QA Automation Platform** — Production-grade, built from zero to deployment.
> Django · Selenium · Pytest · LangChain · Gemini AI · Web Scraping · CI/CD

---

## 🎯 What is QA-Pilot?

QA-Pilot is a full-stack QA Automation platform that demonstrates everything a senior QA Engineer needs to know — in one production-grade project. It combines real web scraping, AI-powered test generation, self-healing Selenium selectors, and a full test automation pipeline with CI/CD.

---

## ✅ Live Features

| Feature | Status | Description |
|---------|--------|-------------|
| 🌐 Dark UI Dashboard | ✅ Live | Real-time stats, Chart.js trends, WebSocket-ready |
| 🕷️ Web Scraper | ✅ Working | Headless Chrome scrapes Wikipedia (238 rows), Hacker News |
| 🤖 AI Test Generator | ✅ Working | Gemini 2.0 Flash writes real pytest code from descriptions |
| 🔍 Failure Analyzer | ✅ Working | AI reads test logs → root cause + fix suggestion |
| 🏥 Self-Healing Selector | ✅ Working | Broken CSS/XPath → AI finds new selector automatically |
| 💬 AI Chat Assistant | ✅ Working | Ask anything about QA automation |
| ▶️ Test Runner | ✅ Working | Executes pytest directly, shows pass/fail in UI |
| 📊 Scraped Data Viewer | ✅ Working | Table view, JSON view, Pytest fixture export, CSV download |
| 🔐 Django Admin | ✅ Working | Full model management |
| 🔄 CI/CD Pipeline | ✅ Green | GitHub Actions — 4 test types on every push |

---

## 🧪 Testing — 5 Types, 60+ Tests

| Type | Tests | What it covers |
|------|-------|----------------|
| **Unit** | 29 | Scraper hash/normalize, parametrized with real scraped data, AI agent logic |
| **API** | 16 | Every Django endpoint — health, dashboard, suites, runs, scraper |
| **Integration** | 10 | Django ORM + PostgreSQL — User, TestSuite, TestCase, ScrapedData models |
| **E2E** | 12 | Selenium headless Chrome — page loads, sidebar, admin panel, navigation |
| **Performance** | Locust | Load tests with scraped data as realistic payloads |

### 🕷️ Web Scraping → Real Test Fixtures

```python
# Scrape Wikipedia → normalize → use as pytest parametrize fixtures
@pytest.mark.parametrize("country_data", [
    {"rank": 1, "country": "India", "population": 1428627663, "region": "Asia"},
    {"rank": 2, "country": "China", "population": 1425671352, "region": "Asia"},
    {"rank": 3, "country": "United States", "population": 335893238, "region": "Americas"},
])
def test_country_data_has_required_fields(country_data):
    """Every scraped row must have rank, country, population, region."""
    required = {"rank", "country", "population", "region"}
    assert required.issubset(country_data.keys())
```

---

## 🤖 AI Agents (Gemini 2.0 Flash)

### Agent 1 — Test Case Generator
Takes a feature description + scraped data → writes ready-to-run pytest code.
```
Input:  "User login endpoint with JWT authentication"
Output: 5 pytest test functions with parametrize, docstrings, edge cases
```

### Agent 2 — Failure Analyzer
Reads test failure logs → explains root cause in plain English + gives exact fix.
```
Input:  Stack trace + test logs
Output: {"root_cause": "...", "fix_suggestion": "...", "severity": "high"}
```

### Agent 3 — Self-Healing Selector
When a Selenium locator breaks, AI finds the new correct selector automatically.
```
Input:  broken_selector=".btn-login", page_html="<button data-testid='login-btn'>..."
Output: {"new_css_selector": "[data-testid='login-btn']", "confidence": 0.95}
```

---

## 🏗️ Architecture

```
qa_pilot/
├── apps/
│   ├── core/           # User, TestSuite, TestCase, TestRun, BugReport models + all Django APIs
│   ├── scraper/        # Selenium engine, ScraperTarget, ScrapedData, Celery tasks
│   ├── testrunner/     # pytest subprocess executor, Celery tasks
│   └── agents/         # LangChain + Gemini AI agents
├── config/
│   ├── settings/       # base · local · ci · production
│   ├── celery_app.py   # Beat schedule (scrape every 6h, nightly test runs)
│   └── urls.py
├── frontend/
│   ├── static/         # CSS (dark neon theme), JS
│   └── templates/      # Dashboard, Suites, Runs, Scraper, AI pages
├── tests/
│   ├── unit/           # 29 tests — pure Python, no heavy deps
│   ├── api/            # 16 tests — Django TestClient
│   ├── integration/    # 10 tests — PostgreSQL ORM pipeline
│   ├── e2e/            # 12 tests — Selenium Chrome
│   └── performance/    # Locust load tests
├── docker/             # Dockerfiles (Django + FastAPI)
├── .github/workflows/  # Full CI/CD — 4 parallel jobs
├── docker-compose.yml  # 6 services
├── Makefile
└── pytest.ini
```

---

## ⚡ Quick Start (Local)

```bash
# 1. Clone
git clone https://github.com/tushar-kumar-9354/qa-pilot.git
cd qa-pilot

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Setup environment
copy .env.example .env   # Windows
# cp .env.example .env   # Mac/Linux

# 5. Edit .env — set your values
# GEMINI_API_KEY=your_gemini_api_key
# POSTGRES_PASSWORD=your_password

# 6. Create PostgreSQL database
# Run in pgAdmin: CREATE DATABASE qa_pilot;

# 7. Run migrations
set DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py migrate
python manage.py createsuperuser

# 8. Start server
python manage.py runserver
```

Open `http://localhost:8000` — dashboard is live!

---

## 🐳 Docker Start (Full Stack)

```bash
# One command — starts Django + PostgreSQL + Redis + Celery + Flower
make setup

# Access:
# Django:  http://localhost:8000       (admin / admin123)
# Flower:  http://localhost:5555       (Celery monitor)
```

---

## 🔄 CI/CD Pipeline (GitHub Actions)

4 jobs run on every push to `main`:

```
Push to main
    │
    ├── Unit Tests (29 tests)          ~20s  ✅
    ├── API Tests (16 tests)           ~30s  ✅
    ├── Integration Tests (PostgreSQL) ~45s  ✅
    └── E2E Tests (Selenium Chrome)    ~60s  ✅
```

---

## 📋 Key Commands

```bash
# Run tests
pytest tests/unit/ -v                    # Unit tests only
pytest tests/api/ -v                     # API tests
pytest tests/integration/ -v             # Integration tests
pytest tests/e2e/ -v                     # E2E Selenium tests
pytest tests/ -v --cov=apps              # All + coverage

# Django
python manage.py runserver               # Start server
python manage.py migrate                 # Run migrations
python manage.py createsuperuser         # Create admin

# Docker
make run                                 # Start all services
make test                                # Run all tests
make scrape                              # Trigger scraper
make logs                                # Tail logs
make clean                               # Remove containers
```

---

## 🔑 Environment Variables

```env
DJANGO_SECRET_KEY=your-secret-key
GEMINI_API_KEY=your_gemini_api_key      # Required for AI features
POSTGRES_PASSWORD=your_password
GEMINI_MODEL=gemini-2.0-flash
```

---

## 📊 Tech Stack

| Category | Technology |
|----------|-----------|
| **Backend** | Python 3.11 · Django 5 · Celery · PostgreSQL · Redis |
| **API** | Django REST Framework · JWT Auth · FastAPI (optional) |
| **AI** | Google Gemini 2.0 Flash · LangChain · LangChain Memory |
| **Scraping** | Selenium 4 · BeautifulSoup4 · fake-useragent |
| **Testing** | Pytest 8 · pytest-django · Selenium · Locust · Allure |
| **Frontend** | HTML5 · CSS3 · Vanilla JS · Chart.js · WebSockets |
| **DevOps** | Docker · Docker Compose · GitHub Actions · Render |

---

## 👨‍💻 Built By

**Tushar Kumar** — Software Developer

[![GitHub](https://img.shields.io/badge/GitHub-tushar--kumar--9354-black)](https://github.com/tushar-kumar-9354)
[![Portfolio](https://img.shields.io/badge/Portfolio-Live-blue)](https://0tushar-portfolio0.netlify.app/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://www.linkedin.com/in/tusharkumar-a0a013326/)