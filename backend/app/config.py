import os
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

class Config:
    """Base application configuration with environment variable validation."""
    
    APP_ENV = os.getenv("APP_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "1").lower() in ("1", "true", "yes")
    SECRET_KEY = os.getenv("SECRET_KEY", "cloudbox-dev-secret-key-phase2-active")
    PORT = int(os.getenv("BACKEND_PORT", 5000))

    # JWT Authentication Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "cloudbox-jwt-dev-secret-key-phase2-active")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400))  # 24 hours

    # File Upload Limits (Default 50 MB)
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 52428800))

    # PostgreSQL Connection Settings
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "cloudbox_db")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "cloudbox_user")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password123")

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # MinIO Object Storage Settings
    MINIO_HOST = os.getenv("MINIO_HOST", "minio")
    MINIO_PORT = int(os.getenv("MINIO_API_PORT", 9000))
    MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "cloudbox_admin")
    MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "password123")
    MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("1", "true", "yes")
    MINIO_DEFAULT_BUCKET = os.getenv("MINIO_DEFAULT_BUCKET", "cloudbox-uploads")

    @property
    def MINIO_ENDPOINT(self) -> str:
        return f"{self.MINIO_HOST}:{self.MINIO_PORT}"

    # Redis Cache & Broker Settings
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "password123")
    REDIS_DB = int(os.getenv("REDIS_DB", 0))

    def validate_production_secrets(self) -> None:
        """
        Validate that required production security settings and secrets are properly configured.
        Raises RuntimeError if default or weak credentials are detected in production mode.
        """
        insecure_defaults = {
            "SECRET_KEY": "cloudbox-dev-secret-key-phase2-active",
            "JWT_SECRET_KEY": "cloudbox-jwt-dev-secret-key-phase2-active",
            "POSTGRES_PASSWORD": "password123",
            "MINIO_ROOT_PASSWORD": "password123",
            "REDIS_PASSWORD": "password123"
        }

        if self.APP_ENV.lower() in ("production", "prod"):
            for key, default_val in insecure_defaults.items():
                current_val = getattr(self, key, "")
                if current_val == default_val or len(current_val) < 16:
                    raise RuntimeError(
                        f"CRITICAL SECURITY CONFIGURATION ERROR: '{key}' is using an insecure default or weak value in production environment. "
                        f"Set a strong unique secret of at least 16 characters in environment variables."
                    )

config = Config()
