import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class UploadSession(db.Model):
    __tablename__ = "upload_sessions"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_file_id = db.Column(UUID(as_uuid=True), db.ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    content_type = db.Column(db.String(128), nullable=False, default="application/octet-stream")
    total_chunks = db.Column(db.Integer, nullable=False)
    chunk_size = db.Column(db.Integer, nullable=False)
    uploaded_chunks = db.Column(db.JSON, nullable=False, default=list)
    checksum_sha256 = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="initiated", index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    expires_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=24),
        nullable=False,
        index=True
    )

    # Relationships
    user = db.relationship("User")
    target_file = db.relationship("File")

    @property
    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        exp = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
        return now > exp

    def to_dict(self) -> dict:
        return {
            "upload_id": str(self.id),
            "user_id": str(self.user_id),
            "target_file_id": str(self.target_file_id) if self.target_file_id else None,
            "filename": self.filename,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "total_chunks": self.total_chunks,
            "chunk_size": self.chunk_size,
            "uploaded_chunks": self.uploaded_chunks or [],
            "progress_percent": round((len(self.uploaded_chunks or []) / self.total_chunks * 100), 1) if self.total_chunks > 0 else 0.0,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
        }

    def __repr__(self) -> str:
        return f"<UploadSession {self.id} for {self.filename} ({len(self.uploaded_chunks or [])}/{self.total_chunks} chunks)>"
