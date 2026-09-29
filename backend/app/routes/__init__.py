from app.routes.health import health_bp
from app.routes.auth import auth_bp
from app.routes.files import files_bp
from app.routes.versions import versions_bp
from app.routes.shares import shares_bp
from app.routes.trash import trash_bp

__all__ = ["health_bp", "auth_bp", "files_bp", "versions_bp", "shares_bp", "trash_bp"]
