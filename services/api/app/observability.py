from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from contextvars import ContextVar
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from starlette.middleware.base import BaseHTTPMiddleware

from .settings import Settings

logger = logging.getLogger("aegisdesk.api")
tracer = trace.get_tracer("aegisdesk.api")
correlation_id = ContextVar("aegisdesk_correlation_id", default="request-unavailable")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        for key in ("method", "path", "status_code", "duration_ms", "trace_id", "correlation_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"))


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        started = time.perf_counter()
        token = correlation_id.set(f"req-{uuid4().hex}")
        try:
            response = await call_next(request)
        except Exception:
            correlation_id.reset(token)
            raise
        response.headers["X-AegisDesk-Correlation-ID"] = current_correlation_id()
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "trace_id": current_trace_id(),
                "correlation_id": current_correlation_id(),
            },
        )
        correlation_id.reset(token)
        return response


def configure_observability(app: FastAPI, settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)

    if settings.otlp_endpoint:
        provider = TracerProvider(resource=Resource.create({"service.name": settings.service_name}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint)))
        trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    app.add_middleware(RequestLogMiddleware)


def current_trace_id() -> str:
    span_context = trace.get_current_span().get_span_context()
    if not span_context.is_valid:
        return "trace-unavailable"
    return f"{span_context.trace_id:032x}"


def current_correlation_id() -> str:
    return correlation_id.get()
