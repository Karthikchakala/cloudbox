import io
from flask import Blueprint, request, jsonify, g, Response, stream_with_context
from werkzeug.utils import secure_filename
from app.config import config
from app.extensions import db
from app.models.file import File
from app.models.file_version import FileVersion
from app.services.storage_service import storage_service
from app.services.security import jwt_required
from app.services.cache_service import cache_service

versions_bp = Blueprint("versions", __name__, url_prefix="/api/files")

@versions_bp.route("/<uuid:file_id>/versions", methods=["GET"])
@jwt_required
def list_versions(file_id):
    """List all versions for a file owned by the authenticated user."""
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    versions = (
        FileVersion.query.filter_by(file_id=file_id)
        .order_by(FileVersion.version_number.desc())
        .all()
    )

    if not versions:
        # Auto-create Version 1 entry if legacy file has no version records
        v1 = FileVersion(
            file_id=file_record.id,
            version_number=1,
            object_key=file_record.object_key,
            original_filename=file_record.original_filename,
            content_type=file_record.content_type,
            size_bytes=file_record.size_bytes,
            checksum_sha256=file_record.checksum_sha256,
            created_by=g.current_user.id,
            created_at=file_record.created_at,
        )
        db.session.add(v1)
        db.session.commit()
        versions = [v1]

    max_version = versions[0].version_number if versions else 1

    return jsonify({
        "file_id": str(file_id),
        "versions": [v.to_dict(is_current=(v.version_number == max_version)) for v in versions]
    }), 200


@versions_bp.route("/<uuid:file_id>/versions", methods=["POST"])
@jwt_required
def upload_new_version(file_id):
    """
    Upload a new version for an existing file.
    Creates next sequential version, uploads to MinIO, and updates File pointer.
    """
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

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
    clean_filename = secure_filename(raw_filename) or file_record.original_filename

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

        content_type = uploaded_file.content_type or file_record.content_type
        checksum = storage_service.compute_sha256(file_bytes)
        object_key = storage_service.generate_object_key(str(g.current_user.id), clean_filename)

        stream = io.BytesIO(file_bytes)
        storage_service.upload_file(
            object_key=object_key,
            data_stream=stream,
            length=file_size,
            content_type=content_type,
        )

    except Exception:
        return jsonify({
            "error": "Failed to upload new version to storage.",
            "code": "STORAGE_UPLOAD_ERROR"
        }), 500

    try:
        existing_versions = (
            FileVersion.query.filter_by(file_id=file_id)
            .order_by(FileVersion.version_number.desc())
            .all()
        )
        if not existing_versions:
            # Auto-create Version 1 from current file record
            v1 = FileVersion(
                file_id=file_record.id,
                version_number=1,
                object_key=file_record.object_key,
                original_filename=file_record.original_filename,
                content_type=file_record.content_type,
                size_bytes=file_record.size_bytes,
                checksum_sha256=file_record.checksum_sha256,
                created_by=g.current_user.id,
                created_at=file_record.created_at,
            )
            db.session.add(v1)
            db.session.flush()
            next_version_num = 2
        else:
            next_version_num = existing_versions[0].version_number + 1

        new_version = FileVersion(
            file_id=file_id,
            version_number=next_version_num,
            object_key=object_key,
            original_filename=clean_filename,
            content_type=content_type,
            size_bytes=file_size,
            checksum_sha256=checksum,
            created_by=g.current_user.id,
        )
        db.session.add(new_version)

        file_record.original_filename = clean_filename
        file_record.object_key = object_key
        file_record.content_type = content_type
        file_record.size_bytes = file_size
        file_record.checksum_sha256 = checksum
        db.session.commit()

        # Invalidate cached file listings for user
        cache_service.invalidate_user_cache(str(g.current_user.id))

        return jsonify({
            "message": f"Version {next_version_num} uploaded successfully.",
            "version": new_version.to_dict(is_current=True),
            "file": file_record.to_dict(),
        }), 201

    except Exception:
        db.session.rollback()
        storage_service.delete_file(object_key)
        return jsonify({
            "error": "Database error while persisting version metadata.",
            "code": "VERSION_SAVE_ERROR"
        }), 500


@versions_bp.route("/<uuid:file_id>/versions/<uuid:version_id>/download", methods=["GET"])
@jwt_required
def download_specific_version(file_id, version_id):
    """Download the binary of a specific historical version."""
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    version_record = FileVersion.query.filter_by(id=version_id, file_id=file_id).first()
    if not version_record:
        return jsonify({
            "error": "Version not found.",
            "code": "VERSION_NOT_FOUND"
        }), 404

    minio_response = storage_service.get_file_stream(version_record.object_key)
    if not minio_response:
        return jsonify({
            "error": "Object data not found in storage.",
            "code": "OBJECT_NOT_FOUND"
        }), 404

    def generate():
        try:
            for chunk in minio_response.stream(32 * 1024):
                yield chunk
        finally:
            minio_response.close()
            minio_response.release_conn()

    safe_name = version_record.original_filename.replace('"', '\\"')
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_name}"',
        "Content-Type": version_record.content_type,
        "Content-Length": str(version_record.size_bytes),
        "Cache-Control": "no-cache",
    }

    return Response(stream_with_context(generate()), headers=headers)


@versions_bp.route("/<uuid:file_id>/versions/<uuid:version_id>/restore", methods=["POST"])
@jwt_required
def restore_version(file_id, version_id):
    """
    Restore an earlier version by creating a new version pointing to that content.
    Preserves version history.
    """
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    target_version = FileVersion.query.filter_by(id=version_id, file_id=file_id).first()
    if not target_version:
        return jsonify({
            "error": "Target version not found.",
            "code": "VERSION_NOT_FOUND"
        }), 404

    # Retrieve data stream of target version
    target_stream = storage_service.get_file_stream(target_version.object_key)
    if not target_stream:
        return jsonify({
            "error": "Target version content not found in storage.",
            "code": "OBJECT_NOT_FOUND"
        }), 404

    try:
        content_bytes = b"".join(list(target_stream.stream(32 * 1024)))
        new_object_key = storage_service.generate_object_key(str(g.current_user.id), target_version.original_filename)

        stream = io.BytesIO(content_bytes)
        storage_service.upload_file(
            object_key=new_object_key,
            data_stream=stream,
            length=len(content_bytes),
            content_type=target_version.content_type,
        )
    except Exception:
        return jsonify({
            "error": "Failed to copy version object in storage.",
            "code": "STORAGE_RESTORE_ERROR"
        }), 500

    latest_version = (
        FileVersion.query.filter_by(file_id=file_id)
        .order_by(FileVersion.version_number.desc())
        .first()
    )
    next_version_num = (latest_version.version_number + 1) if latest_version else 1

    try:
        new_version = FileVersion(
            file_id=file_id,
            version_number=next_version_num,
            object_key=new_object_key,
            original_filename=target_version.original_filename,
            content_type=target_version.content_type,
            size_bytes=target_version.size_bytes,
            checksum_sha256=target_version.checksum_sha256,
            created_by=g.current_user.id,
        )
        db.session.add(new_version)

        file_record.original_filename = target_version.original_filename
        file_record.object_key = new_object_key
        file_record.content_type = target_version.content_type
        file_record.size_bytes = target_version.size_bytes
        file_record.checksum_sha256 = target_version.checksum_sha256
        db.session.commit()

        # Invalidate cached file listings for user
        cache_service.invalidate_user_cache(str(g.current_user.id))

        return jsonify({
            "message": f"Successfully restored version {target_version.version_number} as version {next_version_num}.",
            "version": new_version.to_dict(is_current=True),
            "file": file_record.to_dict(),
        }), 200

    except Exception:
        db.session.rollback()
        storage_service.delete_file(new_object_key)
        return jsonify({
            "error": "Failed to restore version.",
            "code": "RESTORE_VERSION_ERROR"
        }), 500


@versions_bp.route("/<uuid:file_id>/versions/<uuid:version_id>", methods=["DELETE"])
@jwt_required
def delete_version(file_id, version_id):
    """
    Delete an old version.
    Preserves at least one valid version for an active file.
    """
    file_record = File.query.filter_by(id=file_id, owner_id=g.current_user.id).filter(File.deleted_at.is_(None)).first()
    if not file_record:
        return jsonify({
            "error": "File not found or access denied.",
            "code": "FILE_NOT_FOUND"
        }), 404

    target_version = FileVersion.query.filter_by(id=version_id, file_id=file_id).first()
    if not target_version:
        return jsonify({
            "error": "Version not found.",
            "code": "VERSION_NOT_FOUND"
        }), 404

    all_versions = FileVersion.query.filter_by(file_id=file_id).all()
    if len(all_versions) <= 1:
        return jsonify({
            "error": "Cannot delete the only version of an active file.",
            "code": "CANNOT_DELETE_ONLY_VERSION"
        }), 400

    is_current = (file_record.object_key == target_version.object_key)
    object_key_to_delete = target_version.object_key

    try:
        db.session.delete(target_version)
        db.session.flush()

        if is_current:
            remaining_latest = (
                FileVersion.query.filter_by(file_id=file_id)
                .order_by(FileVersion.version_number.desc())
                .first()
            )
            if remaining_latest:
                file_record.original_filename = remaining_latest.original_filename
                file_record.object_key = remaining_latest.object_key
                file_record.content_type = remaining_latest.content_type
                file_record.size_bytes = remaining_latest.size_bytes
                file_record.checksum_sha256 = remaining_latest.checksum_sha256

        db.session.commit()

        # Invalidate cached file listings for user
        cache_service.invalidate_user_cache(str(g.current_user.id))

        # Delete MinIO object if no other reference exists
        other_ref = FileVersion.query.filter_by(object_key=object_key_to_delete).first()
        if not other_ref and file_record.object_key != object_key_to_delete:
            storage_service.delete_file(object_key_to_delete)

        return jsonify({
            "message": f"Version {target_version.version_number} deleted successfully.",
            "id": str(version_id)
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Failed to delete version.",
            "code": "DELETE_VERSION_ERROR"
        }), 500
