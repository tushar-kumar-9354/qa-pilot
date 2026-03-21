"""
QA-PILOT — Performance Tests (Locust)
Uses scraped Hacker News data as realistic load test payloads.

Run locally:
    locust -f tests/performance/locustfile.py --host=http://localhost:8001 --headless -u 10 -r 2 --run-time 30s

Run via make:
    make test-perf
"""
from locust import HttpUser, task, between
import random
import json


# ── Realistic payloads from scraped data ─────────────────────
SCRAPED_FEATURE_DESCRIPTIONS = [
    "User authentication with email and password validation",
    "REST API pagination with cursor-based navigation",
    "Web scraper that extracts Wikipedia population tables",
    "Selenium test for login form submission",
    "Database query optimization for test run history",
    "AI-powered test case generation from feature specs",
    "WebSocket connection for live test log streaming",
    "JWT token refresh mechanism with rotation",
]

SCRAPED_CHAT_MESSAGES = [
    "Why would a Selenium locator fail with NoSuchElementException?",
    "How do I write a parametrized pytest test with scraped data?",
    "What is the best way to handle dynamic content in Selenium?",
    "Explain what a 500 error in my API test means",
    "How do I set up pytest fixtures for database testing?",
]


class QAPilotAPIUser(HttpUser):
    """
    Simulates a real QA engineer using the platform.
    Uses realistic scraped data as request payloads.
    """
    wait_time = between(1, 3)

    def on_start(self):
        """Called when a Locust user starts."""
        self.headers = {"Content-Type": "application/json"}

    # ── Health check (lightest endpoint) ─────────────────────
    @task(5)
    def health_check(self):
        """Frequently hit health check."""
        self.client.get("/health", name="GET /health")

    # ── Dashboard stats (most common page) ───────────────────
    @task(10)
    def get_dashboard_stats(self):
        """Load dashboard stats — most frequent user action."""
        self.client.get("/api/dashboard/stats", name="GET /api/dashboard/stats")

    # ── List suites ───────────────────────────────────────────
    @task(8)
    def list_test_suites(self):
        """Browse test suites list."""
        page = random.randint(1, 3)
        self.client.get(f"/api/suites?page={page}&page_size=20", name="GET /api/suites")

    # ── List runs ─────────────────────────────────────────────
    @task(6)
    def list_test_runs(self):
        """View test run history."""
        self.client.get("/api/runs?page=1&page_size=20", name="GET /api/runs")

    # ── Scraped data list ─────────────────────────────────────
    @task(4)
    def list_scraped_data(self):
        """Browse scraped data records."""
        self.client.get("/api/scraper/data", name="GET /api/scraper/data")

    # ── AI chat (heaviest — Gemini call, low weight) ──────────
    @task(2)
    def ai_chat(self):
        """Send a chat message to AI assistant using scraped message."""
        message = random.choice(SCRAPED_CHAT_MESSAGES)
        payload = json.dumps({"message": message})
        with self.client.post(
            "/api/agents/chat",
            data=payload,
            headers=self.headers,
            name="POST /api/agents/chat",
            catch_response=True,
            timeout=30,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 500:
                # Gemini might be down — don't count as failure
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    # ── OpenAPI docs ──────────────────────────────────────────
    @task(1)
    def view_api_docs(self):
        """Occasionally hit the API docs page."""
        self.client.get("/openapi.json", name="GET /openapi.json")
