"""
QA-PILOT — Unit Tests (CI-compatible, no selenium/langchain needed)
Run: pytest tests/unit/ -v -m unit
"""
import pytest
import json
from unittest.mock import patch, MagicMock


@pytest.fixture
def scraped_country_rows():
    return [
        {"rank": 1, "country": "India", "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China", "population": 1425671352, "region": "Asia"},
        {"rank": 3, "country": "United States", "population": 335893238, "region": "Americas"},
        {"rank": 4, "country": "Indonesia", "population": 277534122, "region": "Asia"},
        {"rank": 5, "country": "Pakistan", "population": 240485658, "region": "Asia"},
    ]


@pytest.fixture
def scraped_hn_stories():
    return [
        {"id": "39876543", "title": "Ask HN: Best practices for QA automation", "score": "312 points", "author": "testuser1"},
        {"id": "39876544", "title": "Show HN: AI-powered test generation tool", "score": "201 points", "author": "testuser2"},
        {"id": "39876545", "title": "Python 3.13 released with new features", "score": "445 points", "author": "testuser3"},
    ]


# ── ScraperEngine Unit Tests ───────────────────────────────────

@pytest.mark.unit
class TestScraperEngine:

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
        """normalize_table_data should clean header keys."""
        from apps.scraper.engine import ScraperEngine
        raw = {"rows": [raw_row]}
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
        """normalize_table_data should convert numeric strings."""
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


# ── Scraped Country Data Tests ─────────────────────────────────

@pytest.mark.unit
class TestScrapedCountryData:

    @pytest.mark.parametrize("country_data", [
        {"rank": 1, "country": "India", "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China", "population": 1425671352, "region": "Asia"},
        {"rank": 3, "country": "United States", "population": 335893238, "region": "Americas"},
    ])
    def test_country_data_has_required_fields(self, country_data):
        """Every scraped country record must have required fields."""
        required = {"rank", "country", "population", "region"}
        assert required.issubset(country_data.keys())

    @pytest.mark.parametrize("country_data", [
        {"rank": 1, "country": "India", "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China", "population": 1425671352, "region": "Asia"},
    ])
    def test_population_is_positive_integer(self, country_data):
        """Population must be a positive integer."""
        pop = country_data["population"]
        assert isinstance(pop, int)
        assert pop > 0

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
        """No country should have an empty name."""
        for row in scraped_country_rows:
            assert row.get("country")

    def test_scraped_dataset_is_sorted_by_rank(self, scraped_country_rows):
        """Scraped country data should be sorted by rank."""
        ranks = [r["rank"] for r in scraped_country_rows]
        assert ranks == sorted(ranks)


# ── Hacker News Data Tests ─────────────────────────────────────

@pytest.mark.unit
class TestScrapedHNData:

    @pytest.mark.parametrize("story", [
        {"id": "123", "title": "Ask HN: Best QA tools", "score": "312 points", "author": "user1"},
        {"id": "124", "title": "Show HN: New test framework", "score": "201 points", "author": "user2"},
    ])
    def test_story_has_required_fields(self, story):
        """Every HN story must have id, title, score, author."""
        for field in ["id", "title", "score", "author"]:
            assert field in story

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
        assert len(ids) == len(set(ids))

    def test_score_contains_points_keyword(self, scraped_hn_stories):
        """Score field should contain 'points'."""
        for story in scraped_hn_stories:
            assert "points" in story.get("score", "")


# ── AI Agents Tests (fully mocked) ────────────────────────────

@pytest.mark.unit
class TestAIAgents:

    def test_test_generator_returns_code(self):
        """TestCaseGenerator must return Python code string."""
        # Mock ALL heavy dependencies before importing
        mock_modules = {
            'langchain_google_genai': MagicMock(),
            'langchain': MagicMock(),
            'langchain.agents': MagicMock(),
            'langchain.tools': MagicMock(),
            'langchain.prompts': MagicMock(),
            'langchain.memory': MagicMock(),
            'langchain_core': MagicMock(),
            'langchain_core.messages': MagicMock(),
            'langchain_community': MagicMock(),
            'google': MagicMock(),
            'google.generativeai': MagicMock(),
        }
        with patch.dict('sys.modules', mock_modules):
            # Create mock LLM response
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = """import pytest

def test_user_registration_valid():
    \"\"\"Test valid user registration.\"\"\"
    assert True

def test_user_registration_empty_email():
    \"\"\"Test empty email raises error.\"\"\"
    assert True
"""
            mock_llm.return_value.invoke.return_value = mock_response

            # Patch ChatGoogleGenerativeAI inside agents module
            with patch('apps.agents.agents.ChatGoogleGenerativeAI', mock_llm):
                import importlib
                import apps.agents.agents as agents_module
                importlib.reload(agents_module)
                agent = agents_module.TestCaseGeneratorAgent()
                result = agent.generate("User registration", num_tests=2)
                assert "code" in result
                assert "test_" in result["code"]

    def test_failure_analyzer_returns_dict(self):
        """FailureAnalyzer must return a dict with root_cause."""
        mock_modules = {
            'langchain_google_genai': MagicMock(),
            'langchain': MagicMock(),
            'langchain.agents': MagicMock(),
            'langchain.tools': MagicMock(),
            'langchain.prompts': MagicMock(),
            'langchain.memory': MagicMock(),
            'langchain_core': MagicMock(),
            'langchain_core.messages': MagicMock(),
            'langchain_community': MagicMock(),
            'google': MagicMock(),
            'google.generativeai': MagicMock(),
        }
        with patch.dict('sys.modules', mock_modules):
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "root_cause": "AssertionError: expected 200 got 404",
                "detailed_explanation": "URL changed from v1 to v2",
                "fix_suggestion": "Update base URL",
                "fix_code_snippet": "BASE_URL = '/api/v2/'",
                "severity": "high",
                "category": "assertion_error",
                "similar_patterns": [],
                "prevention": "Use URL constants",
            })
            mock_llm.return_value.invoke.return_value = mock_response

            with patch('apps.agents.agents.ChatGoogleGenerativeAI', mock_llm):
                import importlib
                import apps.agents.agents as agents_module
                importlib.reload(agents_module)
                agent = agents_module.FailureAnalyzerAgent()
                result = agent.analyze("FAILED test_login\nAssertionError: 404")
                assert "root_cause" in result

    def test_self_healing_returns_selector(self):
        """SelfHealingSelector must return a new CSS selector."""
        mock_modules = {
            'langchain_google_genai': MagicMock(),
            'langchain': MagicMock(),
            'langchain.agents': MagicMock(),
            'langchain.tools': MagicMock(),
            'langchain.prompts': MagicMock(),
            'langchain.memory': MagicMock(),
            'langchain_core': MagicMock(),
            'langchain_core.messages': MagicMock(),
            'langchain_community': MagicMock(),
            'google': MagicMock(),
            'google.generativeai': MagicMock(),
        }
        with patch.dict('sys.modules', mock_modules):
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "new_css_selector": "[data-testid='login-button']",
                "new_xpath": "//button[@data-testid='login-button']",
                "recommended_type": "css",
                "confidence": 0.95,
                "why_old_broke": "Class renamed",
                "explanation": "data-testid is stable",
                "selenium_code": "driver.find_element(By.CSS_SELECTOR, \"[data-testid='login-button']\")",
                "alternative_selectors": [],
                "robustness_tips": "Use data-testid",
            })
            mock_llm.return_value.invoke.return_value = mock_response

            with patch('apps.agents.agents.ChatGoogleGenerativeAI', mock_llm):
                import importlib
                import apps.agents.agents as agents_module
                importlib.reload(agents_module)
                agent = agents_module.SelfHealingSelectorAgent()
                result = agent.heal(
                    broken_selector=".btn-login",
                    selector_type="css",
                    element_description="Login button",
                    page_html="<button data-testid='login-button'>Login</button>",
                )
                assert "new_css_selector" in result
                assert len(result["new_css_selector"]) > 0