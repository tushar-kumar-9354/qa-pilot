"""
QA-PILOT — API Tests
Tests every FastAPI endpoint using the TestClient + scraped data as payloads.
Run: pytest tests/api/ -v -m api
"""
import pytest
import json
from httpx import AsyncClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def scraped_hn_titles():
    """Real scraped HN titles used as API test payloads — real edge cases."""
    return [
        "Ask HN: What tools do you use for QA automation?",
        "Show HN: I built a self-healing Selenium framework",
        "AI-powered test case generation with LangChain + Gemini",
        "Python 3.13 – what's new?",
        "Why 80% code coverage is a lie",
    ]


@pytest.fixture
def fastapi_client():
    """FastAPI async test client."""
    from fastapi.testclient import TestClient
    from fastapi_app.main import app
    return TestClient(app)


# ──────────────────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────────────────

@pytest.mark.api
class TestHealthEndpoint:

    def test_health_returns_200(self, fastapi_client):
        """Health check must return 200 OK."""
        response = fastapi_client.get("/health")
        assert response.status_code == 200

    def test_health_response_has_status_field(self, fastapi_client):
        """Health response must include 'status' field."""
        response = fastapi_client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]

    def test_health_response_has_services(self, fastapi_client):
        """Health response must include services dict."""
        response = fastapi_client.get("/health")
        data = response.json()
        assert "services" in data
        assert "database" in data["services"]
        assert "redis" in data["services"]

    def test_health_response_has_timestamp(self, fastapi_client):
        """Health response must include ISO timestamp."""
        response = fastapi_client.get("/health")
        data = response.json()
        assert "timestamp" in data
        assert "T" in data["timestamp"]  # ISO 8601 format


# ──────────────────────────────────────────────────────────
# Test Suites API
# ──────────────────────────────────────────────────────────

@pytest.mark.api
class TestSuitesAPI:

    def test_list_suites_returns_200(self, fastapi_client):
        """GET /api/suites must return 200."""
        response = fastapi_client.get("/api/suites")
        assert response.status_code == 200

    def test_list_suites_response_structure(self, fastapi_client):
        """Suites response must have total, page, results fields."""
        response = fastapi_client.get("/api/suites")
        data = response.json()
        assert "total" in data
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_list_suites_pagination_page_1(self, fastapi_client):
        """Default page=1 must work."""
        response = fastapi_client.get("/api/suites?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 5

    def test_list_suites_invalid_page_returns_422(self, fastapi_client):
        """page=0 (invalid) must return 422 Unprocessable Entity."""
        response = fastapi_client.get("/api/suites?page=0")
        assert response.status_code == 422

    def test_list_suites_search_filter(self, fastapi_client):
        """Search parameter must filter results."""
        response = fastapi_client.get("/api/suites?search=nonexistentsuite12345")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_get_nonexistent_suite_returns_404(self, fastapi_client):
        """Getting a non-existent suite UUID must return 404."""
        response = fastapi_client.get("/api/suites/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


# ──────────────────────────────────────────────────────────
# AI Agents API — Using Scraped Titles as Test Payloads
# ──────────────────────────────────────────────────────────

@pytest.mark.api
class TestAIAgentsAPI:
    """
    These tests use scraped Hacker News titles as feature descriptions.
    Real world input = real edge cases discovered automatically.
    """

    @patch('apps.agents.agents.ChatGoogleGenerativeAI')
    @pytest.mark.parametrize("feature_desc", [
        "User login with email and password",
        "REST API endpoint that returns paginated results",
        "Web scraper that extracts tables from Wikipedia",
    ])
    def test_generate_tests_with_various_features(self, mock_llm, feature_desc, fastapi_client):
        """AI test generator must accept any feature description."""
        mock_resp = MagicMock()
        mock_resp.content = "import pytest\n\ndef test_example():\n    assert True\n"
        mock_llm.return_value.invoke.return_value = mock_resp

        response = fastapi_client.post("/api/agents/generate-tests", json={
            "feature_description": feature_desc,
            "test_type": "unit",
            "num_tests": 2,
            "use_scraped_data": False,
        })
        assert response.status_code == 200
        data = response.json()
        assert "code" in data

    def test_generate_tests_too_short_description_returns_422(self, fastapi_client):
        """Feature description under 10 chars must return 422."""
        response = fastapi_client.post("/api/agents/generate-tests", json={
            "feature_description": "login",
            "test_type": "unit",
            "num_tests": 3,
        })
        assert response.status_code == 422

    def test_generate_tests_invalid_num_tests_returns_422(self, fastapi_client):
        """num_tests > 20 must return 422."""
        response = fastapi_client.post("/api/agents/generate-tests", json={
            "feature_description": "User authentication with JWT tokens",
            "test_type": "unit",
            "num_tests": 100,
        })
        assert response.status_code == 422

    @patch('apps.agents.agents.ChatGoogleGenerativeAI')
    def test_chat_endpoint_returns_response(self, mock_llm, fastapi_client):
        """Chat endpoint must return a text response."""
        mock_resp = MagicMock()
        mock_resp.content = "Sure, I can help with that test failure."
        mock_llm.return_value.invoke.return_value = mock_resp

        response = fastapi_client.post("/api/agents/chat", json={
            "message": "Why would a Selenium test fail with NoSuchElementException?",
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert len(data["response"]) > 0

    def test_chat_empty_message_returns_422(self, fastapi_client):
        """Empty chat message must return 422."""
        response = fastapi_client.post("/api/agents/chat", json={"message": ""})
        assert response.status_code == 422


# ──────────────────────────────────────────────────────────
# Scraper API
# ──────────────────────────────────────────────────────────

@pytest.mark.api
class TestScraperAPI:

    def test_list_scraped_data_returns_200(self, fastapi_client):
        """GET /api/scraper/data must return 200."""
        response = fastapi_client.get("/api/scraper/data")
        assert response.status_code == 200

    def test_scraped_data_has_total_and_results(self, fastapi_client):
        """Scraped data response must have total + results."""
        response = fastapi_client.get("/api/scraper/data")
        data = response.json()
        assert "total" in data
        assert "results" in data

    @patch('apps.scraper.tasks.scrape_custom_url_task')
    def test_trigger_scrape_returns_task_id(self, mock_task, fastapi_client):
        """Trigger scrape must return a task_id."""
        mock_task.delay.return_value = MagicMock(id="fake-task-id-123")

        response = fastapi_client.post("/api/scraper/trigger", json={
            "url": "https://en.wikipedia.org/wiki/List_of_countries_by_area",
            "data_type": "table",
        })
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "triggered"


# ──────────────────────────────────────────────────────────
# Dashboard Stats API
# ──────────────────────────────────────────────────────────

@pytest.mark.api
class TestDashboardAPI:

    def test_dashboard_stats_returns_200(self, fastapi_client):
        """Dashboard stats endpoint must return 200."""
        response = fastapi_client.get("/api/dashboard/stats")
        assert response.status_code == 200

    def test_dashboard_stats_has_totals(self, fastapi_client):
        """Stats must include totals dict."""
        response = fastapi_client.get("/api/dashboard/stats")
        data = response.json()
        assert "totals" in data
        totals = data["totals"]
        for field in ["suites", "cases", "runs", "open_bugs", "scraped_records"]:
            assert field in totals, f"Missing field: {field}"

    def test_dashboard_stats_trend_has_7_days(self, fastapi_client):
        """Trend must always have exactly 7 days of data."""
        response = fastapi_client.get("/api/dashboard/stats")
        data = response.json()
        assert "trend" in data
        assert len(data["trend"]) == 7

    def test_dashboard_stats_trend_pass_rate_in_range(self, fastapi_client):
        """Pass rate in trend must be 0-100."""
        response = fastapi_client.get("/api/dashboard/stats")
        data = response.json()
        for day in data["trend"]:
            assert 0 <= day["pass_rate"] <= 100, f"Invalid pass rate: {day['pass_rate']}"
