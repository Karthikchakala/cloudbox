import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db

class File(db.Model):
    __tablename__ = "files"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    object_key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    content_type = db.Column(db.String(128), nullable=False, default="application/octet-stream")
    size_bytes = db.Column(db.BigInteger, nullable=False)
    checksum_sha256 = db.Column(db.String(64), nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    thumbnail_object_key = db.Column(db.String(255), nullable=True)
    processing_status = db.Column(db.String(32), nullable=False, default="completed", index=True)
    extracted_metadata = db.Column(db.JSON, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    owner = db.relationship("User", back_populates="files")
    versions = db.relationship("FileVersion", back_populates="file", cascade="all, delete-orphan", order_by="FileVersion.version_number.desc()")
    share_links = db.relationship("ShareLink", back_populates="file", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Return safe metadata for the client."""
        return {
            "id": str(self.id),
            "owner_id": str(self.owner_id),
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "has_thumbnail": bool(self.thumbnail_object_key),
            "processing_status": self.processing_status or "completed",
            "extracted_metadata": self.extracted_metadata or {},
            "version_count": len(self.versions) if self.versions else 1,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<File {self.original_filename} ({self.id}) owner={self.owner_id}>"

