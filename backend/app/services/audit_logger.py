import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from flask import request, g, has_request_context

logger = logging.getLogger("cloudbox.security.audit")

SENSITIVE_REDACT_KEYS = {
    "password", "token", "access_token", "secret", "authorization",
    "jwt_secret_key", "secret_key", "password_hash", "token_hash"
}

def sanitize_audit_data(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Remove or redact sensitive parameters from audit logs."""
    if not data or not isinstance(data, dict):
        return {}
    sanitized = {}
    for k, v in data.items():
        if k.lower() in SENSITIVE_REDACT_KEYS:
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_audit_data(v)
        else:
            sanitized[k] = v
    return sanitized

def log_security_event(
    event_type: str,
    action: str,
    status: str = "SUCCESS",
    user_id: Optional[str] = None,
    target_resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
):
    """
    Record an immutable security audit event.
    Logs structured JSON with timestamp, event category, actor, status, and target.
    """
    req_id = "system"
    remote_ip = ip_address or "127.0.0.1"

    if has_request_context():
        req_id = getattr(g, "request_id", None) or request.headers.get("X-Request-ID", "internal")
        remote_ip = ip_address or request.headers.get("X-Forwarded-For", request.remote_addr)
        if not user_id and hasattr(g, "current_user") and g.current_user:
            user_id = str(g.current_user.id)

    audit_entry = {
        "audit_type": "SECURITY_EVENT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": req_id,
        "event_type": event_type,
        "action": action,
        "status": status.upper(),
        "actor_user_id": str(user_id) if user_id else "anonymous",
        "target_resource_id": str(target_resource_id) if target_resource_id else None,
        "client_ip": remote_ip,
        "details": sanitize_audit_data(details)
    }

    log_msg = f"SECURITY_AUDIT: event={event_type} action={action} status={status.upper()} actor={audit_entry['actor_user_id']}"
    if status.upper() in ("FAIL", "DENIED", "UNAUTHORIZED", "FORBIDDEN"):
        logger.warning(log_msg, extra={"structured_data": audit_entry})
    else:
        logger.info(log_msg, extra={"structured_data": audit_entry})

    return audit_entry
