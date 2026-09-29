import os
import io
import uuid
import hashlib
from typing import BinaryIO, Tuple, Optional
from werkzeug.utils import secure_filename
from minio import Minio
from minio.error import S3Error
from app.config import config

class StorageService:
    """Manages object storage operations with MinIO S3 API."""

    def __init__(self):
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                endpoint=config.MINIO_ENDPOINT,
                access_key=config.MINIO_ROOT_USER,
                secret_key=config.MINIO_ROOT_PASSWORD,
                secure=config.MINIO_SECURE,
            )
        return self._client

    @property
    def bucket_name(self) -> str:
        return config.MINIO_DEFAULT_BUCKET

    def ensure_bucket_exists(self, bucket_name: str = None) -> bool:
        """Create the target bucket if it doesn't already exist."""
        bucket = bucket_name or config.MINIO_DEFAULT_BUCKET
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                print(f"[StorageService] Successfully created bucket: '{bucket}'")
            return True
        except Exception as e:
            print(f"[StorageService] Bucket check/creation warning for '{bucket}': {e}")
            return False

    def generate_object_key(self, user_id: str, original_filename: str) -> str:
        """
        Generate a cryptographically unique object key.
        Prevents path traversal and file collisions while preserving extension.
        Format: {user_id}/{uuid4}_{sanitized_basename}
        """
        clean_name = secure_filename(original_filename) or "unnamed_file"
        unique_id = uuid.uuid4().hex
        return f"{user_id}/{unique_id}_{clean_name}"

    def compute_sha256(self, data_bytes: bytes) -> str:
        """Calculate SHA-256 checksum of raw binary data."""
        return hashlib.sha256(data_bytes).hexdigest()

    def upload_file(
        self,
        object_key: str,
        data_stream: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
        bucket_name: str = None,
    ) -> bool:
        """Upload a file stream to MinIO."""
        bucket = bucket_name or config.MINIO_DEFAULT_BUCKET
        self.ensure_bucket_exists(bucket)

        self.client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=data_stream,
            length=length,
            content_type=content_type or "application/octet-stream",
        )
        return True

    def get_file_stream(self, object_key: str, bucket_name: str = None):
        """Retrieve a file stream and metadata from MinIO."""
        bucket = bucket_name or config.MINIO_DEFAULT_BUCKET
        try:
            response = self.client.get_object(bucket_name=bucket, object_name=object_key)
            return response
        except S3Error as e:
            if e.code in ("NoSuchKey", "ResourceNotFound"):
                return None
            raise

    def delete_file(self, object_key: str, bucket_name: str = None) -> bool:
        """Delete an object from MinIO."""
        bucket = bucket_name or config.MINIO_DEFAULT_BUCKET
        try:
            self.client.remove_object(bucket_name=bucket, object_name=object_key)
            return True
        except Exception as e:
            print(f"[StorageService] Warning deleting object '{object_key}': {e}")
            return False

storage_service = StorageService()
