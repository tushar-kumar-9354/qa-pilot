"""
QA-PILOT — Global Pytest conftest.py
Shared fixtures available across all test types.
"""
import pytest
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')


@pytest.fixture(scope='session')
def django_db_setup():
    """Use test database for all DB-hitting tests."""
    pass


@pytest.fixture
def scraped_wikipedia_data():
    """
    Provides realistic scraped country data as test fixtures.
    In production this comes from ScrapedData.as_pytest_fixtures().
    """
    return [
        {"rank": 1, "country": "India", "population": 1428627663, "area_km2": 3287263, "region": "Asia"},
        {"rank": 2, "country": "China", "population": 1425671352, "area_km2": 9596960, "region": "Asia"},
        {"rank": 3, "country": "United States", "population": 335893238, "area_km2": 9833517, "region": "Americas"},
        {"rank": 4, "country": "Indonesia", "population": 277534122, "area_km2": 1904569, "region": "Asia"},
        {"rank": 5, "country": "Pakistan", "population": 240485658, "area_km2": 881913, "region": "Asia"},
        {"rank": 6, "country": "Brazil", "population": 216422446, "area_km2": 8515767, "region": "Americas"},
        {"rank": 7, "country": "Nigeria", "population": 223804632, "area_km2": 923768, "region": "Africa"},
        {"rank": 8, "country": "Bangladesh", "population": 172954319, "area_km2": 147570, "region": "Asia"},
    ]


@pytest.fixture
def scraped_hn_data():
    """Provides realistic scraped HN stories as fixtures."""
    return [
        {"id": "39876001", "title": "Ask HN: What makes a great QA engineer?", "score": "312 points", "author": "qa_dev"},
        {"id": "39876002", "title": "Show HN: pytest plugin for AI test generation", "score": "201 points", "author": "pytest_fan"},
        {"id": "39876003", "title": "Selenium 4 — new features and migration guide", "score": "445 points", "author": "webdev"},
        {"id": "39876004", "title": "Why I switched from unittest to pytest", "score": "178 points", "author": "python_dev"},
        {"id": "39876005", "title": "LangChain + Gemini for test automation", "score": "289 points", "author": "ai_tester"},
    ]
print("Django setup complete in conftest.py")

@pytest.fixture
def api_client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from fastapi_app.main import app
    return TestClient(app)
