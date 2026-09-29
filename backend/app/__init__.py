import os
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import config
from app.extensions import db, migrate
from app.routes.health import health_bp
from app.routes.auth import auth_bp
from app.routes.files import files_bp
from app.routes.versions import versions_bp
from app.routes.shares import shares_bp
from app.routes.trash import trash_bp
from app.routes.analytics import analytics_bp
from app.routes.uploads import uploads_bp
from app.routes.metrics import metrics_bp
from app.services.logger import setup_logger
from app.services.storage_service import storage_service
from app.services.cache_service import cache_service

def create_app(custom_config=None) -> Flask:
    """Application factory for CloudBox Backend."""
    app = Flask(__name__)
    app.config.from_object(config)

    if custom_config:
        app.config.update(custom_config)

    # Configure structured logging and request observability
    setup_logger(app)

    # Enable CORS for frontend cross-origin requests
    CORS(
        app,
        resources={
            r"/api/*": {"origins": "*"},
            r"/health": {"origins": "*"},
        },
        supports_credentials=True,
    )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(versions_bp)
    app.register_blueprint(shares_bp)
    app.register_blueprint(trash_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(metrics_bp)

    # Standard JSON Error Handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "code": "BAD_REQUEST"}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized access", "code": "UNAUTHORIZED"}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "Access forbidden", "code": "FORBIDDEN"}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found", "code": "NOT_FOUND"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed", "code": "METHOD_NOT_ALLOWED"}), 405

    @app.errorhandler(410)
    def gone(error):
        return jsonify({"error": "Resource gone or expired", "code": "GONE"}), 410

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            "error": f"File size exceeds maximum limit of {config.MAX_CONTENT_LENGTH // (1024 * 1024)} MB.",
            "code": "PAYLOAD_TOO_LARGE"
        }), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({"error": "An internal server error occurred.", "code": "INTERNAL_ERROR"}), 500

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({
            "message": "CloudBox API is online",
            "version": "5.0.0-phase5",
            "features": {
                "versioning": True,
                "sharing": True,
                "recycle_bin": True,
                "analytics": True,
                "redis_caching": cache_service.is_available,
                "background_processing": True,
                "chunked_uploads": True,
                "production_hardened": True
            }
        }), 200

    # Auto-initialize database tables and MinIO default bucket if in runtime mode
    with app.app_context():
        try:
            db.create_all()
            # Non-destructive column additions for existing PostgreSQL tables
            with db.engine.connect() as conn:
                try:
                    conn.execute(db.text("ALTER TABLE files ADD COLUMN IF NOT EXISTS thumbnail_object_key VARCHAR(255) DEFAULT NULL;"))
                    conn.execute(db.text("ALTER TABLE files ADD COLUMN IF NOT EXISTS processing_status VARCHAR(32) DEFAULT 'completed' NOT NULL;"))
                    conn.execute(db.text("ALTER TABLE files ADD COLUMN IF NOT EXISTS extracted_metadata JSONB DEFAULT NULL;"))
                    conn.execute(db.text("ALTER TABLE files ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL;"))
                    conn.commit()
                except Exception:
                    pass
        except Exception as e:
            print(f"[*] Notice: Database table auto-check: {e}")

        try:
            storage_service.ensure_bucket_exists()
        except Exception as e:
            print(f"[*] Notice: MinIO bucket check: {e}")

    return app
