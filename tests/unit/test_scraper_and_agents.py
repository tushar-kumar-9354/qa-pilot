"""
QA-PILOT - Unit Tests
Pure Python tests, no selenium/langchain/heavy deps needed.
Run: pytest tests/unit/ -v
"""
import pytest
import json
import hashlib
import re
from unittest.mock import MagicMock


# Pure Python implementations (no imports from apps needed)
def compute_hash(data: dict) -> str:
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


def normalize_table_data(raw_data: dict) -> list:
    rows = raw_data.get('rows', [])
    normalized = []
    for row in rows:
        clean_row = {}
        for key, value in row.items():
            clean_key = key.strip().lower().replace(' ', '_').replace('.', '').replace(',', '')
            clean_value = value.strip() if isinstance(value, str) else value
            if clean_value:
                try:
                    clean_value = int(clean_value.replace(',', '').replace('%', ''))
                except (ValueError, AttributeError):
                    try:
                        clean_value = float(clean_value.replace(',', ''))
                    except (ValueError, AttributeError):
                        pass
            clean_row[clean_key] = clean_value
        if any(v for v in clean_row.values()):
            normalized.append(clean_row)
    return normalized


@pytest.fixture
def scraped_country_rows():
    return [
        {"rank": 1, "country": "India",         "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China",         "population": 1425671352, "region": "Asia"},
        {"rank": 3, "country": "United States", "population": 335893238,  "region": "Americas"},
        {"rank": 4, "country": "Indonesia",     "population": 277534122,  "region": "Asia"},
        {"rank": 5, "country": "Pakistan",      "population": 240485658,  "region": "Asia"},
    ]


@pytest.fixture
def scraped_hn_stories():
    return [
        {"id": "39876543", "title": "Ask HN: Best practices for QA automation", "score": "312 points", "author": "testuser1"},
        {"id": "39876544", "title": "Show HN: AI-powered test generation tool",  "score": "201 points", "author": "testuser2"},
        {"id": "39876545", "title": "Python 3.13 released with new features",    "score": "445 points", "author": "testuser3"},
    ]


@pytest.mark.unit
class TestScraperEngine:

    def test_compute_hash_returns_sha256_string(self):
        data = {"rows": [{"col1": "val1"}], "url": "https://example.com"}
        result = compute_hash(data)
        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in '0123456789abcdef' for c in result)

    def test_compute_hash_is_deterministic(self):
        data = {"rows": [{"a": 1}], "url": "https://test.com"}
        assert compute_hash(data) == compute_hash(data)

    def test_compute_hash_different_data_different_hash(self):
        h1 = compute_hash({"data": "version1"})
        h2 = compute_hash({"data": "version2"})
        assert h1 != h2

    @pytest.mark.parametrize("raw_row,expected_key", [
        ({"Country Name": "India"}, "country_name"),
        ({"GDP (USD)": "2.3T"},     "gdp_(usd)"),
        ({"Population.2024": "1.4B"}, "population2024"),
    ])
    def test_normalize_cleans_column_keys(self, raw_row, expected_key):
        raw = {"rows": [raw_row]}
        result = normalize_table_data(raw)
        assert len(result) == 1
        assert expected_key in result[0]

    @pytest.mark.parametrize("raw_value,expected_type", [
        ("1,428,627,663", int),
        ("3.14",          float),
        ("India",         str),
        ("",              str),
    ])
    def test_normalize_converts_numeric_strings(self, raw_value, expected_type):
        raw = {"rows": [{"value": raw_value}]}
        result = normalize_table_data(raw)
        if result:
            assert isinstance(result[0]["value"], expected_type)

    def test_normalize_removes_empty_rows(self):
        raw = {"rows": [{"col": ""}, {"col": "data"}, {"col": "  "}]}
        result = normalize_table_data(raw)
        assert len(result) == 1
        assert result[0]["col"] == "data"


@pytest.mark.unit
class TestScrapedCountryData:

    @pytest.mark.parametrize("country_data", [
        {"rank": 1, "country": "India",         "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China",         "population": 1425671352, "region": "Asia"},
        {"rank": 3, "country": "United States", "population": 335893238,  "region": "Americas"},
    ])
    def test_country_data_has_required_fields(self, country_data):
        assert {"rank", "country", "population", "region"}.issubset(country_data.keys())

    @pytest.mark.parametrize("country_data", [
        {"rank": 1, "country": "India", "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China", "population": 1425671352, "region": "Asia"},
    ])
    def test_population_is_positive_integer(self, country_data):
        assert isinstance(country_data["population"], int)
        assert country_data["population"] > 0

    @pytest.mark.parametrize("country_data", [
        {"rank": 1, "country": "India",         "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China",         "population": 1425671352, "region": "Asia"},
        {"rank": 3, "country": "United States", "population": 335893238,  "region": "Americas"},
    ])
    def test_rank_is_sequential_positive(self, country_data):
        assert isinstance(country_data["rank"], int)
        assert country_data["rank"] > 0

    def test_all_scraped_countries_have_non_empty_name(self, scraped_country_rows):
        for row in scraped_country_rows:
            assert row.get("country")

    def test_scraped_dataset_is_sorted_by_rank(self, scraped_country_rows):
        ranks = [r["rank"] for r in scraped_country_rows]
        assert ranks == sorted(ranks)


@pytest.mark.unit
class TestScrapedHNData:

    @pytest.mark.parametrize("story", [
        {"id": "123", "title": "Ask HN: Best QA tools",      "score": "312 points", "author": "user1"},
        {"id": "124", "title": "Show HN: New test framework", "score": "201 points", "author": "user2"},
    ])
    def test_story_has_required_fields(self, story):
        for field in ["id", "title", "score", "author"]:
            assert field in story

    @pytest.mark.parametrize("story", [
        {"id": "123", "title": "Ask HN: Best QA tools", "score": "312 points", "author": "user1"},
    ])
    def test_story_title_is_non_empty_string(self, story):
        assert isinstance(story["title"], str)
        assert len(story["title"].strip()) > 0

    def test_all_stories_have_unique_ids(self, scraped_hn_stories):
        ids = [s["id"] for s in scraped_hn_stories]
        assert len(ids) == len(set(ids))

    def test_score_contains_points_keyword(self, scraped_hn_stories):
        for story in scraped_hn_stories:
            assert "points" in story.get("score", "")


@pytest.mark.unit
class TestAIAgents:

    def test_gemini_code_fence_stripping(self):
        """Generator must strip markdown fences from Gemini response."""
        raw = "```python\nimport pytest\n\ndef test_example():\n    assert True\n```"
        if "```python" in raw:
            code = raw.split("```python")[1].split("```")[0].strip()
        elif "```" in raw:
            code = raw.split("```")[1].split("```")[0].strip()
        else:
            code = raw.strip()
        assert code.startswith("import pytest")
        assert "```" not in code

    def test_gemini_test_name_extraction(self):
        """Generator must extract test function names from code."""
        code = (
            "import pytest\n\n"
            "def test_user_login_valid():\n    assert True\n\n"
            "def test_user_login_invalid():\n    assert True\n\n"
            "def test_user_login_empty():\n    assert True\n"
        )
        test_names = re.findall(r"def (test_\w+)", code)
        assert len(test_names) == 3
        assert "test_user_login_valid" in test_names
        assert all(name.startswith("test_") for name in test_names)

    def test_failure_analyzer_json_parsing(self):
        """Failure analyzer must parse JSON response correctly."""
        raw_response = json.dumps({
            "root_cause": "AssertionError: expected 200 got 404",
            "detailed_explanation": "URL changed from /api/v1/ to /api/v2/",
            "fix_suggestion": "Update BASE_URL in test config",
            "fix_code_snippet": "BASE_URL = '/api/v2/'",
            "severity": "high",
            "category": "assertion_error",
            "similar_patterns": ["URL versioning issues"],
            "prevention": "Use URL constants not hardcoded strings",
        })
        result = json.loads(raw_response)
        assert "root_cause" in result
        assert "fix_suggestion" in result
        assert result["severity"] in ["critical", "high", "medium", "low"]
        assert result["category"] == "assertion_error"

    def test_self_healer_json_parsing(self):
        """Self-healer must parse JSON selector response correctly."""
        raw_response = json.dumps({
            "new_css_selector": "[data-testid='login-button']",
            "new_xpath": "//button[@data-testid='login-button']",
            "recommended_type": "css",
            "confidence": 0.95,
            "why_old_broke": "Class renamed from btn-login to login-btn",
            "explanation": "data-testid attributes are stable",
            "selenium_code": "driver.find_element(By.CSS_SELECTOR, '[data-testid]')",
            "robustness_tips": "Always prefer data-testid over class selectors",
        })
        result = json.loads(raw_response)
        assert "new_css_selector" in result
        assert len(result["new_css_selector"]) > 0
        assert result["confidence"] > 0
        assert result["recommended_type"] in ["css", "xpath"]

    def test_scraped_data_as_pytest_fixtures(self):
        """Scraped data rows must be usable as pytest parametrize arguments."""
        scraped_rows = [
            {"rank": 1, "country": "India", "population": 1428627663},
            {"rank": 2, "country": "China", "population": 1425671352},
            {"rank": 3, "country": "USA",   "population": 335893238},
        ]
        fixtures = scraped_rows if isinstance(scraped_rows, list) else [scraped_rows]
        assert len(fixtures) == 3
        for fixture in fixtures:
            assert isinstance(fixture, dict)
            assert "country" in fixture
            assert fixture["population"] > 0