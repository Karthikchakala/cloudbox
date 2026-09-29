import os
import time
import json
import logging
import uuid
from flask import request, g, has_request_context

SENSITIVE_KEYS = {
    "password", "token", "access_token", "secret", "authorization",
    "jwt_secret_key", "secret_key", "postgres_password", "minio_root_password"
}

class StructuredJSONFormatter(logging.Formatter):
    """Custom logging formatter that outputs JSON lines for observability."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt or "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach request context if running inside a Flask request
        if has_request_context():
            log_entry["request_id"] = getattr(g, "request_id", None) or request.headers.get("X-Request-ID", "internal")
            log_entry["method"] = request.method
            log_entry["path"] = request.path
            log_entry["remote_addr"] = request.headers.get("X-Forwarded-For", request.remote_addr)
            if hasattr(g, "current_user") and g.current_user:
                log_entry["user_id"] = str(g.current_user.id)
                log_entry["username"] = g.current_user.username

        # Attach extra structured fields if passed via extra={}
        if hasattr(record, "structured_data") and isinstance(record.structured_data, dict):
            for k, v in record.structured_data.items():
                if k.lower() in SENSITIVE_KEYS:
                    log_entry[k] = "[REDACTED]"
                else:
                    log_entry[k] = v

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)

def setup_logger(app):
    """Configure structured logging and request ID middleware on Flask app."""
    log_level = logging.INFO if app.config.get("APP_ENV") == "production" else logging.DEBUG
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(StructuredJSONFormatter())

    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    @app.before_request
    def before_request_logging():
        g.start_time = time.time()
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    @app.after_request
    def after_request_logging(response):
        # Attach Request-ID to response headers for distributed tracing
        response.headers["X-Request-ID"] = getattr(g, "request_id", str(uuid.uuid4()))
        
        # Security headers injection
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Do not log health checks in flood
        if request.path != "/health":
            latency_ms = round((time.time() - getattr(g, "start_time", time.time())) * 1000, 2)
            extra_data = {
                "structured_data": {
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                    "content_length": response.content_length or 0
                }
            }
            app.logger.info(
                f"{request.method} {request.path} {response.status_code} ({latency_ms}ms)",
                extra=extra_data
            )
        return response
