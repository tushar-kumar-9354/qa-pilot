"""
QA-PILOT — AI Agents (LangChain + Gemini)
Agent 1: Test Case Generator
Agent 2: Failure Analyzer
Agent 3: Self-Healing Selector
"""
import json
import re
from typing import Optional
from django.conf import settings
import structlog

from langchain_google_genai import ChatGoogleGenerativeAI # pyright: ignore[reportMissingImports]
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.messages import HumanMessage, SystemMessage

logger = structlog.get_logger(__name__)


def get_llm(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    """Initialize Gemini LLM via LangChain."""
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        convert_system_message_to_human=True,
    )


# ─────────────────────────────────────────────────────────────
# AGENT 1 — Test Case Generator
# Takes: scraped data + feature description
# Returns: ready-to-run pytest test code
# ─────────────────────────────────────────────────────────────

class TestCaseGeneratorAgent:
    """
    Generates pytest test cases from scraped data + feature descriptions.
    Uses Gemini to write real, runnable test code including fixtures,
    assertions, edge cases and parametrize decorators.
    """

    SYSTEM_PROMPT = """You are an expert QA Automation Engineer specializing in pytest.
Your job is to generate production-grade pytest test cases from scraped data and feature descriptions.

Rules:
- Always use @pytest.mark.parametrize with real data rows when available
- Include positive tests, negative tests, and edge case tests
- Use descriptive test function names: test_<what>_<condition>_<expected>
- Add docstrings to every test function
- Use pytest fixtures for setup/teardown
- Return ONLY valid Python code, no explanation text
- Import only standard pytest, no third-party unless specified
"""

    def __init__(self):
        self.llm = get_llm(temperature=0.2)
        self.memory = ConversationBufferWindowMemory(k=5, return_messages=True)

    def generate(
        self,
        feature_description: str,
        scraped_data: Optional[list] = None,
        test_type: str = "unit",
        num_tests: int = 5,
    ) -> dict:
        """
        Generate pytest test cases.

        Args:
            feature_description: What feature/function to test
            scraped_data: List of real data rows from scraper (optional)
            test_type: unit | integration | api | e2e
            num_tests: Number of test cases to generate

        Returns:
            dict with 'code', 'test_names', 'explanation'
        """
        data_section = ""
        if scraped_data and len(scraped_data) > 0:
            sample = scraped_data[:10]
            data_section = f"""
SCRAPED DATA (use as test fixtures/parametrize values):
{json.dumps(sample, indent=2, default=str)}

Use rows from this data as @pytest.mark.parametrize arguments.
"""

        prompt = f"""
{self.SYSTEM_PROMPT}

Generate {num_tests} pytest {test_type} tests for the following:

FEATURE: {feature_description}
{data_section}

Requirements:
- Test type: {test_type}
- Generate exactly {num_tests} test functions
- Include at least 1 parametrized test using the scraped data if provided
- Include at least 1 negative/edge case test
- Use type hints
- Each test must have a clear docstring

Return ONLY the Python code block. Start with imports.
"""

        try:
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
            response = self.llm.invoke(messages)
            code = self._clean_code(response.content)

            test_names = re.findall(r'def (test_\w+)', code)

            logger.info(
                "agent.test_generator.success",
                feature=feature_description[:50],
                tests_generated=len(test_names),
                test_type=test_type,
            )

            return {
                'code': code,
                'test_names': test_names,
                'test_count': len(test_names),
                'test_type': test_type,
                'used_scraped_data': scraped_data is not None and len(scraped_data) > 0,
                'explanation': f"Generated {len(test_names)} {test_type} tests for: {feature_description}",
            }

        except Exception as e:
            logger.error("agent.test_generator.error", error=str(e))
            return {'error': str(e), 'code': '', 'test_names': []}

    def _clean_code(self, raw: str) -> str:
        """Strip markdown code fences if present."""
        raw = raw.strip()
        if raw.startswith('```python'):
            raw = raw[9:]
        elif raw.startswith('```'):
            raw = raw[3:]
        if raw.endswith('```'):
            raw = raw[:-3]
        return raw.strip()


# ─────────────────────────────────────────────────────────────
# AGENT 2 — Failure Analyzer
# Takes: test logs + stack trace
# Returns: root cause analysis + fix suggestion
# ─────────────────────────────────────────────────────────────

class FailureAnalyzerAgent:
    """
    Analyzes test failure logs and provides:
    1. Plain-English root cause explanation
    2. Exact fix suggestion with code
    3. Severity assessment
    4. Similar failure patterns to watch for
    """

    SYSTEM_PROMPT = """You are a senior QA engineer and Python expert.
Analyze test failure logs and provide clear, actionable diagnosis.
Be specific, not generic. Point to exact lines, exact values, exact fixes.
"""

    def __init__(self):
        self.llm = get_llm(temperature=0.1)
        self.memory = ConversationBufferWindowMemory(k=10, return_messages=True)

    def analyze(
        self,
        logs: str,
        stack_trace: str = "",
        test_name: str = "",
        test_code: str = "",
    ) -> dict:
        """
        Analyze a test failure.

        Returns:
            dict with root_cause, fix_suggestion, severity, similar_patterns
        """
        prompt = f"""
Analyze this test failure and provide a structured diagnosis.

TEST NAME: {test_name or 'Unknown'}

FAILURE LOGS:
{logs[:3000]}

STACK TRACE:
{stack_trace[:2000] if stack_trace else 'Not provided'}

TEST CODE:
{test_code[:2000] if test_code else 'Not provided'}

Respond with a JSON object (and ONLY the JSON, no markdown):
{{
    "root_cause": "One clear sentence explaining exactly what went wrong",
    "detailed_explanation": "2-3 sentences with more detail",
    "fix_suggestion": "Exact code change or step-by-step fix",
    "fix_code_snippet": "Python code snippet showing the fix (if applicable)",
    "severity": "critical|high|medium|low",
    "category": "assertion_error|import_error|timeout|network|database|fixture|logic|type_error|other",
    "similar_patterns": ["Pattern 1 to watch for", "Pattern 2"],
    "prevention": "How to prevent this in future"
}}
"""

        try:
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
            response = self.llm.invoke(messages)
            content = response.content.strip()

            # Clean JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)

            logger.info(
                "agent.failure_analyzer.success",
                test=test_name,
                severity=result.get('severity'),
                category=result.get('category'),
            )

            return result

        except json.JSONDecodeError:
            # Fallback: return raw text
            return {
                'root_cause': response.content[:500],
                'fix_suggestion': 'See detailed explanation above.',
                'severity': 'medium',
                'category': 'other',
                'similar_patterns': [],
                'prevention': '',
                'fix_code_snippet': '',
                'detailed_explanation': '',
            }
        except Exception as e:
            logger.error("agent.failure_analyzer.error", error=str(e))
            return {'error': str(e)}

    def chat(self, message: str) -> str:
        """
        Conversational follow-up on failures.
        Allows dashboard chat: "Why did the login test fail?"
        """
        try:
            self.memory.chat_memory.add_user_message(message)
            messages = self.memory.chat_memory.messages + [HumanMessage(content=message)]
            response = self.llm.invoke(messages)
            self.memory.chat_memory.add_ai_message(response.content)
            return response.content
        except Exception as e:
            logger.error("agent.failure_analyzer.chat_error", error=str(e))
            return f"Error: {str(e)}"


# ─────────────────────────────────────────────────────────────
# AGENT 3 — Self-Healing Selector
# Takes: broken Selenium locator + page HTML
# Returns: new working CSS/XPath selector
# ─────────────────────────────────────────────────────────────

class SelfHealingSelectorAgent:
    """
    When a Selenium test breaks because a CSS/XPath selector changed,
    this agent automatically finds the new correct selector from the page HTML.

    This is a cutting-edge QA automation technique — impresses senior engineers.
    """

    SYSTEM_PROMPT = """You are a Selenium expert specializing in robust element locators.
When given a broken selector and the current page HTML, find the best new selector.
Prioritize: data-testid > aria-label > unique class > id > text content.
Always explain WHY the old selector broke.
"""

    def __init__(self):
        self.llm = get_llm(temperature=0.1)

    def heal(
        self,
        broken_selector: str,
        selector_type: str,
        element_description: str,
        page_html: str,
        error_message: str = "",
    ) -> dict:
        """
        Find a replacement for a broken Selenium selector.

        Args:
            broken_selector: The CSS or XPath that no longer works
            selector_type: 'css' or 'xpath'
            element_description: Human description of what the element is
            page_html: Current page HTML (truncated to relevant section)
            error_message: The NoSuchElementException message

        Returns:
            dict with new_selector, selector_type, confidence, explanation
        """
        # Truncate HTML to keep context manageable
        html_snippet = page_html[:4000] if len(page_html) > 4000 else page_html

        prompt = f"""
A Selenium locator has broken. Find a replacement.

ELEMENT DESCRIPTION: {element_description}
BROKEN {selector_type.upper()} SELECTOR: {broken_selector}
ERROR: {error_message or 'NoSuchElementException'}

CURRENT PAGE HTML (relevant section):
{html_snippet}

Respond with ONLY this JSON (no markdown):
{{
    "new_css_selector": "The best CSS selector for this element",
    "new_xpath": "The best XPath for this element",
    "recommended_type": "css or xpath",
    "confidence": 0.95,
    "why_old_broke": "Exact reason the old selector stopped working",
    "explanation": "Why the new selector is better",
    "selenium_code": "driver.find_element(By.CSS_SELECTOR, 'your_selector')",
    "alternative_selectors": ["fallback1", "fallback2"],
    "robustness_tips": "How to write selectors that won't break"
}}
"""

        try:
            messages = [
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
            response = self.llm.invoke(messages)
            content = response.content.strip()

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)

            logger.info(
                "agent.self_healing.success",
                old_selector=broken_selector,
                new_selector=result.get('new_css_selector'),
                confidence=result.get('confidence'),
            )

            return result

        except Exception as e:
            logger.error("agent.self_healing.error", error=str(e))
            return {
                'error': str(e),
                'new_css_selector': '',
                'new_xpath': '',
                'confidence': 0.0,
            }


# ─────────────────────────────────────────────────────────────
# AGENT CHAT — General QA assistant for the dashboard
# ─────────────────────────────────────────────────────────────

class QAChatAgent:
    """
    General-purpose QA assistant embedded in the dashboard.
    Can answer questions about test results, explain failures,
    suggest improvements, and have a full conversation.
    """

    SYSTEM_PROMPT = """You are QA-Pilot, an expert AI assistant for QA Automation Engineers.
You help with:
- Analyzing test failures and suggesting fixes
- Writing pytest test cases
- Explaining Selenium errors
- Reviewing test strategies
- Answering questions about the test suite

Be concise, technical, and always practical.
When showing code, use proper Python syntax.
"""

    def __init__(self):
        self.llm = get_llm(temperature=0.4)
        self.memory = ConversationBufferWindowMemory(k=10, return_messages=True)

    def chat(self, message: str, context: dict = None) -> str:
        """Send a message and get a response."""
        context_str = ""
        if context:
            context_str = f"\n\nCurrent Context:\n{json.dumps(context, indent=2, default=str)[:1000]}"

        full_message = message + context_str

        try:
            history = self.memory.chat_memory.messages[-10:]
            messages = [SystemMessage(content=self.SYSTEM_PROMPT)] + history + [HumanMessage(content=full_message)]
            response = self.llm.invoke(messages)

            self.memory.chat_memory.add_user_message(message)
            self.memory.chat_memory.add_ai_message(response.content)

            return response.content

        except Exception as e:
            logger.error("agent.chat.error", error=str(e))
            return f"I encountered an error: {str(e)}. Please check your Gemini API key."

    def clear_memory(self):
        self.memory.clear()
