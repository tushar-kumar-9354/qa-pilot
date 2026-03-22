"""
QA-PILOT — FastAPI Application
High-performance async REST API + WebSocket for live test streaming
"""
import os
import json
import asyncio
from typing import Optional, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from jose import jwt, JWTError
import structlog
from asgiref.sync import sync_to_async

logger = structlog.get_logger(__name__)


# ── Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("fastapi.startup", version="1.0.0")
    yield
    logger.info("fastapi.shutdown")


# ── App Init ─────────────────────────────────────────────────
app = FastAPI(
    title="QA-Pilot API",
    description="AI-powered QA Automation Platform — REST API & WebSocket",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket Connection Manager ─────────────────────────────
class ConnectionManager:
    """Manages active WebSocket connections for live log streaming."""

    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        self.active.setdefault(room, []).append(websocket)
        logger.info("ws.connected", room=room, total=len(self.active.get(room, [])))

    def disconnect(self, websocket: WebSocket, room: str):
        self.active.get(room, []).remove(websocket) if websocket in self.active.get(room, []) else None
        logger.info("ws.disconnected", room=room)

    async def broadcast(self, room: str, message: dict):
        connections = self.active.get(room, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, room)


manager = ConnectionManager()


# ── Sync to async wrappers for Django ORM ─────────────────────
@sync_to_async
def get_test_suites_count(qs):
    return qs.count()

@sync_to_async
def get_test_suites_slice(qs, offset, page_size):
    return list(qs[offset:offset + page_size])

@sync_to_async
def get_test_suite_by_id(suite_id):
    from apps.core.models import TestSuite
    return TestSuite.objects.prefetch_related('test_cases').get(id=suite_id)

@sync_to_async
def get_test_runs_count(qs):
    return qs.count()

@sync_to_async
def get_test_runs_slice(qs, offset, page_size):
    return list(qs[offset:offset + page_size])

@sync_to_async
def get_test_suite_by_id_for_trigger(suite_id):
    from apps.core.models import TestSuite
    return TestSuite.objects.get(id=suite_id)

@sync_to_async
def create_test_run(suite, environment):
    from apps.core.models import TestRun
    return TestRun.objects.create(
        suite=suite,
        status=TestRun.Status.PENDING,
        environment=environment,
    )

@sync_to_async
def update_test_run_task_id(run, task_id):
    run.celery_task_id = task_id
    run.save(update_fields=['celery_task_id'])

@sync_to_async
def get_dashboard_stats_data():
    from apps.core.models import TestSuite, TestCase, TestRun, BugReport
    from apps.scraper.models import ScrapedData, ScraperRun
    from django.utils import timezone

    today = timezone.now().date()
    
    total_suites = TestSuite.objects.count()
    total_cases = TestCase.objects.count()
    total_runs = TestRun.objects.count()
    runs_today = TestRun.objects.filter(created_at__date=today).count()
    open_bugs = BugReport.objects.filter(status='open').count()
    scraped_records = ScrapedData.objects.count()
    
    # Pass rate trend (last 7 days)
    trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_runs = TestRun.objects.filter(created_at__date=day, status='completed')
        passed = day_runs.filter(result='passed').count()
        total = day_runs.count()
        trend.append({
            "date": day.isoformat(),
            "runs": total,
            "pass_rate": round((passed / total * 100), 1) if total > 0 else 0,
        })
    
    # Recent failures
    recent_failures = list(TestRun.objects.filter(
        result='failed'
    ).select_related('suite').order_by('-created_at')[:5])
    
    return {
        "total_suites": total_suites,
        "total_cases": total_cases,
        "total_runs": total_runs,
        "runs_today": runs_today,
        "open_bugs": open_bugs,
        "scraped_records": scraped_records,
        "trend": trend,
        "recent_failures": recent_failures,
    }

@sync_to_async
def get_scraped_data_count(qs):
    return qs.count()

@sync_to_async
def get_scraped_data_slice(qs, offset, page_size):
    return list(qs[offset:offset + page_size])

@sync_to_async
def get_test_run_for_websocket(run_id):
    from apps.core.models import TestRun
    return TestRun.objects.get(id=run_id)


# ── Pydantic Schemas ─────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: dict


class TestSuiteResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    total_cases: int
    pass_rate: float
    created_at: str


class TestRunResponse(BaseModel):
    id: str
    suite_name: str
    status: str
    result: Optional[str]
    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    pass_rate: float
    duration_seconds: Optional[float]
    created_at: str


class TriggerRunRequest(BaseModel):
    suite_id: str
    environment: str = Field(default="development")


class GenerateTestsRequest(BaseModel):
    feature_description: str = Field(..., min_length=10)
    test_type: str = Field(default="unit")
    num_tests: int = Field(default=5, ge=1, le=20)
    use_scraped_data: bool = Field(default=True)
    scraped_data_id: Optional[str] = None


class AnalyzeFailureRequest(BaseModel):
    test_run_id: str
    test_name: str = ""


class HealSelectorRequest(BaseModel):
    broken_selector: str
    selector_type: str = "css"
    element_description: str
    page_html: str
    error_message: str = ""


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    context: Optional[dict] = None


class ScrapeRequest(BaseModel):
    url: str
    data_type: str = "table"
    css_selector: str = ""


# ── Health Check ─────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint for Docker/load balancer."""
    from django.db import connection
    import redis as redis_lib
    from django.conf import settings

    db_ok = False
    redis_ok = False

    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    try:
        r = redis_lib.from_url(settings.REDIS_URL)
        r.ping()
        redis_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if db_ok and redis_ok else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        services={"database": db_ok, "redis": redis_ok},
    )


# ── Test Suites ───────────────────────────────────────────────
@app.get("/api/suites", tags=["Test Suites"])
async def list_suites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """List all test suites with filtering and pagination."""
    from apps.core.models import TestSuite

    qs = TestSuite.objects.all()
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(name__icontains=search)

    total = await get_test_suites_count(qs)
    offset = (page - 1) * page_size
    suites = await get_test_suites_slice(qs, offset, page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "id": str(s.id),
                "name": s.name,
                "description": s.description,
                "status": s.status,
                "total_cases": s.total_cases,
                "pass_rate": s.pass_rate,
                "tags": s.tags,
                "created_at": s.created_at.isoformat(),
            }
            for s in suites
        ],
    }


@app.get("/api/suites/{suite_id}", tags=["Test Suites"])
async def get_suite(suite_id: str):
    """Get a single test suite with its test cases."""
    try:
        suite = await get_test_suite_by_id(suite_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Test suite not found")

    return {
        "id": str(suite.id),
        "name": suite.name,
        "description": suite.description,
        "status": suite.status,
        "total_cases": suite.total_cases,
        "pass_rate": suite.pass_rate,
        "tags": suite.tags,
        "target_url": suite.target_url,
        "test_cases": [
            {
                "id": str(tc.id),
                "name": tc.name,
                "test_type": tc.test_type,
                "priority": tc.priority,
                "is_ai_generated": tc.is_ai_generated,
            }
            for tc in suite.test_cases.all()
        ],
    }


# ── Test Runs ─────────────────────────────────────────────────
@app.get("/api/runs", tags=["Test Runs"])
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    suite_id: Optional[str] = None,
    status: Optional[str] = None,
):
    """List test runs with filtering."""
    from apps.core.models import TestRun

    qs = TestRun.objects.select_related('suite').all()
    if suite_id:
        qs = qs.filter(suite_id=suite_id)
    if status:
        qs = qs.filter(status=status)

    total = await get_test_runs_count(qs)
    offset = (page - 1) * page_size
    runs = await get_test_runs_slice(qs, offset, page_size)

    return {
        "total": total,
        "results": [
            {
                "id": str(r.id),
                "suite_name": r.suite.name,
                "status": r.status,
                "result": r.result,
                "total_tests": r.total_tests,
                "passed": r.passed,
                "failed": r.failed,
                "errors": r.errors,
                "skipped": r.skipped,
                "pass_rate": r.pass_rate,
                "duration_seconds": r.duration_seconds,
                "environment": r.environment,
                "created_at": r.created_at.isoformat(),
            }
            for r in runs
        ],
    }


@app.post("/api/runs/trigger", tags=["Test Runs"])
async def trigger_test_run(request: TriggerRunRequest):
    """Trigger a test run via Celery async task."""
    from apps.core.models import TestSuite, TestRun
    from apps.testrunner.tasks import execute_test_suite_task

    try:
        suite = await get_test_suite_by_id_for_trigger(request.suite_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Suite not found")

    run = await create_test_run(suite, request.environment)

    task = execute_test_suite_task.delay(str(run.id))
    await update_test_run_task_id(run, task.id)

    logger.info("api.run.triggered", run_id=str(run.id), suite=suite.name)

    return {"run_id": str(run.id), "task_id": task.id, "status": "pending"}


# ── Dashboard Stats ───────────────────────────────────────────
@app.get("/api/dashboard/stats", tags=["Dashboard"])
async def get_dashboard_stats():
    """Aggregate stats for the main dashboard."""
    data = await get_dashboard_stats_data()
    
    return {
        "totals": {
            "suites": data["total_suites"],
            "cases": data["total_cases"],
            "runs": data["total_runs"],
            "runs_today": data["runs_today"],
            "open_bugs": data["open_bugs"],
            "scraped_records": data["scraped_records"],
        },
        "trend": data["trend"],
        "recent_failures": [
            {
                "id": str(r.id),
                "suite": r.suite.name,
                "failed": r.failed,
                "total": r.total_tests,
                "created_at": r.created_at.isoformat(),
            }
            for r in data["recent_failures"]
        ],
    }


# ── AI Agents ─────────────────────────────────────────────────
@app.post("/api/agents/generate-tests", tags=["AI Agents"])
async def generate_tests(request: GenerateTestsRequest):
    """Agent 1: Generate pytest test cases using Gemini AI."""
    from apps.agents.agents import TestCaseGeneratorAgent
    from apps.scraper.models import ScrapedData

    scraped_data = None
    if request.use_scraped_data:
        if request.scraped_data_id:
            try:
                sd = await sync_to_async(ScrapedData.objects.get)(id=request.scraped_data_id)
                scraped_data = await sync_to_async(sd.as_pytest_fixtures)()
            except ScrapedData.DoesNotExist:
                pass
        else:
            latest = await sync_to_async(
                lambda: ScrapedData.objects.filter(
                    status=ScrapedData.DataStatus.VALIDATED
                ).order_by('-created_at').first()
            )()
            if latest:
                scraped_data = await sync_to_async(latest.as_pytest_fixtures)()

    agent = TestCaseGeneratorAgent()
    result = agent.generate(
        feature_description=request.feature_description,
        scraped_data=scraped_data,
        test_type=request.test_type,
        num_tests=request.num_tests,
    )

    if 'error' in result and not result.get('code'):
        raise HTTPException(status_code=500, detail=result['error'])

    return result


@app.post("/api/agents/analyze-failure", tags=["AI Agents"])
async def analyze_failure(request: AnalyzeFailureRequest):
    """Agent 2: AI root cause analysis of test failure."""
    from apps.agents.agents import FailureAnalyzerAgent
    from apps.core.models import TestRun

    try:
        run = await sync_to_async(TestRun.objects.get)(id=request.test_run_id)
    except TestRun.DoesNotExist:
        raise HTTPException(status_code=404, detail="Test run not found")

    agent = FailureAnalyzerAgent()
    logs = await sync_to_async(lambda: run.logs)()
    result = agent.analyze(
        logs=logs,
        test_name=request.test_name or f"Run #{str(run.id)[:8]}",
    )

    # Save AI analysis to bug reports
    bug = await sync_to_async(lambda: run.bug_reports.first())()
    if bug and 'root_cause' in result:
        bug.ai_analysis = result.get('root_cause', '') + '\n\n' + result.get('detailed_explanation', '')
        bug.ai_fix_suggestion = result.get('fix_suggestion', '')
        await sync_to_async(bug.save)(update_fields=['ai_analysis', 'ai_fix_suggestion'])

    return result


@app.post("/api/agents/heal-selector", tags=["AI Agents"])
async def heal_selector(request: HealSelectorRequest):
    """Agent 3: Self-healing Selenium selector repair."""
    from apps.agents.agents import SelfHealingSelectorAgent

    agent = SelfHealingSelectorAgent()
    result = agent.heal(
        broken_selector=request.broken_selector,
        selector_type=request.selector_type,
        element_description=request.element_description,
        page_html=request.page_html,
        error_message=request.error_message,
    )

    if 'error' in result:
        raise HTTPException(status_code=500, detail=result['error'])

    return result


@app.post("/api/agents/chat", tags=["AI Agents"])
async def agent_chat(request: ChatRequest):
    """QA assistant chat — ask anything about your test suite."""
    from apps.agents.agents import QAChatAgent

    agent = QAChatAgent()
    response = agent.chat(message=request.message, context=request.context)
    return {"response": response, "timestamp": datetime.utcnow().isoformat()}


# ── Scraper ───────────────────────────────────────────────────
@app.get("/api/scraper/data", tags=["Scraper"])
async def list_scraped_data(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all scraped data records."""
    from apps.scraper.models import ScrapedData

    qs = ScrapedData.objects.select_related('target').all()
    total = await get_scraped_data_count(qs)
    offset = (page - 1) * page_size
    records = await get_scraped_data_slice(qs, offset, page_size)

    return {
        "total": total,
        "results": [
            {
                "id": str(r.id),
                "title": r.title,
                "target": r.target.name,
                "row_count": r.row_count,
                "column_count": r.column_count,
                "status": r.status,
                "source_url": r.source_url,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ],
    }


@app.post("/api/scraper/trigger", tags=["Scraper"])
async def trigger_scrape(request: ScrapeRequest):
    """Trigger a manual scraping job."""
    from apps.scraper.tasks import scrape_custom_url_task

    task = scrape_custom_url_task.delay(
        url=request.url,
        data_type=request.data_type,
        css_selector=request.css_selector,
    )

    return {"task_id": task.id, "status": "triggered", "url": request.url}


# ── WebSocket — Live Test Log Streaming ───────────────────────
@app.websocket("/ws/runs/{run_id}/logs")
async def websocket_test_logs(websocket: WebSocket, run_id: str):
    """
    WebSocket endpoint: streams live test execution logs to the UI.
    Connect from JS: const ws = new WebSocket('ws://localhost:8001/ws/runs/{id}/logs')
    """
    await manager.connect(websocket, room=run_id)
    try:
        # Send initial status
        try:
            run = await get_test_run_for_websocket(run_id)
            await websocket.send_json({
                "type": "init",
                "status": run.status,
                "run_id": run_id,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception:
            await websocket.send_json({"type": "error", "message": "Run not found"})

        # Keep connection alive, relay messages from Celery via Redis pubsub
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()})

    except WebSocketDisconnect:
        manager.disconnect(websocket, room=run_id)
        logger.info("ws.client_disconnected", run_id=run_id)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket for real-time AI agent chat."""
    await manager.connect(websocket, room="chat")
    from apps.agents.agents import QAChatAgent
    agent = QAChatAgent()

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            if message:
                await websocket.send_json({"type": "typing", "status": True})
                response = agent.chat(message)
                await websocket.send_json({
                    "type": "response",
                    "message": response,
                    "timestamp": datetime.utcnow().isoformat(),
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket, room="chat")