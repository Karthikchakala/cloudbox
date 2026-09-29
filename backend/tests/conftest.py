import pytest
import io
import uuid
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.file import File
from app.services.security import generate_jwt_token

class DummyMinioStream:
    def __init__(self, data_bytes):
        self.data_bytes = data_bytes

    def stream(self, chunk_size):
        stream = io.BytesIO(self.data_bytes)
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def close(self):
        pass

    def release_conn(self):
        pass

class MockStorageService:
    def __init__(self):
        self.storage = {}

    def ensure_bucket_exists(self, bucket_name=None):
        return True

    def generate_object_key(self, user_id, original_filename):
        return f"{user_id}/{uuid.uuid4().hex}_{original_filename}"

    def compute_sha256(self, data_bytes):
        import hashlib
        return hashlib.sha256(data_bytes).hexdigest()

    def upload_file(self, object_key, data_stream, length, content_type="application/octet-stream", bucket_name=None):
        self.storage[object_key] = {
            "data": data_stream.read(),
            "content_type": content_type,
            "length": length
        }
        return True

    def get_file_stream(self, object_key, bucket_name=None):
        if object_key in self.storage:
            return DummyMinioStream(self.storage[object_key]["data"])
        return None

    def delete_file(self, object_key, bucket_name=None):
        if object_key in self.storage:
            del self.storage[object_key]
            return True
        return False

@pytest.fixture
def app(monkeypatch):
    """Create test application with SQLite in-memory database and comprehensively mocked storage."""
    mock_storage = MockStorageService()
    monkeypatch.setattr("app.routes.files.storage_service", mock_storage)
    monkeypatch.setattr("app.routes.versions.storage_service", mock_storage)
    monkeypatch.setattr("app.routes.shares.storage_service", mock_storage)
    monkeypatch.setattr("app.routes.trash.storage_service", mock_storage)
    monkeypatch.setattr("app.routes.uploads.storage_service", mock_storage)
    monkeypatch.setattr("app.tasks.file_tasks.storage_service", mock_storage)
    monkeypatch.setattr("app.services.storage_service", mock_storage)

    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-jwt-secret-key-12345",
        "JWT_ACCESS_TOKEN_EXPIRES": 3600,
        "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,  # 10 MB for testing
    }

    application = create_app(test_config)

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(id=uuid.uuid4(), username="testuser", email="test@cloudbox.local")
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user

@pytest.fixture
def auth_token(test_user):
    return generate_jwt_token(str(test_user.id), test_user.email, test_user.username)

@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture
def second_user(app):
    with app.app_context():
        user = User(id=uuid.uuid4(), username="seconduser", email="second@cloudbox.local")
        user.set_password("AnotherPassword456!")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user

@pytest.fixture
def second_auth_headers(second_user):
    token = generate_jwt_token(str(second_user.id), second_user.email, second_user.username)
    return {"Authorization": f"Bearer {token}"}
