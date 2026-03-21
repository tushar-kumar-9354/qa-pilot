"""QA-PILOT — Structured Logging Middleware"""
import time
import uuid
import structlog

logger = structlog.get_logger(__name__)


class StructuredLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())[:8]
        start = time.time()

        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = self.get_response(request)

        duration = round((time.time() - start) * 1000, 2)
        logger.info(
            "http.request",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=duration,
            user=str(request.user) if request.user.is_authenticated else "anonymous",
        )

        structlog.contextvars.unbind_contextvars("request_id")
        return response
