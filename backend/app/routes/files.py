import io
import math
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g, Response, stream_with_context
from werkzeug.utils import secure_filename
from app.config import config
from app.extensions import db
from app.models.file import File
from app.models.file_version import FileVersion
from app.services.storage_service import storage_service
from app.services.security import jwt_required
from app.services.cache_service import cache_service
from app.services.audit_logger import log_security_event

files_bp = Blueprint("files", __name__, url_prefix="/api/files")

@files_bp.route("", methods=["POST"])
@jwt_required
def upload_file():
    """
    Upload a new file.
    Validates payload, uploads object to MinIO, creates File and Version 1 records,
    and enqueues background processing for thumbnails/metadata.
    """
    if "file" not in request.files:
        return jsonify({
            "error": "No file part in multipart request. Use form-data field 'file'.",
            "code": "MISSING_FILE_FIELD"
        }), 400

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename or uploaded_file.filename.strip() == "":
        return jsonify({
            "error": "No file selected for upload.",
            "code": "NO_FILE_SELECTED"
        }), 400

    raw_filename = uploaded_file.filename
    clean_filename = secure_filename(raw_filename) or "unnamed_file"

    try:
        file_bytes = uploaded_file.read()
        file_size = len(file_bytes)

        if file_size == 0:
            return jsonify({
                "error": "Empty files cannot be uploaded.",
                "code": "EMPTY_FILE"
            }), 400

        if file_size > config.MAX_CONTENT_LENGTH:
            return jsonify({
                "error": f"File exceeds maximum permitted size of {config.MAX_CONTENT_LENGTH // (1024 * 1024)} MB.",
                "code": "FILE_TOO_LARGE"
            }), 413

        content_type = uploaded_file.content_type or "application/octet-stream"
        checksum = storage_service.compute_sha256(file_bytes)
        object_key = storage_service.generate_object_key(str(g.current_user.id), clean_filename)

        # Upload binary stream to MinIO
        stream = io.BytesIO(file_bytes)
        storage_service.upload_file(
            object_key=object_key,
            data_stream=stream,
            length=file_size,
            content_type=content_type,
        )

    except Exception:
        return jsonify({
            "error": "Failed to upload file to object storage.",
            "code": "STORAGE_UPLOAD_ERROR"
        }), 500

    # Save File and FileVersion (v1) in database transaction
    try:
        file_record = File(
            owner_id=g.current_user.id,
            original_filename=clean_filename,
            object_key=object_key,
            content_type=content_type,
            size_bytes=file_size,
            checksum_sha256=checksum,
            deleted_at=None,
            processing_status="pending",
        )
        db.session.add(file_record)
        db.session.flush()

        version_record = FileVersion(
            file_id=file_record.id,
            version_number=1,
            object_key=object_key,
            original_filename=clean_filename,
            content_type=content_type,
            size_bytes=file_size,
            checksum_sha256=checksum,
            created_by=g.current_user.id,
        )
        db.session.add(version_record)
        db.session.commit()

        # Invalidate cached file listings for user
        cache_service.invalidate_user_cache(str(g.current_user.id))

        log_security_event(
            event_type="FILE",
            action="FILE_UPLOAD",
            status="SUCCESS",
            user_id=str(g.current_user.id),
            target_resource_id=str(file_record.id),
            details={"filename": clean_filename, "size_bytes": file_size}
        )

        # Enqueue asynchronous background processing
        try:
            from app.tasks.file_tasks import process_file_pipeline
            process_file_pipeline.delay(str(file_record.id))
        except Exception:
            try:
                from app.tasks.file_tasks import process_file_pipeline
                process_file_pipeline(str(file_record.id))
            except Exception:
                pass

        return jsonify({
            "message": "File uploaded successfully.",
            "file": file_record.to_dict()
        }), 201

    except Exception:
        db.session.rollback()
        storage_service.delete_file(object_key)
        return jsonify({
            "error": "Database error while persisting file metadata.",
            "code": "METADATA_SAVE_ERROR"
        }), 500


@files_bp.route("", methods=["GET"])
@jwt_required
def list_files():
    """
    List active (non-deleted) files owned by authenticated user with Redis caching, search, and pagination.
    """
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
        search = request.args.get("search", "").strip()

        cache_key = f"user:{g.current_user.id}:files:p{page}:l{per_page}:s{search}"
        cached = cache_service.get_json(cache_key)
        if cached is not None:
            return jsonify(cached), 200

        # Query only active files (deleted_at IS NULL)
        query = File.query.filter_by(owner_id=g.current_user.id).filter(File.deleted_at.is_(None))

        if search:
            query = query.filter(File.original_filename.ilike(f"%{search}%"))

        total = query.count()
        total_pages = max(1, math.ceil(total / per_page))

        files = (
            query.order_by(File.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        response_payload = {
            "files": [f.to_dict() for f in files],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            }
        }

        # Cache in Redis with 3-minute TTL
        cache_service.set_json(cache_key, response_payload, ttl_seconds=180)

        return jsonify(response_payload), 200

    except ValueError:
        return jsonify({
            "error": "Invalid pagination parameters.",
            "code": "INVALID_PARAMS"
        }), 400
    except Exception:
        return jsonify({
            "error": "Failed to retrieve file list.",
            "code": "LIST_FILES_ERROR"
        }), 500


@files_bp.route("/<uuid:file_id>", methods=["GET"])
@jwt_required
def get_file_metadata(file_id):
    """Retrieve metadata for an active file with caching."""
    cache_key = f"file:{file_id}:meta"
    cached = cache_service.get_json(cache_key)
    if cached is not None:
        return jsonify({"file": cached}), 200

    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    data = file_record.to_dict()
    cache_service.set_json(cache_key, data, ttl_seconds=300)
    return jsonify({"file": data}), 200


@files_bp.route("/<uuid:file_id>", methods=["PATCH"])
@jwt_required
def update_file_metadata(file_id):
    """Update file metadata such as original_filename."""
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    data = request.get_json(silent=True) or {}
    new_name = data.get("name") or data.get("original_filename") or data.get("filename")
    if not new_name:
        return jsonify({
            "error": "No valid update fields provided. Specify 'name'.",
            "code": "INVALID_PARAMS"
        }), 400

    clean_name = secure_filename(str(new_name).strip())
    if not clean_name:
        return jsonify({
            "error": "Invalid filename provided.",
            "code": "INVALID_FILENAME"
        }), 400

    file_record.original_filename = clean_name
    file_record.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    cache_service.invalidate_user_cache(str(g.current_user.id))
    cache_service.invalidate_file_cache(str(file_id))

    log_security_event(
        event_type="FILE",
        action="FILE_RENAME",
        status="SUCCESS",
        user_id=str(g.current_user.id),
        target_resource_id=str(file_id),
        details={"new_filename": clean_name}
    )

    return jsonify({
        "message": "File updated successfully.",
        "file": file_record.to_dict()
    }), 200


@files_bp.route("/<uuid:file_id>/processing-status", methods=["GET"])
@jwt_required
def get_processing_status(file_id):
    """Retrieve background processing status and extracted metadata for a file."""
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    return jsonify({
        "file_id": str(file_record.id),
        "status": file_record.processing_status or "completed",
        "has_thumbnail": bool(file_record.thumbnail_object_key),
        "extracted_metadata": file_record.extracted_metadata or {},
        "error_message": file_record.error_message,
        "updated_at": file_record.updated_at.isoformat() if file_record.updated_at else None
    }), 200


@files_bp.route("/<uuid:file_id>/thumbnail", methods=["GET"])
@jwt_required
def get_file_thumbnail(file_id):
    """Stream generated image thumbnail from MinIO."""
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record or not file_record.thumbnail_object_key:
        return jsonify({
            "error": "Thumbnail not found.",
            "code": "THUMBNAIL_NOT_FOUND"
        }), 404

    minio_response = storage_service.get_file_stream(file_record.thumbnail_object_key)
    if not minio_response:
        return jsonify({"error": "Thumbnail storage object missing.", "code": "OBJECT_NOT_FOUND"}), 404

    def generate():
        try:
            for chunk in minio_response.stream(32 * 1024):
                yield chunk
        finally:
            minio_response.close()
            minio_response.release_conn()

    headers = {
        "Content-Type": "image/jpeg",
        "Cache-Control": "public, max-age=86400",
    }
    return Response(stream_with_context(generate()), headers=headers)


@files_bp.route("/<uuid:file_id>/preview", methods=["GET"])
@jwt_required
def preview_file(file_id):
    """Stream file content for inline browser preview (images, pdfs, text)."""
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    minio_response = storage_service.get_file_stream(file_record.object_key)
    if not minio_response:
        return jsonify({"error": "Storage object missing.", "code": "OBJECT_NOT_FOUND"}), 404

    def generate():
        try:
            for chunk in minio_response.stream(32 * 1024):
                yield chunk
        finally:
            minio_response.close()
            minio_response.release_conn()

    safe_name = file_record.original_filename.replace('"', '\\"')
    headers = {
        "Content-Disposition": f'inline; filename="{safe_name}"',
        "Content-Type": file_record.content_type,
        "Content-Length": str(file_record.size_bytes),
        "Cache-Control": "private, max-age=3600",
    }
    return Response(stream_with_context(generate()), headers=headers)


@files_bp.route("/<uuid:file_id>/download", methods=["GET"])
@jwt_required
def download_file(file_id):
    """Stream active file contents from MinIO storage for download."""
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    minio_response = storage_service.get_file_stream(file_record.object_key)
    if not minio_response:
        return jsonify({
            "error": "Storage object not found for this file record.",
            "code": "OBJECT_NOT_FOUND"
        }), 404

    log_security_event(
        event_type="FILE",
        action="FILE_DOWNLOAD",
        status="SUCCESS",
        user_id=str(g.current_user.id),
        target_resource_id=str(file_record.id),
        details={"filename": file_record.original_filename, "size_bytes": file_record.size_bytes}
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


@files_bp.route("/<uuid:file_id>", methods=["DELETE"])
@jwt_required
def soft_delete_file(file_id):
    """
    Soft-delete a file by moving it to the Recycle Bin.
    Does NOT remove MinIO objects or version history.
    """
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    try:
        file_record.deleted_at = datetime.now(timezone.utc)
        db.session.commit()

        # Invalidate cache for user and file
        cache_service.invalidate_user_cache(str(g.current_user.id))
        cache_service.invalidate_file_cache(str(file_id))

        log_security_event(
            event_type="FILE",
            action="FILE_SOFT_DELETE",
            status="SUCCESS",
            user_id=str(g.current_user.id),
            target_resource_id=str(file_id),
            details={"filename": file_record.original_filename}
        )

        return jsonify({
            "message": "File moved to recycle bin.",
            "id": str(file_id)
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Failed to move file to recycle bin.",
            "code": "SOFT_DELETE_ERROR"
        }), 500
