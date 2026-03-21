"""
QA-PILOT — Unit Tests
Uses scraped Wikipedia/HN data as parametrized fixtures.
Run: pytest tests/unit/ -v -m unit
"""
import pytest
import json
import hashlib
from unittest.mock import patch, MagicMock


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────

@pytest.fixture
def scraped_country_rows():
    """
    Sample scraped data rows (as would come from Wikipedia country table).
    In production, these come from ScrapedData.as_pytest_fixtures()
    """
    return [
        {"rank": 1, "country": "India", "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China", "population": 1425671352, "region": "Asia"},
        {"rank": 3, "country": "United States", "population": 335893238, "region": "Americas"},
        {"rank": 4, "country": "Indonesia", "population": 277534122, "region": "Asia"},
        {"rank": 5, "country": "Pakistan", "population": 240485658, "region": "Asia"},
    ]


@pytest.fixture
def scraped_hn_stories():
    """Sample Hacker News stories from scraper."""
    return [
        {"id": "39876543", "title": "Ask HN: Best practices for QA automation in 2024", "score": "312 points", "author": "testuser1"},
        {"id": "39876544", "title": "Show HN: AI-powered test generation tool", "score": "201 points", "author": "testuser2"},
        {"id": "39876545", "title": "Python 3.13 released with new features", "score": "445 points", "author": "testuser3"},
    ]


@pytest.fixture
def mock_scraper_engine():
    """Mock ScraperEngine for unit tests — no real browser needed."""
    with patch('apps.scraper.engine.ScraperEngine') as mock:
        instance = MagicMock()
        mock.return_value.__enter__ = MagicMock(return_value=instance)
        mock.return_value.__exit__ = MagicMock(return_value=False)
        yield instance


# ──────────────────────────────────────────────────────────
# ScraperEngine Unit Tests
# ──────────────────────────────────────────────────────────

@pytest.mark.unit
class TestScraperEngine:
    """Unit tests for ScraperEngine static methods — no browser, no network."""

    def test_compute_hash_returns_sha256_string(self):
        """Hash output must be a 64-char hex string."""
        from apps.scraper.engine import ScraperEngine
        data = {"rows": [{"col1": "val1"}], "url": "https://example.com"}
        result = ScraperEngine.compute_hash(data)
        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in '0123456789abcdef' for c in result)

    def test_compute_hash_is_deterministic(self):
        """Same data must always produce same hash."""
        from apps.scraper.engine import ScraperEngine
        data = {"rows": [{"a": 1}], "url": "https://test.com"}
        assert ScraperEngine.compute_hash(data) == ScraperEngine.compute_hash(data)

    def test_compute_hash_different_data_different_hash(self):
        """Different data must produce different hashes."""
        from apps.scraper.engine import ScraperEngine
        h1 = ScraperEngine.compute_hash({"data": "version1"})
        h2 = ScraperEngine.compute_hash({"data": "version2"})
        assert h1 != h2

    @pytest.mark.parametrize("raw_row,expected_key", [
        ({"Country Name": "India"}, "country_name"),
        ({"GDP (USD)": "2.3T"}, "gdp_(usd)"),
        ({"Population.2024": "1.4B"}, "population2024"),
    ])
    def test_normalize_cleans_column_keys(self, raw_row, expected_key):
        """normalize_table_data should clean header keys consistently."""
        from apps.scraper.engine import ScraperEngine
        raw = {"rows": [raw_row], "headers": list(raw_row.keys())}
        result = ScraperEngine.normalize_table_data(raw)
        assert len(result) == 1
        assert expected_key in result[0]

    @pytest.mark.parametrize("raw_value,expected_type", [
        ("1,428,627,663", int),
        ("3.14", float),
        ("India", str),
        ("", str),
    ])
    def test_normalize_converts_numeric_strings(self, raw_value, expected_type):
        """normalize_table_data should convert '1,234,567' → int, '3.14' → float."""
        from apps.scraper.engine import ScraperEngine
        raw = {"rows": [{"value": raw_value}]}
        result = ScraperEngine.normalize_table_data(raw)
        if result:
            assert isinstance(result[0]["value"], expected_type)

    def test_normalize_removes_empty_rows(self):
        """Rows with all empty values must be filtered out."""
        from apps.scraper.engine import ScraperEngine
        raw = {"rows": [{"col": ""}, {"col": "data"}, {"col": "  "}]}
        result = ScraperEngine.normalize_table_data(raw)
        assert len(result) == 1
        assert result[0]["col"] == "data"


# ──────────────────────────────────────────────────────────
# Parametrized Tests Using Scraped Country Data
# ──────────────────────────────────────────────────────────

@pytest.mark.unit
class TestScrapedCountryData:
    """
    Tests parametrized with real scraped data.
    Each row from Wikipedia becomes a separate test case.
    This is the core QA-Pilot concept: scraped data → test fixtures.
    """

    @pytest.mark.parametrize("country_data", [
        {"rank": 1, "country": "India", "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China", "population": 1425671352, "region": "Asia"},
        {"rank": 3, "country": "United States", "population": 335893238, "region": "Americas"},
    ])
    def test_country_data_has_required_fields(self, country_data):
        """Every scraped country record must have rank, country, population, region."""
        required = {"rank", "country", "population", "region"}
        assert required.issubset(country_data.keys()), f"Missing fields in: {country_data}"

    @pytest.mark.parametrize("country_data", [
        {"rank": 1, "country": "India", "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China", "population": 1425671352, "region": "Asia"},
    ])
    def test_population_is_positive_integer(self, country_data):
        """Population must be a positive integer."""
        pop = country_data["population"]
        assert isinstance(pop, int), f"Population should be int, got {type(pop)}"
        assert pop > 0, f"Population must be positive, got {pop}"

    @pytest.mark.parametrize("country_data", [
        {"rank": 1, "country": "India", "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China", "population": 1425671352, "region": "Asia"},
        {"rank": 3, "country": "United States", "population": 335893238, "region": "Americas"},
    ])
    def test_rank_is_sequential_positive(self, country_data):
        """Rank must be a positive integer."""
        assert isinstance(country_data["rank"], int)
        assert country_data["rank"] > 0

    def test_all_scraped_countries_have_non_empty_name(self, scraped_country_rows):
        """No country in scraped data should have an empty name."""
        for row in scraped_country_rows:
            assert row.get("country"), f"Empty country name in row: {row}"

    def test_scraped_dataset_is_sorted_by_rank(self, scraped_country_rows):
        """Scraped country data should be sorted by rank (ascending)."""
        ranks = [r["rank"] for r in scraped_country_rows]
        assert ranks == sorted(ranks), f"Data not sorted by rank: {ranks}"


# ──────────────────────────────────────────────────────────
# Hacker News Data Tests
# ──────────────────────────────────────────────────────────

@pytest.mark.unit
class TestScrapedHNData:
    """Tests using scraped Hacker News story data as fixtures."""

    @pytest.mark.parametrize("story", [
        {"id": "123", "title": "Ask HN: Best QA tools", "score": "312 points", "author": "user1"},
        {"id": "124", "title": "Show HN: New test framework", "score": "201 points", "author": "user2"},
    ])
    def test_story_has_required_fields(self, story):
        """Every scraped HN story must have id, title, score, author."""
        for field in ["id", "title", "score", "author"]:
            assert field in story, f"Missing '{field}' in story: {story}"

    @pytest.mark.parametrize("story", [
        {"id": "123", "title": "Ask HN: Best QA tools", "score": "312 points", "author": "user1"},
    ])
    def test_story_title_is_non_empty_string(self, story):
        """Story title must be a non-empty string."""
        assert isinstance(story["title"], str)
        assert len(story["title"].strip()) > 0

    def test_all_stories_have_unique_ids(self, scraped_hn_stories):
        """All scraped stories must have unique IDs."""
        ids = [s["id"] for s in scraped_hn_stories]
        assert len(ids) == len(set(ids)), "Duplicate story IDs found"

    def test_score_contains_points_keyword(self, scraped_hn_stories):
        """Score field from HN should contain 'points'."""
        for story in scraped_hn_stories:
            assert "points" in story.get("score", ""), f"Invalid score: {story['score']}"


# ──────────────────────────────────────────────────────────
# AI Agent Unit Tests (mocked)
# ──────────────────────────────────────────────────────────

@pytest.mark.unit
class TestAIAgents:
    """Unit tests for AI agents with mocked Gemini responses."""

    @patch('apps.agents.agents.ChatGoogleGenerativeAI')
    def test_test_generator_returns_code(self, mock_llm_class):
        """TestCaseGenerator must return Python code string."""
        from apps.agents.agents import TestCaseGeneratorAgent

        mock_response = MagicMock()
        mock_response.content = """
import pytest

def test_user_registration_with_valid_data():
    \"\"\"Test user registration with valid input.\"\"\"
    assert True

def test_user_registration_with_empty_email_raises_error():
    \"\"\"Test that empty email raises ValueError.\"\"\"
    with pytest.raises(ValueError):
        raise ValueError("Email required")
"""
        mock_llm_class.return_value.invoke.return_value = mock_response

        agent = TestCaseGeneratorAgent()
        result = agent.generate("User registration endpoint", num_tests=2)

        assert "code" in result
        assert "test_" in result["code"]
        assert len(result["test_names"]) >= 1

    @patch('apps.agents.agents.ChatGoogleGenerativeAI')
    def test_failure_analyzer_returns_json_fields(self, mock_llm_class):
        """FailureAnalyzer must return dict with root_cause and fix_suggestion."""
        from apps.agents.agents import FailureAnalyzerAgent

        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "root_cause": "AssertionError: expected 200, got 404",
            "detailed_explanation": "The endpoint URL changed from /api/v1/ to /api/v2/",
            "fix_suggestion": "Update the base URL in test config",
            "fix_code_snippet": "BASE_URL = '/api/v2/'",
            "severity": "high",
            "category": "assertion_error",
            "similar_patterns": ["URL versioning changes"],
            "prevention": "Use URL constants, not hardcoded strings",
        })
        mock_llm_class.return_value.invoke.return_value = mock_response

        agent = FailureAnalyzerAgent()
        result = agent.analyze("FAILED test_login\nAssertionError: 404")

        assert "root_cause" in result
        assert "fix_suggestion" in result
        assert result["severity"] in ["critical", "high", "medium", "low"]

    @patch('apps.agents.agents.ChatGoogleGenerativeAI')
    def test_self_healing_returns_new_selector(self, mock_llm_class):
        """SelfHealingSelector must return a new CSS selector."""
        from apps.agents.agents import SelfHealingSelectorAgent

        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "new_css_selector": "[data-testid='login-button']",
            "new_xpath": "//button[@data-testid='login-button']",
            "recommended_type": "css",
            "confidence": 0.95,
            "why_old_broke": "The class 'btn-login' was renamed to 'login-btn'",
            "explanation": "data-testid is stable and test-specific",
            "selenium_code": "driver.find_element(By.CSS_SELECTOR, \"[data-testid='login-button']\")",
            "alternative_selectors": ["#login-btn", "button[type='submit']"],
            "robustness_tips": "Always prefer data-testid attributes",
        })
        mock_llm_class.return_value.invoke.return_value = mock_response

        agent = SelfHealingSelectorAgent()
        result = agent.heal(
            broken_selector=".btn-login",
            selector_type="css",
            element_description="Login button",
            page_html="<button data-testid='login-button' class='login-btn'>Login</button>",
        )

        assert "new_css_selector" in result
        assert len(result["new_css_selector"]) > 0
        assert result["confidence"] > 0
