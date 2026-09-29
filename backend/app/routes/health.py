from datetime import datetime, timezone
from flask import Blueprint, jsonify
from app.config import config

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for container health probes and orchestration monitoring.
    """
    return jsonify({
        "status": "healthy",
        "service": "cloudbox-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": config.APP_ENV,
        "database": {
            "host": config.POSTGRES_HOST,
            "database": config.POSTGRES_DB
        },
        "storage": {
            "host": config.MINIO_HOST,
            "port": config.MINIO_PORT
        }
    }), 200
