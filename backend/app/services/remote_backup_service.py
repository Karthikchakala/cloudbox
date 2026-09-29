import os
import sys
import json
import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import urllib3

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    Minio = None
    S3Error = Exception

try:
    from app.services.audit_logger import log_security_event
except Exception:
    def log_security_event(*args, **kwargs):
        pass

logger = logging.getLogger("cloudbox.remote_backup")

def compute_file_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(64 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()

class RemoteBackupService:
    """
    S3-compatible Remote Backup Replication Service.
    Supports AWS S3, Cloudflare R2, MinIO, and standard S3 providers.
    """

    def __init__(self):
        self.enabled = os.getenv("REMOTE_BACKUP_ENABLED", "false").lower() in ("1", "true", "yes")
        self.endpoint = os.getenv("REMOTE_BACKUP_S3_ENDPOINT", "s3.amazonaws.com").replace("https://", "").replace("http://", "")
        self.bucket = os.getenv("REMOTE_BACKUP_BUCKET", "cloudbox-offsite-backups")
        self.access_key = os.getenv("REMOTE_BACKUP_ACCESS_KEY", "")
        self.secret_key = os.getenv("REMOTE_BACKUP_SECRET_KEY", "")
        self.region = os.getenv("REMOTE_BACKUP_REGION", "us-east-1")
        self.retention_count = int(os.getenv("BACKUP_RETENTION_COUNT", "10"))
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Optional[Minio]:
        if not self.enabled or not self.access_key or not self.secret_key:
            return None
        if self._client is None:
            self._client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                region=self.region,
                secure=True,
            )
        return self._client

    def ensure_remote_bucket(self) -> bool:
        """Ensure the destination remote backup bucket exists."""
        if not self.client:
            return False
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket, location=self.region)
                logger.info(f"Created remote backup bucket: {self.bucket}")
            return True
        except Exception as e:
            logger.error(f"Error checking/creating remote backup bucket '{self.bucket}': {e}")
            return False

    def replicate_bundle(self, bundle_path: str) -> Dict[str, Any]:
        """
        Replicate a local backup bundle to remote S3 storage.
        Verifies remote upload integrity and applies remote retention policy.
        """
        if not os.path.exists(bundle_path):
            return {
                "success": False,
                "error": f"Local backup bundle not found: {bundle_path}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        bundle_filename = os.path.basename(bundle_path)
        file_size = os.path.getsize(bundle_path)
        local_sha256 = compute_file_sha256(bundle_path)

        if not self.enabled:
            logger.info("Remote backup replication is disabled (REMOTE_BACKUP_ENABLED=false). Local backup preserved.")
            return {
                "success": True,
                "status": "LOCAL_ONLY",
                "bundle": bundle_filename,
                "size_bytes": file_size,
                "sha256": local_sha256,
                "message": "Local backup verified. Remote sync disabled.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        if not self.client:
            return {
                "success": False,
                "error": "Remote backup enabled but credentials/endpoint are missing or invalid.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        try:
            self.ensure_remote_bucket()

            # Upload bundle archive
            logger.info(f"Uploading backup bundle '{bundle_filename}' ({file_size} bytes) to remote S3...")
            with open(bundle_path, "rb") as f:
                self.client.put_object(
                    bucket_name=self.bucket,
                    object_name=bundle_filename,
                    data=f,
                    length=file_size,
                    content_type="application/gzip",
                    metadata={"sha256": local_sha256}
                )

            # Upload sidecar checksum if present
            sha_sidecar = bundle_path + ".sha256"
            if os.path.exists(sha_sidecar):
                with open(sha_sidecar, "rb") as sf:
                    self.client.put_object(
                        bucket_name=self.bucket,
                        object_name=bundle_filename + ".sha256",
                        data=sf,
                        length=os.path.getsize(sha_sidecar),
                        content_type="text/plain"
                    )

            # Verify remote object existence and size
            remote_stat = self.client.stat_object(self.bucket, bundle_filename)
            if remote_stat.size != file_size:
                raise RuntimeError(f"Remote size mismatch! Expected {file_size}, got {remote_stat.size}")

            # Prune old remote backups according to retention count
            self.prune_remote_backups()

            log_security_event(
                event_type="DISASTER_RECOVERY",
                action="REMOTE_BACKUP_SYNC",
                status="SUCCESS",
                target_resource_id=bundle_filename,
                details={"bucket": self.bucket, "size_bytes": file_size, "sha256": local_sha256}
            )

            return {
                "success": True,
                "status": "REPLICATED",
                "bundle": bundle_filename,
                "remote_bucket": self.bucket,
                "size_bytes": file_size,
                "sha256": local_sha256,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Remote backup replication failed for '{bundle_filename}': {e}")
            log_security_event(
                event_type="DISASTER_RECOVERY",
                action="REMOTE_BACKUP_SYNC",
                status="FAILED",
                target_resource_id=bundle_filename,
                details={"error": str(e), "local_preserved": True}
            )
            return {
                "success": False,
                "status": "FAILED",
                "error": str(e),
                "local_bundle_preserved": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def prune_remote_backups(self):
        """Prune older remote backups to satisfy retention policy."""
        if not self.client:
            return
        try:
            objects = list(self.client.list_objects(self.bucket, prefix="cloudbox_backup_"))
            tar_objects = [obj for obj in objects if obj.object_name.endswith(".tar.gz")]
            tar_objects.sort(key=lambda x: x.last_modified or datetime.min)

            if len(tar_objects) > self.retention_count:
                to_delete = tar_objects[:-self.retention_count]
                for obj in to_delete:
                    self.client.remove_object(self.bucket, obj.object_name)
                    # Also remove .sha256 sidecar
                    try:
                        self.client.remove_object(self.bucket, obj.object_name + ".sha256")
                    except Exception:
                        pass
                    logger.info(f"Pruned old remote backup: {obj.object_name}")
        except Exception as e:
            logger.warning(f"Warning during remote backup pruning: {e}")

remote_backup_service = RemoteBackupService()
