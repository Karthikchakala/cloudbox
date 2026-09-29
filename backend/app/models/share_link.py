import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.extensions import db

ph = PasswordHasher()

class ShareLink(db.Model):
    __tablename__ = "share_links"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    permission = db.Column(db.String(32), default="download", nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    max_downloads = db.Column(db.Integer, nullable=True)
    download_count = db.Column(db.Integer, default=0, nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    file = db.relationship("File", back_populates="share_links")
    creator = db.relationship("User", foreign_keys=[created_by])

    def set_password(self, password: str) -> None:
        """Hash and set protection password using Argon2."""
        if password and len(password.strip()) > 0:
            self.password_hash = ph.hash(password.strip())
        else:
            self.password_hash = None

    def check_password(self, password: str) -> bool:
        """Verify the supplied password."""
        if not self.password_hash:
            return True
        if not password:
            return False
        try:
            return ph.verify(self.password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    @property
    def is_active(self) -> bool:
        """Check if link is currently active, unexpired, unrevoked, and has downloads remaining."""
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None:
            now = datetime.now(timezone.utc)
            exp = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
            if now > exp:
                return False
        if self.max_downloads is not None and self.download_count >= self.max_downloads:
            return False
        return True

    def to_dict(self) -> dict:
        """Return safe public-safe metadata without token hash or password hash."""
        return {
            "id": str(self.id),
            "file_id": str(self.file_id),
            "created_by": str(self.created_by),
            "permission": self.permission,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "has_password": self.password_hash is not None,
            "max_downloads": self.max_downloads,
            "download_count": self.download_count,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<ShareLink for File {self.file_id} by {self.created_by}>"
