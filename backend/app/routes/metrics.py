import os
import time
import json
from datetime import datetime, timezone
from flask import Blueprint, jsonify, Response
from sqlalchemy import func

from app.extensions import db
from app.models.file import File
from app.models.user import User
from app.models.upload_session import UploadSession
from app.services.cache_service import cache_service

metrics_bp = Blueprint("metrics", __name__, url_prefix="/api/metrics")

START_TIME = time.time()
BACKUP_STATUS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backups", "backup_status.json"))

@metrics_bp.route("", methods=["GET"])
def get_system_metrics():
    """
    Operational metrics and telemetry (JSON format):
    - Redis Cache Hit/Miss ratio
    - Upload sessions throughput
    - Storage and user aggregate counts
    - Service uptime
    """
    uptime_seconds = int(time.time() - START_TIME)
    cache_stats = cache_service.get_stats()

    try:
        total_users = db.session.query(func.count(User.id)).scalar() or 0
        total_files = db.session.query(func.count(File.id)).scalar() or 0
        active_files = db.session.query(func.count(File.id)).filter(File.deleted_at.is_(None)).scalar() or 0
        active_upload_sessions = db.session.query(func.count(UploadSession.id)).filter(UploadSession.status == "uploading").scalar() or 0
        db_healthy = True
    except Exception:
        total_users = 0
        total_files = 0
        active_files = 0
        active_upload_sessions = 0
        db_healthy = False

    return jsonify({
        "status": "healthy" if db_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "cache": cache_stats,
        "database": {
            "healthy": db_healthy,
            "total_users": total_users,
            "total_files": total_files,
            "active_files": active_files,
            "active_upload_sessions": active_upload_sessions,
        },
        "features": {
            "caching": cache_stats["connected"],
            "background_worker": True,
            "chunked_uploads": True,
        }
    }), 200

@metrics_bp.route("/prometheus", methods=["GET"])
def get_prometheus_metrics():
    """
    Prometheus text exposition format endpoint for scraping.
    """
    uptime_seconds = int(time.time() - START_TIME)
    cache_stats = cache_service.get_stats()

    try:
        total_users = db.session.query(func.count(User.id)).scalar() or 0
        total_files = db.session.query(func.count(File.id)).scalar() or 0
        active_files = db.session.query(func.count(File.id)).filter(File.deleted_at.is_(None)).scalar() or 0
        active_upload_sessions = db.session.query(func.count(UploadSession.id)).filter(UploadSession.status == "uploading").scalar() or 0
        db_up = 1
    except Exception:
        total_users = 0
        total_files = 0
        active_files = 0
        active_upload_sessions = 0
        db_up = 0

    redis_up = 1 if cache_stats.get("connected") else 0
    cache_hits = cache_stats.get("hits", 0)
    cache_misses = cache_stats.get("misses", 0)
    raw_hit_ratio = cache_stats.get("hit_ratio_percent", 0.0)
    if isinstance(raw_hit_ratio, str):
        try:
            hit_ratio = float(raw_hit_ratio.replace("%", "").strip() or 0) / 100.0
        except ValueError:
            hit_ratio = 0.0
    elif isinstance(raw_hit_ratio, (int, float)):
        hit_ratio = float(raw_hit_ratio) / 100.0 if raw_hit_ratio > 1.0 else float(raw_hit_ratio)
    else:
        hit_ratio = 0.0

    # Read latest backup status
    backup_status_val = 1
    backup_timestamp_val = 0
    backup_size_val = 0
    recovery_verified_val = 1
    if os.path.exists(BACKUP_STATUS_PATH):
        try:
            with open(BACKUP_STATUS_PATH, "r", encoding="utf-8") as f:
                bdata = json.load(f)
                backup_status_val = 1 if bdata.get("status") == "SUCCESS" else 0
                backup_size_val = bdata.get("bundle", {}).get("size_bytes", 0)
                recovery_verified_val = 1 if bdata.get("recovery_verification", {}).get("passed") else 0
        except Exception:
            pass

    lines = [
        "# HELP cloudbox_uptime_seconds CloudBox Backend uptime in seconds",
        "# TYPE cloudbox_uptime_seconds gauge",
        f"cloudbox_uptime_seconds {uptime_seconds}",
        "",
        "# HELP cloudbox_db_up PostgreSQL database connectivity status (1=up, 0=down)",
        "# TYPE cloudbox_db_up gauge",
        f"cloudbox_db_up {db_up}",
        "",
        "# HELP cloudbox_redis_up Redis cache and broker connectivity status (1=up, 0=down)",
        "# TYPE cloudbox_redis_up gauge",
        f"cloudbox_redis_up {redis_up}",
        "",
        "# HELP cloudbox_users_total Total registered user accounts",
        "# TYPE cloudbox_users_total gauge",
        f"cloudbox_users_total {total_users}",
        "",
        "# HELP cloudbox_files_total Total files uploaded across system",
        "# TYPE cloudbox_files_total gauge",
        f"cloudbox_files_total {total_files}",
        "",
        "# HELP cloudbox_files_active Active non-deleted files in system",
        "# TYPE cloudbox_files_active gauge",
        f"cloudbox_files_active {active_files}",
        "",
        "# HELP cloudbox_active_upload_sessions Currently active chunked upload sessions",
        "# TYPE cloudbox_active_upload_sessions gauge",
        f"cloudbox_active_upload_sessions {active_upload_sessions}",
        "",
        "# HELP cloudbox_cache_hits_total Total Redis cache hits",
        "# TYPE cloudbox_cache_hits_total counter",
        f"cloudbox_cache_hits_total {cache_hits}",
        "",
        "# HELP cloudbox_cache_misses_total Total Redis cache misses",
        "# TYPE cloudbox_cache_misses_total counter",
        f"cloudbox_cache_misses_total {cache_misses}",
        "",
        "# HELP cloudbox_cache_hit_ratio Redis cache hit ratio (0.0 to 1.0)",
        "# TYPE cloudbox_cache_hit_ratio gauge",
        f"cloudbox_cache_hit_ratio {hit_ratio}",
        "",
        "# HELP cloudbox_backup_latest_status Latest backup pipeline status (1=success, 0=failure)",
        "# TYPE cloudbox_backup_latest_status gauge",
        f"cloudbox_backup_latest_status {backup_status_val}",
        "",
        "# HELP cloudbox_backup_latest_size_bytes Byte size of the most recent backup bundle",
        "# TYPE cloudbox_backup_latest_size_bytes gauge",
        f"cloudbox_backup_latest_size_bytes {backup_size_val}",
        "",
        "# HELP cloudbox_backup_recovery_verification_status Latest isolated recovery verification (1=passed, 0=failed)",
        "# TYPE cloudbox_backup_recovery_verification_status gauge",
        f"cloudbox_backup_recovery_verification_status {recovery_verified_val}",
    ]

    return Response("\n".join(lines) + "\n", mimetype="text/plain; version=0.0.4")

