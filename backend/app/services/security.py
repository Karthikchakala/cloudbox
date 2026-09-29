import re
import uuid
import jwt
from functools import wraps
from datetime import datetime, timezone, timedelta
from flask import request, jsonify, g, current_app
from app.config import config
from app.extensions import db
from app.models.user import User

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,50}$")

def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

def validate_username(username: str) -> bool:
    """Validate username length and characters (3-50 chars, alphanumeric, _ -)."""
    if not username or not isinstance(username, str):
        return False
    return bool(USERNAME_REGEX.match(username.strip()))

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password complexity (minimum 8 chars)."""
    if not password or not isinstance(password, str):
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."
    return True, ""

def get_jwt_secret() -> str:
    try:
        return current_app.config.get("JWT_SECRET_KEY", config.JWT_SECRET_KEY)
    except RuntimeError:
        return config.JWT_SECRET_KEY

def generate_jwt_token(user_id: str, email: str, username: str, expires_in: int = None) -> str:
    """Generate signed JWT access token."""
    if expires_in is None:
        try:
            expires_in = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", config.JWT_ACCESS_TOKEN_EXPIRES)
        except RuntimeError:
            expires_in = config.JWT_ACCESS_TOKEN_EXPIRES

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "username": username,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "iss": "cloudbox-auth",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm="HS256")

def decode_jwt_token(token: str) -> dict:
    """Decode and verify JWT access token."""
    try:
        return jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=["HS256"],
            issuer="cloudbox-auth",
            options={"require": ["exp", "iat", "sub"]}
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid authentication token.")

def jwt_required(f):
    """Decorator to require valid JWT Bearer token in request header or auth cookie."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = None

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        elif "access_token" in request.cookies:
            token = request.cookies.get("access_token")

        if not token:
            return jsonify({
                "error": "Authentication required. Bearer token missing.",
                "code": "UNAUTHORIZED"
            }), 401

        try:
            payload = decode_jwt_token(token)
            user_id_str = payload.get("sub")
            try:
                user_id = uuid.UUID(str(user_id_str))
            except (ValueError, TypeError):
                user_id = user_id_str

            user = db.session.get(User, user_id)
            if not user:
                return jsonify({
                    "error": "User associated with this token does not exist.",
                    "code": "USER_NOT_FOUND"
                }), 401

            # Attach authenticated user to request context
            g.current_user = user
        except ValueError as e:
            return jsonify({
                "error": str(e),
                "code": "INVALID_TOKEN"
            }), 401
        except Exception:
            return jsonify({
                "error": "Authentication failed.",
                "code": "AUTH_ERROR"
            }), 401

        return f(*args, **kwargs)

    return decorated_function
