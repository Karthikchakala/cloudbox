import hashlib
import secrets
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g, Response, stream_with_context
from app.extensions import db
from app.models.file import File
from app.models.share_link import ShareLink
from app.services.storage_service import storage_service
from app.services.security import jwt_required
from app.services.audit_logger import log_security_event

shares_bp = Blueprint("shares", __name__)

def hash_token(token: str) -> str:
    """Compute SHA-256 hash of sharing token."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# Authenticated Share Management Endpoints (Owner Only)
# ---------------------------------------------------------------------------

@shares_bp.route("/api/files/<uuid:file_id>/shares", methods=["POST"])
@jwt_required
def create_share_link(file_id):
    """
    Create a new sharing link for a file.
    Generates a cryptographically random token, hashes it for storage,
    and returns the raw link once.
    """
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    data = request.get_json(silent=True) or {}
    permission = data.get("permission", "download")
    raw_expires = data.get("expires_at")
    raw_password = data.get("password")
    max_downloads = data.get("max_downloads")

    expires_at = None
    if raw_expires:
        try:
            # Parse ISO string
            expires_at = datetime.fromisoformat(raw_expires.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return jsonify({
                "error": "Invalid expires_at format. Use ISO 8601 string.",
                "code": "INVALID_EXPIRATION"
            }), 400

    if max_downloads is not None:
        try:
            max_downloads = int(max_downloads)
            if max_downloads <= 0:
                max_downloads = None
        except (ValueError, TypeError):
            max_downloads = None

    # Generate cryptographically secure token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)

    try:
        share = ShareLink(
            file_id=file_id,
            created_by=g.current_user.id,
            token_hash=token_hash,
            permission=permission,
            expires_at=expires_at,
            max_downloads=max_downloads,
            download_count=0,
            revoked_at=None,
        )
        if raw_password and len(str(raw_password).strip()) > 0:
            share.set_password(str(raw_password).strip())

        db.session.add(share)
        db.session.commit()

        log_security_event(
            event_type="SHARE",
            action="SHARE_CREATE",
            status="SUCCESS",
            user_id=str(g.current_user.id),
            target_resource_id=str(share.id),
            details={"file_id": str(file_id), "permission": permission, "has_password": bool(raw_password)}
        )

        return jsonify({
            "message": "Sharing link created successfully.",
            "share": share.to_dict(),
            "token": raw_token,
            "share_url": f"/shared/{raw_token}",
        }), 201

    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Failed to create share link.",
            "code": "SHARE_CREATE_ERROR"
        }), 500


@shares_bp.route("/api/files/<uuid:file_id>/shares", methods=["GET"])
@jwt_required
def list_share_links(file_id):
    """List all active and historical share links for a file owned by the user."""
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    shares = (
        ShareLink.query.filter_by(file_id=file_id, created_by=g.current_user.id)
        .order_by(ShareLink.created_at.desc())
        .all()
    )

    return jsonify({
        "file_id": str(file_id),
        "shares": [s.to_dict() for s in shares]
    }), 200


@shares_bp.route("/api/shares/<uuid:share_id>", methods=["DELETE"])
@jwt_required
def revoke_share_link(share_id):
    """Revoke an active sharing link immediately."""
    share = ShareLink.query.filter_by(id=share_id, created_by=g.current_user.id).first()
    if not share:
        return jsonify({
            "error": "Share link not found or access denied.",
            "code": "SHARE_NOT_FOUND"
        }), 404

    try:
        share.revoked_at = datetime.now(timezone.utc)
        db.session.commit()

        log_security_event(
            event_type="SHARE",
            action="SHARE_REVOKE",
            status="SUCCESS",
            user_id=str(g.current_user.id),
            target_resource_id=str(share_id),
            details={"file_id": str(share.file_id)}
        )

        return jsonify({
            "message": "Share link revoked successfully.",
            "id": str(share_id)
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Failed to revoke share link.",
            "code": "SHARE_REVOKE_ERROR"
        }), 500


# ---------------------------------------------------------------------------
# Public Sharing Endpoints (Recipients)
# ---------------------------------------------------------------------------

@shares_bp.route("/api/shared/<string:token>", methods=["GET"])
def access_shared_file(token):
    """
    Access or download a shared file via public sharing token.
    Validates token hash, expiration, revocation, download limits, and password.
    """
    token_hash = hash_token(token)
    share = ShareLink.query.filter_by(token_hash=token_hash).first()

    if not share:
        return jsonify({
            "error": "Invalid or expired sharing link.",
            "code": "INVALID_SHARE_TOKEN"
        }), 404

    # Check if link is active
    if not share.is_active:
        return jsonify({
            "error": "This sharing link has expired, been revoked, or reached its download limit.",
            "code": "SHARE_INACTIVE"
        }), 410

    # Ensure associated file exists and is NOT in recycle bin
    file_record = File.query.filter_by(id=share.file_id).first()
    if not file_record or file_record.deleted_at is not None:
        return jsonify({
            "error": "The shared file is no longer available.",
            "code": "FILE_UNAVAILABLE"
        }), 404

    # Password check
    supplied_password = request.headers.get("X-Share-Password") or request.args.get("password")
    if share.password_hash:
        if not supplied_password or not share.check_password(supplied_password):
            return jsonify({
                "requires_password": True,
                "is_password_protected": True,
                "original_filename": file_record.original_filename,
                "size_bytes": file_record.size_bytes,
                "content_type": file_record.content_type,
            }), 200

    # Check if this is a download action
    is_download = request.args.get("download", "false").lower() in ("true", "1", "yes")

    if not is_download:
        # Return safe public metadata
        return jsonify({
            "id": str(file_record.id),
            "original_filename": file_record.original_filename,
            "content_type": file_record.content_type,
            "size_bytes": file_record.size_bytes,
            "checksum_sha256": file_record.checksum_sha256,
            "permission": share.permission,
            "created_at": file_record.created_at.isoformat(),
            "requires_password": False,
        }), 200

    # Stream file binary from MinIO
    minio_response = storage_service.get_file_stream(file_record.object_key)
    if not minio_response:
        return jsonify({
            "error": "Object data not found.",
            "code": "OBJECT_NOT_FOUND"
        }), 404

    # Increment download count
    try:
        share.download_count += 1
        db.session.commit()
    except Exception:
        db.session.rollback()

    log_security_event(
        event_type="SHARE",
        action="SHARE_DOWNLOAD",
        status="SUCCESS",
        user_id="public_recipient",
        target_resource_id=str(share.id),
        details={"file_id": str(file_record.id), "filename": file_record.original_filename}
    )

    def generate():
        try:
            for chunk in minio_response.stream(32 * 1024):
                yield chunk
        finally:
            minio_response.close()
            minio_response.release_conn()

    safe_name = file_record.original_filename.replace('"', '\\"')
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_name}"',
        "Content-Type": file_record.content_type,
        "Content-Length": str(file_record.size_bytes),
        "Cache-Control": "no-cache",
    }

    return Response(stream_with_context(generate()), headers=headers)


@shares_bp.route("/api/shared/<string:token>/verify", methods=["POST"])
def verify_shared_password(token):
    """Verify password for a password-protected share link."""
    token_hash = hash_token(token)
    share = ShareLink.query.filter_by(token_hash=token_hash).first()

    if not share or not share.is_active:
        return jsonify({
            "error": "Invalid or inactive sharing link.",
            "code": "SHARE_INACTIVE"
        }), 404

    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    if not share.password_hash:
        return jsonify({"valid": True}), 200

    if not password or not share.check_password(password):
        log_security_event(
            event_type="SHARE",
            action="SHARE_PASSWORD_VERIFY",
            status="FAILED",
            user_id="public_recipient",
            target_resource_id=str(share.id)
        )
        return jsonify({
            "error": "Incorrect password for this shared file.",
            "code": "INVALID_PASSWORD"
        }), 401

    log_security_event(
        event_type="SHARE",
        action="SHARE_PASSWORD_VERIFY",
        status="SUCCESS",
        user_id="public_recipient",
        target_resource_id=str(share.id)
    )

    return jsonify({"valid": True}), 200
