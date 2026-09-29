import uuid
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

class FileVersion(db.Model):
    __tablename__ = "file_versions"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False)
    object_key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(128), nullable=False, default="application/octet-stream")
    size_bytes = db.Column(db.BigInteger, nullable=False)
    checksum_sha256 = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Constraints
    __table_args__ = (
        db.UniqueConstraint("file_id", "version_number", name="uq_file_version_number"),
    )

    # Relationships
    file = db.relationship("File", back_populates="versions")
    creator = db.relationship("User", foreign_keys=[created_by])

    def to_dict(self, is_current: bool = False) -> dict:
        """Return safe metadata for a specific file version."""
        return {
            "id": str(self.id),
            "file_id": str(self.file_id),
            "version_number": self.version_number,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": str(self.created_by) if self.created_by else None,
            "is_current": is_current,
        }

    def __repr__(self) -> str:
        return f"<FileVersion v{self.version_number} for File {self.file_id}>"
