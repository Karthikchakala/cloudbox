import io
import math
import uuid
import hashlib
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.file import File
from app.models.file_version import FileVersion
from app.models.upload_session import UploadSession
from app.services.security import jwt_required
from app.services.storage_service import storage_service
from app.services.cache_service import cache_service
from app.services.audit_logger import log_security_event

uploads_bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")

# Support large files up to 500 MB via chunked upload
MAX_CHUNKED_FILE_SIZE = 500 * 1024 * 1024
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024 # 5 MB per chunk

@uploads_bp.route("/initiate", methods=["POST"])
@jwt_required
def initiate_upload():
    """Initiate a new resumable chunked upload session."""
    user = g.current_user
    data = request.get_json() or {}

    raw_filename = data.get("filename", "").strip()
    if not raw_filename:
        return jsonify({"error": "Filename is required.", "code": "INVALID_FILENAME"}), 400

    filename = secure_filename(raw_filename) or "unnamed_file"
    file_size = data.get("file_size")
    if not isinstance(file_size, int) or file_size <= 0:
        return jsonify({"error": "Valid positive file_size in bytes is required.", "code": "INVALID_FILE_SIZE"}), 400

    if file_size > MAX_CHUNKED_FILE_SIZE:
        return jsonify({
            "error": f"File exceeds maximum chunked upload limit of {MAX_CHUNKED_FILE_SIZE // (1024*1024)} MB.",
            "code": "FILE_TOO_LARGE"
        }), 413

    chunk_size = data.get("chunk_size", DEFAULT_CHUNK_SIZE)
    if not isinstance(chunk_size, int) or chunk_size <= 0:
        chunk_size = DEFAULT_CHUNK_SIZE

    total_chunks = max(1, math.ceil(file_size / chunk_size))
    content_type = data.get("content_type", "application/octet-stream")

    # Optional target file ID if uploading a new version to an existing file
    target_file_id_str = data.get("target_file_id")
    target_file_id = None
    if target_file_id_str:
        try:
            target_uuid = uuid.UUID(str(target_file_id_str))
            target_file = db.session.get(File, target_uuid)
            if not target_file or target_file.owner_id != user.id or target_file.deleted_at is not None:
                return jsonify({"error": "Target file not found or inaccessible.", "code": "TARGET_NOT_FOUND"}), 404
            target_file_id = target_file.id
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid target_file_id UUID.", "code": "INVALID_UUID"}), 400

    session = UploadSession(
        user_id=user.id,
        target_file_id=target_file_id,
        filename=filename,
        file_size=file_size,
        content_type=content_type,
        total_chunks=total_chunks,
        chunk_size=chunk_size,
        uploaded_chunks=[],
        status="initiated"
    )

    db.session.add(session)
    db.session.commit()

    log_security_event(
        event_type="UPLOAD",
        action="CHUNKED_UPLOAD_INIT",
        status="SUCCESS",
        user_id=str(user.id),
        target_resource_id=str(session.id),
        details={"filename": filename, "file_size": file_size, "total_chunks": total_chunks}
    )

    return jsonify({
        "status": "initiated",
        "upload_id": str(session.id),
        "session": session.to_dict(),
    }), 201

@uploads_bp.route("/<upload_id>/chunks/<int:chunk_number>", methods=["PUT"])
@jwt_required
def upload_chunk(upload_id: str, chunk_number: int):
    """Upload a single chunk binary for an active upload session."""
    user = g.current_user

    try:
        session_uuid = uuid.UUID(upload_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid upload_id UUID.", "code": "INVALID_UUID"}), 400

    session = db.session.get(UploadSession, session_uuid)
    if not session or session.user_id != user.id:
        return jsonify({"error": "Upload session not found.", "code": "NOT_FOUND"}), 404

    if session.status in ("completed", "aborted") or session.is_expired:
        return jsonify({"error": f"Upload session is {session.status} or expired.", "code": "SESSION_CLOSED"}), 400

    if chunk_number < 1 or chunk_number > session.total_chunks:
        return jsonify({"error": f"chunk_number must be between 1 and {session.total_chunks}.", "code": "INVALID_CHUNK_INDEX"}), 400

    # Retrieve chunk bytes
    if "chunk" in request.files:
        chunk_file = request.files["chunk"]
        chunk_data = chunk_file.read()
    else:
        chunk_data = request.get_data()

    if not chunk_data:
        return jsonify({"error": "Empty chunk payload received.", "code": "EMPTY_CHUNK"}), 400

    # Store chunk part in MinIO
    part_key = f"chunks/{session.id}/part_{chunk_number}"
    storage_service.upload_file(
        object_key=part_key,
        data_stream=io.BytesIO(chunk_data),
        length=len(chunk_data),
        content_type="application/octet-stream"
    )

    # Record uploaded chunk index idempotently
    uploaded_set = set(session.uploaded_chunks or [])
    uploaded_set.add(chunk_number)
    session.uploaded_chunks = sorted(list(uploaded_set))
    session.status = "uploading"
    db.session.commit()

    return jsonify({
        "status": "chunk_received",
        "chunk_number": chunk_number,
        "uploaded_chunks_count": len(session.uploaded_chunks),
        "total_chunks": session.total_chunks,
        "progress_percent": round(len(session.uploaded_chunks) / session.total_chunks * 100, 1)
    }), 200

@uploads_bp.route("/<upload_id>", methods=["GET"])
@jwt_required
def get_upload_status(upload_id: str):
    """Inspect status and received chunks of an upload session."""
    user = g.current_user
    try:
        session_uuid = uuid.UUID(upload_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid upload_id UUID.", "code": "INVALID_UUID"}), 400

    session = db.session.get(UploadSession, session_uuid)
    if not session or session.user_id != user.id:
        return jsonify({"error": "Upload session not found.", "code": "NOT_FOUND"}), 404

    return jsonify({"session": session.to_dict()}), 200

@uploads_bp.route("/<upload_id>/complete", methods=["POST"])
@jwt_required
def complete_upload(upload_id: str):
    """Assemble all chunks, verify integrity, create File / Version records, and trigger background task."""
    user = g.current_user
    try:
        session_uuid = uuid.UUID(upload_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid upload_id UUID.", "code": "INVALID_UUID"}), 400

    session = db.session.get(UploadSession, session_uuid)
    if not session or session.user_id != user.id:
        return jsonify({"error": "Upload session not found.", "code": "NOT_FOUND"}), 404

    if session.status == "completed":
        return jsonify({"error": "Upload session has already been completed.", "code": "ALREADY_COMPLETED"}), 400

    uploaded_set = set(session.uploaded_chunks or [])
    expected_set = set(range(1, session.total_chunks + 1))
    missing_chunks = sorted(list(expected_set - uploaded_set))

    if missing_chunks:
        return jsonify({
            "error": "Cannot complete upload. Missing chunks.",
            "code": "INCOMPLETE_CHUNKS",
            "missing_chunks": missing_chunks
        }), 400

    # Assemble all chunk parts in sequential order
    final_object_key = storage_service.generate_object_key(str(user.id), session.filename)
    hasher = hashlib.sha256()
    assembled_bytes = bytearray()

    part_keys = []
    for chunk_num in range(1, session.total_chunks + 1):
        part_key = f"chunks/{session.id}/part_{chunk_num}"
        part_keys.append(part_key)
        stream_resp = storage_service.get_file_stream(part_key)
        if not stream_resp:
            return jsonify({"error": f"Failed reading chunk part {chunk_num}.", "code": "STORAGE_CHUNK_ERROR"}), 500
        part_data = b"".join(stream_resp.stream(32 * 1024))
        hasher.update(part_data)
        assembled_bytes.extend(part_data)

    checksum = hasher.hexdigest()
    total_bytes = len(assembled_bytes)

    # Upload assembled object to MinIO
    storage_service.upload_file(
        object_key=final_object_key,
        data_stream=io.BytesIO(assembled_bytes),
        length=total_bytes,
        content_type=session.content_type
    )

    # Clean up temporary chunk parts
    for pk in part_keys:
        try:
            storage_service.delete_file(pk)
        except Exception:
            pass

    # Create / Update File records
    target_file = None
    if session.target_file_id:
        target_file = db.session.get(File, session.target_file_id)

    if target_file and target_file.owner_id == user.id:
        # Creating a new version on existing file
        current_max_v = (
            db.session.query(db.func.coalesce(db.func.max(FileVersion.version_number), 1))
            .filter_by(file_id=target_file.id)
            .scalar()
        )
        new_v_number = current_max_v + 1

        new_version = FileVersion(
            file_id=target_file.id,
            version_number=new_v_number,
            object_key=final_object_key,
            original_filename=session.filename,
            content_type=session.content_type,
            size_bytes=total_bytes,
            checksum_sha256=checksum,
            created_by=user.id
        )
        db.session.add(new_version)

        target_file.original_filename = session.filename
        target_file.object_key = final_object_key
        target_file.content_type = session.content_type
        target_file.size_bytes = total_bytes
        target_file.checksum_sha256 = checksum
        target_file.processing_status = "pending"
        final_file = target_file
    else:
        # Create new logical file + Version 1
        new_file = File(
            owner_id=user.id,
            original_filename=session.filename,
            object_key=final_object_key,
            content_type=session.content_type,
            size_bytes=total_bytes,
            checksum_sha256=checksum,
            processing_status="pending"
        )
        db.session.add(new_file)
        db.session.flush()

        v1 = FileVersion(
            file_id=new_file.id,
            version_number=1,
            object_key=final_object_key,
            original_filename=session.filename,
            content_type=session.content_type,
            size_bytes=total_bytes,
            checksum_sha256=checksum,
            created_by=user.id
        )
        db.session.add(v1)
        final_file = new_file

    session.status = "completed"
    session.checksum_sha256 = checksum
    db.session.commit()

    log_security_event(
        event_type="UPLOAD",
        action="CHUNKED_UPLOAD_COMPLETE",
        status="SUCCESS",
        user_id=str(user.id),
        target_resource_id=str(final_file.id),
        details={"filename": session.filename, "size_bytes": total_bytes}
    )

    # Trigger asynchronous background processing pipeline
    try:
        from app.tasks.file_tasks import process_file_pipeline
        process_file_pipeline.delay(str(final_file.id))
    except Exception:
        # If Celery worker/broker isn't active, run in-process gracefully
        try:
            from app.tasks.file_tasks import process_file_pipeline
            process_file_pipeline(str(final_file.id))
        except Exception:
            pass

    # Invalidate Redis cache
    cache_service.invalidate_user_cache(str(user.id))

    return jsonify({
        "status": "completed",
        "file": final_file.to_dict(),
        "upload_id": str(session.id)
    }), 201

@uploads_bp.route("/<upload_id>", methods=["DELETE"])
@jwt_required
def cancel_upload(upload_id: str):
    """Abort an upload session and clean up temporary parts."""
    user = g.current_user
    try:
        session_uuid = uuid.UUID(upload_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid upload_id UUID.", "code": "INVALID_UUID"}), 400

    session = db.session.get(UploadSession, session_uuid)
    if not session or session.user_id != user.id:
        return jsonify({"error": "Upload session not found.", "code": "NOT_FOUND"}), 404

    # Remove temporary chunk parts
    for chunk_num in session.uploaded_chunks or []:
        try:
            storage_service.delete_file(f"chunks/{session.id}/part_{chunk_num}")
        except Exception:
            pass

    session.status = "aborted"
    db.session.commit()

    log_security_event(
        event_type="UPLOAD",
        action="CHUNKED_UPLOAD_CANCEL",
        status="SUCCESS",
        user_id=str(user.id),
        target_resource_id=str(session.id),
        details={"filename": session.filename}
    )

    return jsonify({"status": "aborted", "upload_id": str(session.id)}), 200
