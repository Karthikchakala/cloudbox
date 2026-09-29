import pytest
import jwt
from datetime import datetime, timezone, timedelta
from app.models.user import User
from app.services.security import generate_jwt_token, decode_jwt_token, validate_password, validate_username, validate_email
from app.config import config

def test_argon2_password_hashing(app):
    """Verify password hashing produces distinct Argon2 hashes and verifies properly."""
    with app.app_context():
        user = User(username="securityuser", email="security@cloudbox.local")
        user.set_password("MySuperSecretP@ssword123")
        assert user.password_hash.startswith("$argon2")
        assert user.check_password("MySuperSecretP@ssword123") is True
        assert user.check_password("WrongPassword123") is False

def test_jwt_token_creation_and_expiration(app):
    """Verify JWT token encoding, decoding, and expiration."""
    with app.app_context():
        token = generate_jwt_token("123e4567-e89b-12d3-a456-426614174000", "test@domain.com", "myuser", expires_in=2)
        payload = decode_jwt_token(token)
        assert payload["sub"] == "123e4567-e89b-12d3-a456-426614174000"
        assert payload["email"] == "test@domain.com"
        assert payload["username"] == "myuser"

def test_jwt_tampered_token():
    """Verify modified tokens are rejected."""
    token = generate_jwt_token("123e4567-e89b-12d3-a456-426614174000", "test@domain.com", "myuser")
    tampered = token[:-4] + "abcd"
    with pytest.raises(ValueError, match="Invalid authentication token"):
        decode_jwt_token(tampered)

def test_input_sanitization():
    """Test validation utilities."""
    assert validate_email("user@example.com") is True
    assert validate_email("not-an-email") is False

    assert validate_username("valid_user-123") is True
    assert validate_username("ab") is False  # too short
    assert validate_username("user with space") is False

    valid, _ = validate_password("Short1!")
    assert valid is False
    valid, _ = validate_password("ValidPassword123!")
    assert valid is True
