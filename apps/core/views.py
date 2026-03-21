"""
QA-PILOT — All views + Direct Gemini AI (no FastAPI needed)
"""
import json
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.shortcuts import render


# ── Page Views ───────────────────────────────────────────────
def dashboard(request):
    return render(request, 'dashboard/dashboard.html')

def suites(request):
    return render(request, 'pages/suites.html')

def runs(request):
    return render(request, 'pages/runs.html')

def bugs(request):
    return render(request, 'pages/bugs.html')

def scraped_data(request):
    return render(request, 'pages/scraped_data.html')

def scraper(request):
    return render(request, 'pages/scraper.html')

def agent_generate(request):
    return render(request, 'pages/agent_generate.html')

def agent_chat(request):
    return render(request, 'pages/agent_chat.html')

def agent_healer(request):
    return render(request, 'pages/agent_healer.html')


# ── Gemini Helper ────────────────────────────────────────────
def call_gemini(prompt: str, system: str = "") -> str:
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system or "You are QA-Pilot, an expert QA automation assistant.",
    )
    response = model.generate_content(prompt)
    return response.text


# ── Health ───────────────────────────────────────────────────
def api_health(request):
    return JsonResponse({'status': 'healthy', 'version': '1.0.0'})


# ── Dashboard Stats ──────────────────────────────────────────
def api_dashboard_stats(request):
    try:
        from apps.core.models import TestSuite, TestCase, TestRun, BugReport
        from apps.scraper.models import ScrapedData
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        trend = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_runs = TestRun.objects.filter(created_at__date=day, status='completed')
            passed = day_runs.filter(result='passed').count()
            total = day_runs.count()
            trend.append({
                'date': day.isoformat(),
                'runs': total,
                'pass_rate': round((passed / total * 100), 1) if total > 0 else 0,
            })

        recent_failures = TestRun.objects.filter(
            result='failed'
        ).select_related('suite').order_by('-created_at')[:5]

        return JsonResponse({
            'totals': {
                'suites': TestSuite.objects.count(),
                'cases': TestCase.objects.count(),
                'runs': TestRun.objects.count(),
                'runs_today': TestRun.objects.filter(created_at__date=today).count(),
                'open_bugs': BugReport.objects.filter(status='open').count(),
                'scraped_records': ScrapedData.objects.count(),
            },
            'trend': trend,
            'recent_failures': [
                {'id': str(r.id), 'suite': r.suite.name, 'failed': r.failed,
                 'total': r.total_tests, 'created_at': r.created_at.isoformat()}
                for r in recent_failures
            ],
        })
    except Exception as e:
        return JsonResponse({'totals': {'suites':0,'cases':0,'runs':0,'runs_today':0,'open_bugs':0,'scraped_records':0},'trend':[{'date':'2026-01-01','runs':0,'pass_rate':0}]*7,'recent_failures':[]})


# ── Test Suites API ──────────────────────────────────────────
def api_suites(request):
    try:
        from apps.core.models import TestSuite
        search = request.GET.get('search', '')
        status = request.GET.get('status', '')
        qs = TestSuite.objects.all()
        if search:
            qs = qs.filter(name__icontains=search)
        if status:
            qs = qs.filter(status=status)
        return JsonResponse({
            'total': qs.count(),
            'page': 1,
            'results': [
                {'id': str(s.id), 'name': s.name, 'description': s.description,
                 'status': s.status, 'total_cases': s.total_cases,
                 'pass_rate': s.pass_rate, 'tags': s.tags,
                 'created_at': s.created_at.isoformat()}
                for s in qs[:100]
            ]
        })
    except Exception as e:
        return JsonResponse({'total': 0, 'results': [], 'error': str(e)})


# ── Test Runs API ────────────────────────────────────────────
def api_runs(request):
    try:
        from apps.core.models import TestRun
        status = request.GET.get('status', '')
        qs = TestRun.objects.select_related('suite').all()
        if status:
            qs = qs.filter(status=status)
        return JsonResponse({
            'total': qs.count(),
            'results': [
                {'id': str(r.id), 'suite_name': r.suite.name, 'status': r.status,
                 'result': r.result, 'total_tests': r.total_tests, 'passed': r.passed,
                 'failed': r.failed, 'errors': r.errors, 'skipped': r.skipped,
                 'pass_rate': r.pass_rate, 'duration_seconds': r.duration_seconds,
                 'environment': r.environment, 'logs': r.logs,
                 'created_at': r.created_at.isoformat()}
                for r in qs[:50]
            ]
        })
    except Exception as e:
        return JsonResponse({'total': 0, 'results': [], 'error': str(e)})


@csrf_exempt
def api_trigger_run(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        import subprocess, tempfile, os
        from apps.core.models import TestSuite, TestRun
        from django.utils import timezone

        body = json.loads(request.body)
        suite = TestSuite.objects.get(id=body['suite_id'])

        run = TestRun.objects.create(
            suite=suite,
            status=TestRun.Status.RUNNING,
            environment=body.get('environment', 'development'),
            started_at=timezone.now(),
        )

        # Write test code to temp file
        test_cases = suite.test_cases.all()
        if not test_cases.exists():
            run.mark_completed(0, 0, 0, 0, "No test cases in suite.")
            return JsonResponse({'run_id': str(run.id), 'status': 'completed'})

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='_test.py', delete=False, dir=tempfile.gettempdir()
        ) as f:
            f.write("import pytest\n\n")
            for tc in test_cases:
                if tc.code:
                    f.write(f"# {tc.name}\n{tc.code}\n\n")
            temp_path = f.name

        # Run pytest directly
        result = subprocess.run(
            ["python", "-m", "pytest", temp_path, "-v", "--tb=short", "--no-header"],
            capture_output=True, text=True, timeout=120,
        )

        output = result.stdout + result.stderr
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        errors = output.count(" ERROR")
        skipped = output.count(" SKIPPED")

        run.mark_completed(passed, failed, errors, skipped, output)
        os.unlink(temp_path)

        return JsonResponse({
            'run_id': str(run.id),
            'status': 'completed',
            'passed': passed,
            'failed': failed,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# ── Scraper API ──────────────────────────────────────────────
def api_scraper_data(request):
    try:
        from apps.scraper.models import ScrapedData
        qs = ScrapedData.objects.select_related('target').all()
        return JsonResponse({
            'total': qs.count(),
            'results': [
                {'id': str(r.id), 'title': r.title, 'target': r.target.name,
                 'row_count': r.row_count, 'column_count': r.column_count,
                 'status': r.status, 'source_url': r.source_url,
                 'created_at': r.created_at.isoformat()}
                for r in qs[:50]
            ]
        })
    except Exception as e:
        return JsonResponse({'total': 0, 'results': [], 'error': str(e)})


@csrf_exempt
def api_scraper_trigger(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        from apps.scraper.models import ScraperTarget, ScraperRun, ScrapedData
        from apps.scraper.engine import ScraperEngine
        from django.utils import timezone

        body = json.loads(request.body)
        url = body.get('url', '').strip()
        data_type = body.get('data_type', 'table')
        css_selector = body.get('css_selector', '')

        if not url:
            return JsonResponse({'error': 'URL required'}, status=400)

        # Get or create target
        target, _ = ScraperTarget.objects.get_or_create(
            url=url,
            defaults={
                'name': url.split('/')[-1].replace('_', ' ')[:100],
                'data_type': data_type,
                'requires_js': True,
            }
        )

        # Create run record
        run = ScraperRun.objects.create(
            target=target,
            status=ScraperRun.Status.RUNNING,
            started_at=timezone.now(),
            triggered_by='manual',
        )

        # Run scraper directly (synchronous)
        with ScraperEngine() as scraper:
            if data_type == 'table':
                raw_data = scraper.scrape_table(url, css_selector=css_selector or None)
            else:
                raw_data = scraper.scrape_article(url)

        if 'error' in raw_data:
            run.status = ScraperRun.Status.FAILED
            run.error_message = raw_data['error']
            run.completed_at = timezone.now()
            run.save()
            return JsonResponse({'error': raw_data['error']}, status=500)

        # Normalize and save
        normalized = ScraperEngine.normalize_table_data(raw_data) if data_type == 'table' else raw_data
        data_hash = ScraperEngine.compute_hash(raw_data)

        # Skip duplicates
        if ScrapedData.objects.filter(data_hash=data_hash).exists():
            run.status = ScraperRun.Status.SUCCESS
            run.completed_at = timezone.now()
            run.save()
            return JsonResponse({'status': 'skipped', 'reason': 'Duplicate data — already scraped'})

        scraped = ScrapedData.objects.create(
            target=target,
            scraper_run=run,
            title=raw_data.get('title', url[:100]),
            raw_data=raw_data,
            normalized_data=normalized,
            data_hash=data_hash,
            row_count=raw_data.get('row_count', len(normalized) if isinstance(normalized, list) else 1),
            column_count=raw_data.get('column_count', 0),
            source_url=url,
            status=ScrapedData.DataStatus.VALIDATED,
        )

        run.status = ScraperRun.Status.SUCCESS
        run.records_scraped = scraped.row_count
        run.completed_at = timezone.now()
        run.save()

        target.last_scraped_at = timezone.now()
        target.total_records_scraped += scraped.row_count
        target.save()

        return JsonResponse({
            'status': 'success',
            'scraped_id': str(scraped.id),
            'rows': scraped.row_count,
            'title': scraped.title,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
# ── AI: Chat ─────────────────────────────────────────────────
@csrf_exempt
def api_chat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        message = body.get('message', '').strip()
        if not message:
            return JsonResponse({'error': 'Message required'}, status=400)

        system = """You are QA-Pilot, an expert AI assistant for QA Automation Engineers.
Help with pytest, Selenium, test strategy, bug analysis, and automation best practices.
Be concise, technical, and practical. Format code in Python."""

        response = call_gemini(message, system)
        return JsonResponse({'response': response, 'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': f'Gemini error: {str(e)}'}, status=500)


# ── AI: Generate Tests ───────────────────────────────────────
@csrf_exempt
def api_generate_tests(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        feature = body.get('feature_description', '')
        test_type = body.get('test_type', 'unit')
        num_tests = body.get('num_tests', 5)
        use_scraped = body.get('use_scraped_data', False)

        scraped_section = ""
        if use_scraped:
            try:
                from apps.scraper.models import ScrapedData
                latest = ScrapedData.objects.filter(status='validated').order_by('-created_at').first()
                if latest and latest.normalized_data:
                    sample = latest.normalized_data[:5] if isinstance(latest.normalized_data, list) else []
                    if sample:
                        scraped_section = f"\n\nSCRAPED DATA (use as @pytest.mark.parametrize fixtures):\n{json.dumps(sample, indent=2, default=str)}"
            except:
                pass

        prompt = f"""Generate {num_tests} pytest {test_type} tests for:

FEATURE: {feature}{scraped_section}

Rules:
- Use @pytest.mark.parametrize with real data where available
- Include positive, negative, and edge case tests
- Add docstrings to every test function
- Use descriptive names: test_<what>_<condition>_<expected>
- Return ONLY valid Python code, no explanation text

Start with imports."""

        code = call_gemini(prompt)

        # Strip code fences
        if '```python' in code:
            code = code.split('```python')[1].split('```')[0].strip()
        elif '```' in code:
            code = code.split('```')[1].split('```')[0].strip()

        test_names = re.findall(r'def (test_\w+)', code)
        return JsonResponse({
            'code': code,
            'test_names': test_names,
            'test_count': len(test_names),
            'test_type': test_type,
            'used_scraped_data': bool(scraped_section),
        })
    except Exception as e:
        return JsonResponse({'error': f'Gemini error: {str(e)}'}, status=500)


# ── AI: Heal Selector ────────────────────────────────────────
@csrf_exempt
def api_heal_selector(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        broken = body.get('broken_selector', '')
        sel_type = body.get('selector_type', 'css')
        desc = body.get('element_description', '')
        html = body.get('page_html', '')[:3000]
        error = body.get('error_message', '')

        prompt = f"""A Selenium locator broke. Find the best replacement.

ELEMENT: {desc}
BROKEN {sel_type.upper()}: {broken}
ERROR: {error}
PAGE HTML:
{html}

Respond with ONLY valid JSON (no markdown, no explanation):
{{
    "new_css_selector": "best CSS selector here",
    "new_xpath": "best XPath here",
    "recommended_type": "css",
    "confidence": 0.95,
    "why_old_broke": "exact reason",
    "explanation": "why new is better",
    "selenium_code": "driver.find_element(By.CSS_SELECTOR, 'selector')",
    "robustness_tips": "tip here"
}}"""

        raw = call_gemini(prompt)
        if '```json' in raw:
            raw = raw.split('```json')[1].split('```')[0].strip()
        elif '```' in raw:
            raw = raw.split('```')[1].split('```')[0].strip()

        result = json.loads(raw)
        return JsonResponse(result)
    except json.JSONDecodeError:
        return JsonResponse({
            'new_css_selector': 'Parse error — try simplifying your HTML input',
            'new_xpath': '', 'confidence': 0,
            'why_old_broke': 'Could not parse AI response',
            'selenium_code': '', 'robustness_tips': '',
        })
    except Exception as e:
        return JsonResponse({'error': f'Gemini error: {str(e)}'}, status=500)


# ── AI: Analyze Failure ──────────────────────────────────────
@csrf_exempt
def api_analyze_failure(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        logs = body.get('logs', '')
        test_name = body.get('test_name', '')

        prompt = f"""Analyze this test failure and return ONLY valid JSON:

TEST: {test_name}
LOGS: {logs[:3000]}

{{
    "root_cause": "one clear sentence",
    "detailed_explanation": "2-3 sentences",
    "fix_suggestion": "exact fix steps",
    "fix_code_snippet": "python code if applicable",
    "severity": "critical|high|medium|low",
    "category": "assertion_error|timeout|import_error|network|database|other"
}}"""

        raw = call_gemini(prompt)
        if '```json' in raw:
            raw = raw.split('```json')[1].split('```')[0].strip()
        elif '```' in raw:
            raw = raw.split('```')[1].split('```')[0].strip()

        return JsonResponse(json.loads(raw))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def api_scraper_record(request, record_id):
    try:
        from apps.scraper.models import ScrapedData
        r = ScrapedData.objects.get(id=record_id)
        return JsonResponse({
            'id': str(r.id),
            'title': r.title,
            'source_url': r.source_url,
            'row_count': r.row_count,
            'column_count': r.column_count,
            'raw_data': r.raw_data,
            'normalized_data': r.normalized_data,
            'status': r.status,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)