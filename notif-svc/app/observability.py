import logging
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

SERVICE_NAME = "notif-svc"


def _add_service_name(logger, method_name, event_dict):
    event_dict["service"] = SERVICE_NAME
    return event_dict


def _configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_service_name,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


_configure_logging()
logger = structlog.get_logger()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        logger.info("request_started", method=request.method, path=request.url.path)
        response = await call_next(request)
        logger.info("request_finished", status_code=response.status_code)

        response.headers["x-correlation-id"] = correlation_id
        return response
