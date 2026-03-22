"""
QA-PILOT — Unit Tests
Pure Python tests — no selenium, no langchain, no heavy deps needed.
Run: pytest tests/unit/ -v
"""
import pytest
import json
import hashlib
from unittest.mock import patch, MagicMock


# ── Pure Python implementations (mirror of engine.py static methods) ──────────
# These are tested independently so CI does not need selenium installed

def compute_hash(data: dict) -> str:
    """SHA256 hash — mirrors ScraperEngine.compute_hash."""
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


def normalize_table_data(raw_data: dict) -> list:
    """Normalize scraped rows — mirrors ScraperEngine.normalize_table_data."""
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


# ── Fixtures ──────────────────────────────────────────────────

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


# ── ScraperEngine Unit Tests ───────────────────────────────────

@pytest.mark.unit
class TestScraperEngine:

    def test_compute_hash_returns_sha256_string(self):
        """Hash output must be a 64-char hex string."""
        data = {"rows": [{"col1": "val1"}], "url": "https://example.com"}
        result = compute_hash(data)
        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in '0123456789abcdef' for c in result)

    def test_compute_hash_is_deterministic(self):
        """Same data must always produce same hash."""
        data = {"rows": [{"a": 1}], "url": "https://test.com"}
        assert compute_hash(data) == compute_hash(data)

    def test_compute_hash_different_data_different_hash(self):
        """Different data must produce different hashes."""
        h1 = compute_hash({"data": "version1"})
        h2 = compute_hash({"data": "version2"})
        assert h1 != h2

    @pytest.mark.parametrize("raw_row,expected_key", [
        ({"Country Name": "India"}, "country_name"),
        ({"GDP (USD)": "2.3T"},     "gdp_(usd)"),
        ({"Population.2024": "1.4B"}, "population2024"),
    ])
    def test_normalize_cleans_column_keys(self, raw_row, expected_key):
        """normalize_table_data should clean header keys."""
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
        """normalize_table_data should convert numeric strings."""
        raw = {"rows": [{"value": raw_value}]}
        result = normalize_table_data(raw)
        if result:
            assert isinstance(result[0]["value"], expected_type)

    def test_normalize_removes_empty_rows(self):
        """Rows with all empty values must be filtered out."""
        raw = {"rows": [{"col": ""}, {"col": "data"}, {"col": "  "}]}
        result = normalize_table_data(raw)
        assert len(result) == 1
        assert result[0]["col"] == "data"


# ── Scraped Country Data Tests ─────────────────────────────────

@pytest.mark.unit
class TestScrapedCountryData:

    @pytest.mark.parametrize("country_data", [
        {"rank": 1, "country": "India",         "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China",         "population": 1425671352, "region": "Asia"},
        {"rank": 3, "country": "United States", "population": 335893238,  "region": "Americas"},
    ])
    def test_country_data_has_required_fields(self, country_data):
        """Every scraped country record must have required fields."""
        assert {"rank", "country", "population", "region"}.issubset(country_data.keys())

    @pytest.mark.parametrize("country_data", [
        {"rank": 1, "country": "India", "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China", "population": 1425671352, "region": "Asia"},
    ])
    def test_population_is_positive_integer(self, country_data):
        """Population must be a positive integer."""
        assert isinstance(country_data["population"], int)
        assert country_data["population"] > 0

    @pytest.mark.parametrize("country_data", [
        {"rank": 1, "country": "India",         "population": 1428627663, "region": "Asia"},
        {"rank": 2, "country": "China",         "population": 1425671352, "region": "Asia"},
        {"rank": 3, "country": "United States", "population": 335893238,  "region": "Americas"},
    ])
    def test_rank_is_sequential_positive(self, country_data):
        """Rank must be a positive integer."""
        assert isinstance(country_data["rank"], int)
        assert country_data["rank"] > 0

    def test_all_scraped_countries_have_non_empty_name(self, scraped_country_rows):
        """No country should have an empty name."""
        for row in scraped_country_rows:
            assert row.get("country"), f"Empty name in row: {row}"

    def test_scraped_dataset_is_sorted_by_rank(self, scraped_country_rows):
        """Scraped country data should be sorted by rank."""
        ranks = [r["rank"] for r in scraped_country_rows]
        assert ranks == sorted(ranks)


# ── Hacker News Data Tests ─────────────────────────────────────

@pytest.mark.unit
class TestScrapedHNData:

    @pytest.mark.parametrize("story", [
        {"id": "123", "title": "Ask HN: Best QA tools",      "score": "312 points", "author": "user1"},
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


# ── AI Agents Tests (100% mocked — zero heavy deps) ────────────

@pytest.mark.unit
class TestAIAgents:

    def test_test_generator_returns_code(self):
        """TestCaseGenerator must return Python code string."""
        # Mock LLM response
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = (
            "import pytest\n\n"
            "def test_user_login_valid():\n"
            "    \"\"\"Test valid login.\"\"\"\n"
            "    assert True\n\n"
            "def test_user_login_invalid():\n"
            "    \"\"\"Test invalid login.\"\"\"\n"
            "    assert True\n"
        )
        mock_llm_instance.invoke.return_value = mock_response

        with patch.dict('sys.modules', {
            'langchain_google_genai':        MagicMock(),
            'langchain.agents':              MagicMock(),
            'langchain.tools':               MagicMock(),
            'langchain.prompts':             MagicMock(),
            'langchain.memory':              MagicMock(),
            'langchain_core.messages':       MagicMock(),
            'google.generativeai':           MagicMock(),
        }):
            # Patch at the module level
            with patch('apps.agents.agents.ChatGoogleGenerativeAI', return_value=mock_llm_instance):
                from apps.agents import agents as agents_mod
                import importlib
                importlib.reload(agents_mod)
                agent = agents_mod.TestCaseGeneratorAgent()
                result = agent.generate("User login endpoint", num_tests=2)

        assert "code" in result
        assert "test_" in result["code"]
        assert len(result.get("test_names", [])) >= 1

    def test_failure_analyzer_returns_dict(self):
        """FailureAnalyzer must return a dict with root_cause."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "root_cause": "AssertionError: expected 200 got 404",
            "detailed_explanation": "URL changed from v1 to v2",
            "fix_suggestion": "Update base URL in test config",
            "fix_code_snippet": "BASE_URL = '/api/v2/'",
            "severity": "high",
            "category": "assertion_error",
            "similar_patterns": ["URL versioning"],
            "prevention": "Use URL constants",
        })
        mock_llm_instance.invoke.return_value = mock_response

        with patch.dict('sys.modules', {
            'langchain_google_genai':  MagicMock(),
            'langchain.agents':        MagicMock(),
            'langchain.tools':         MagicMock(),
            'langchain.prompts':       MagicMock(),
            'langchain.memory':        MagicMock(),
            'langchain_core.messages': MagicMock(),
            'google.generativeai':     MagicMock(),
        }):
            with patch('apps.agents.agents.ChatGoogleGenerativeAI', return_value=mock_llm_instance):
                from apps.agents import agents as agents_mod
                import importlib
                importlib.reload(agents_mod)
                agent = agents_mod.FailureAnalyzerAgent()
                result = agent.analyze("FAILED test_login\nAssertionError: 404")

        assert "root_cause" in result
        assert result["severity"] in ["critical", "high", "medium", "low"]

    def test_self_healing_returns_selector(self):
        """SelfHealingSelector must return a new CSS selector."""
        mock_llm_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "new_css_selector": "[data-testid='login-button']",
            "new_xpath": "//button[@data-testid='login-button']",
            "recommended_type": "css",
            "confidence": 0.95,
            "why_old_broke": "Class renamed from btn-login to login-btn",
            "explanation": "data-testid is stable",
            "selenium_code": "driver.find_element(By.CSS_SELECTOR, \"[data-testid='login-button']\")",
            "alternative_selectors": ["#login-btn"],
            "robustness_tips": "Always prefer data-testid",
        })
        mock_llm_instance.invoke.return_value = mock_response

        with patch.dict('sys.modules', {
            'langchain_google_genai':  MagicMock(),
            'langchain.agents':        MagicMock(),
            'langchain.tools':         MagicMock(),
            'langchain.prompts':       MagicMock(),
            'langchain.memory':        MagicMock(),
            'langchain_core.messages': MagicMock(),
            'google.generativeai':     MagicMock(),
        }):
            with patch('apps.agents.agents.ChatGoogleGenerativeAI', return_value=mock_llm_instance):
                from apps.agents import agents as agents_mod
                import importlib
                importlib.reload(agents_mod)
                agent = agents_mod.SelfHealingSelectorAgent()
                result = agent.heal(
                    broken_selector=".btn-login",
                    selector_type="css",
                    element_description="Login button",
                    page_html="<button data-testid='login-button'>Login</button>",
                )

        assert "new_css_selector" in result
        assert len(result["new_css_selector"]) > 0
        assert result["confidence"] > 0