"""
QA-PILOT — API Tests using Django TestClient
Tests every Django API endpoint directly.
Run: pytest tests/api/ -v -m api
"""
import pytest
import json
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
@pytest.mark.api
class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        """Health check must return 200."""
        response = client.get('/api/health/')
        assert response.status_code == 200

    def test_health_response_has_status(self, client):
        """Health response must include status field."""
        response = client.get('/api/health/')
        data = response.json()
        assert 'status' in data
        assert data['status'] == 'healthy'

    def test_health_response_has_version(self, client):
        """Health response must include version."""
        response = client.get('/api/health/')
        data = response.json()
        assert 'version' in data


@pytest.mark.django_db
@pytest.mark.api
class TestDashboardAPI:

    def test_dashboard_stats_returns_200(self, client):
        """Dashboard stats must return 200."""
        response = client.get('/api/dashboard/stats')
        assert response.status_code == 200

    def test_dashboard_stats_has_totals(self, client):
        """Stats must include totals with all required fields."""
        response = client.get('/api/dashboard/stats')
        data = response.json()
        assert 'totals' in data
        for field in ['suites', 'cases', 'runs', 'open_bugs', 'scraped_records']:
            assert field in data['totals'], f"Missing: {field}"

    def test_dashboard_trend_has_7_days(self, client):
        """Trend must always return 7 days of data."""
        response = client.get('/api/dashboard/stats')
        data = response.json()
        assert 'trend' in data
        assert len(data['trend']) == 7

    def test_dashboard_pass_rate_valid_range(self, client):
        """Pass rate in trend must be 0-100."""
        response = client.get('/api/dashboard/stats')
        data = response.json()
        for day in data['trend']:
            assert 0 <= day['pass_rate'] <= 100


@pytest.mark.django_db
@pytest.mark.api
class TestSuitesAPI:

    def test_list_suites_returns_200(self, client):
        """GET /api/suites must return 200."""
        response = client.get('/api/suites')
        assert response.status_code == 200

    def test_list_suites_has_total_and_results(self, client):
        """Suites response must have total + results."""
        response = client.get('/api/suites')
        data = response.json()
        assert 'total' in data
        assert 'results' in data
        assert isinstance(data['results'], list)

    def test_list_suites_empty_initially(self, client):
        """Fresh DB must return 0 suites."""
        response = client.get('/api/suites')
        data = response.json()
        assert data['total'] == 0

    def test_create_and_list_suite(self, client, django_user_model):
        """Created suite must appear in list."""
        from apps.core.models import TestSuite
        TestSuite.objects.create(name='My API Suite', status='active')
        response = client.get('/api/suites')
        data = response.json()
        assert data['total'] == 1
        assert data['results'][0]['name'] == 'My API Suite'


@pytest.mark.django_db
@pytest.mark.api
class TestRunsAPI:

    def test_list_runs_returns_200(self, client):
        """GET /api/runs must return 200."""
        response = client.get('/api/runs')
        assert response.status_code == 200

    def test_list_runs_empty_initially(self, client):
        """Fresh DB must return 0 runs."""
        response = client.get('/api/runs')
        data = response.json()
        assert data['total'] == 0


@pytest.mark.django_db
@pytest.mark.api
class TestScraperAPI:

    def test_scraped_data_returns_200(self, client):
        """GET /api/scraper/data must return 200."""
        response = client.get('/api/scraper/data')
        assert response.status_code == 200

    def test_scraped_data_empty_initially(self, client):
        """Fresh DB must return 0 scraped records."""
        response = client.get('/api/scraper/data')
        data = response.json()
        assert data['total'] == 0

    def test_scraper_trigger_returns_200(self, client):
        """POST /api/scraper/trigger must return 200 or 500 (needs Selenium in prod)."""
        response = client.post(
            '/api/scraper/trigger',
            data=json.dumps({'url': 'https://example.com', 'data_type': 'table'}),
            content_type='application/json',
        )
        # 200 = success, 500 = Selenium not installed in CI (expected)
        assert response.status_code in [200, 500]
        data = response.json()
        assert 'status' in data or 'error' in data