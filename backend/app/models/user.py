import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.extensions import db

ph = PasswordHasher()

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    files = db.relationship("File", back_populates="owner", cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash and set user password using Argon2."""
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        self.password_hash = ph.hash(password)

    def check_password(self, password: str) -> bool:
        """Verify user password against the stored Argon2 hash."""
        if not self.password_hash or not password:
            return False
        try:
            return ph.verify(self.password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def to_dict(self) -> dict:
        """Return safe representation of user without sensitive hashes."""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.id})>"
