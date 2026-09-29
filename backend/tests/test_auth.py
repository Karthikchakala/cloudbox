import json
from app.models.user import User

def test_register_success(client):
    """Test standard successful registration."""
    res = client.post("/api/auth/register", json={
        "username": "newuser",
        "email": "newuser@cloudbox.local",
        "password": "ValidPassword123!"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["username"] == "newuser"
    assert data["user"]["email"] == "newuser@cloudbox.local"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

def test_register_duplicate_email(client, test_user):
    """Test duplicate email rejection (409 Conflict)."""
    res = client.post("/api/auth/register", json={
        "username": "differentname",
        "email": test_user.email,
        "password": "ValidPassword123!"
    })
    assert res.status_code == 409
    data = res.get_json()
    assert data["code"] == "EMAIL_ALREADY_EXISTS"

def test_register_duplicate_username(client, test_user):
    """Test duplicate username rejection (409 Conflict)."""
    res = client.post("/api/auth/register", json={
        "username": test_user.username,
        "email": "another@cloudbox.local",
        "password": "ValidPassword123!"
    })
    assert res.status_code == 409
    data = res.get_json()
    assert data["code"] == "USERNAME_ALREADY_EXISTS"

def test_register_invalid_inputs(client):
    """Test validations for email, username, and password."""
    # Invalid email
    res1 = client.post("/api/auth/register", json={
        "username": "validuser",
        "email": "notanemail",
        "password": "Password123!"
    })
    assert res1.status_code == 400

    # Short password
    res2 = client.post("/api/auth/register", json={
        "username": "validuser",
        "email": "valid@email.com",
        "password": "short"
    })
    assert res2.status_code == 400

    # Invalid username format
    res3 = client.post("/api/auth/register", json={
        "username": "us er with spaces!",
        "email": "valid@email.com",
        "password": "Password123!"
    })
    assert res3.status_code == 400

def test_login_success(client, test_user):
    """Test successful login returning JWT token."""
    res = client.post("/api/auth/login", json={
        "email": test_user.email,
        "password": "SecurePassword123!"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "access_token" in data
    assert data["user"]["email"] == test_user.email

def test_login_invalid_credentials(client, test_user):
    """Test login failure on incorrect password."""
    res = client.post("/api/auth/login", json={
        "email": test_user.email,
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert res.get_json()["code"] == "INVALID_CREDENTIALS"

def test_login_nonexistent_user(client):
    """Test login failure on nonexistent email."""
    res = client.post("/api/auth/login", json={
        "email": "doesnotexist@cloudbox.local",
        "password": "Password123!"
    })
    assert res.status_code == 401
    assert res.get_json()["code"] == "INVALID_CREDENTIALS"

def test_get_current_user_authenticated(client, test_user, auth_headers):
    """Test /api/auth/me with valid Bearer token."""
    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["user"]["username"] == test_user.username
    assert data["user"]["email"] == test_user.email

def test_get_current_user_unauthenticated(client):
    """Test /api/auth/me without token (401 Unauthorized)."""
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.get_json()["code"] == "UNAUTHORIZED"

def test_get_current_user_invalid_token(client):
    """Test /api/auth/me with malformed token."""
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.fake.token"})
    assert res.status_code == 401
