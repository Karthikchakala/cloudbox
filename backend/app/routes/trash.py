from flask import Blueprint, jsonify, g
from app.extensions import db
from app.models.file import File
from app.models.file_version import FileVersion
from app.services.storage_service import storage_service
from app.services.security import jwt_required
from app.services.audit_logger import log_security_event

trash_bp = Blueprint("trash", __name__, url_prefix="/api/trash")

@trash_bp.route("", methods=["GET"])
@jwt_required
def list_trash():
    """List soft-deleted files in the Recycle Bin for the authenticated user."""
    deleted_files = (
        File.query.filter_by(owner_id=g.current_user.id)
        .filter(File.deleted_at.isnot(None))
        .order_by(File.deleted_at.desc())
        .all()
    )

    return jsonify({
        "files": [f.to_dict() for f in deleted_files],
        "total": len(deleted_files)
    }), 200


@trash_bp.route("/<uuid:file_id>/restore", methods=["POST"])
@jwt_required
def restore_from_trash(file_id):
    """Restore a soft-deleted file back to the active catalog."""
    file_record = (
        File.query.filter_by(id=file_id, owner_id=g.current_user.id)
        .filter(File.deleted_at.isnot(None))
        .first()
    )
    if not file_record:
        return jsonify({
            "error": "File not found in recycle bin.",
            "code": "FILE_NOT_FOUND"
        }), 404

    try:
        file_record.deleted_at = None
        db.session.commit()

        log_security_event(
            event_type="TRASH",
            action="TRASH_RESTORE",
            status="SUCCESS",
            user_id=str(g.current_user.id),
            target_resource_id=str(file_id),
            details={"filename": file_record.original_filename}
        )

        return jsonify({
            "message": f"'{file_record.original_filename}' restored successfully.",
            "file": file_record.to_dict()
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Failed to restore file.",
            "code": "RESTORE_ERROR"
        }), 500


@trash_bp.route("/<uuid:file_id>", methods=["DELETE"])
@jwt_required
def permanently_delete_file(file_id):
    """
    Permanently delete a file from the Recycle Bin.
    Deletes all version objects from MinIO and deletes metadata from PostgreSQL.
    """
    file_record = (
        File.query.filter_by(id=file_id, owner_id=g.current_user.id)
        .filter(File.deleted_at.isnot(None))
        .first()
    )
    if not file_record:
        return jsonify({
            "error": "File not found in recycle bin.",
            "code": "FILE_NOT_FOUND"
        }), 404

    # Collect all MinIO object keys across versions
    versions = FileVersion.query.filter_by(file_id=file_id).all()
    object_keys = set([v.object_key for v in versions])
    if file_record.object_key:
        object_keys.add(file_record.object_key)

    try:
        # Delete from MinIO
        for key in object_keys:
            storage_service.delete_file(key)

        # Delete from database (cascades to file_versions and share_links)
        db.session.delete(file_record)
        db.session.commit()

        log_security_event(
            event_type="TRASH",
            action="TRASH_PERMANENT_DELETE",
            status="SUCCESS",
            user_id=str(g.current_user.id),
            target_resource_id=str(file_id),
            details={"filename": file_record.original_filename, "objects_deleted": len(object_keys)}
        )

        return jsonify({
            "message": "File permanently deleted.",
            "id": str(file_id)
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Failed to permanently delete file.",
            "code": "PERMANENT_DELETE_ERROR"
        }), 500


@trash_bp.route("", methods=["DELETE"])
@jwt_required
def empty_trash():
    """
    Permanently delete all files in the Recycle Bin for the authenticated user.
    """
    deleted_files = (
        File.query.filter_by(owner_id=g.current_user.id)
        .filter(File.deleted_at.isnot(None))
        .all()
    )

    if not deleted_files:
        return jsonify({
            "message": "Recycle bin is already empty.",
            "deleted_count": 0
        }), 200

    deleted_count = 0
    try:
        for file_record in deleted_files:
            versions = FileVersion.query.filter_by(file_id=file_record.id).all()
            object_keys = set([v.object_key for v in versions])
            if file_record.object_key:
                object_keys.add(file_record.object_key)

            for key in object_keys:
                storage_service.delete_file(key)

            db.session.delete(file_record)
            deleted_count += 1

        db.session.commit()

        log_security_event(
            event_type="TRASH",
            action="TRASH_EMPTY",
            status="SUCCESS",
            user_id=str(g.current_user.id),
            details={"deleted_count": deleted_count}
        )

        return jsonify({
            "message": f"Emptied recycle bin. {deleted_count} files permanently deleted.",
            "deleted_count": deleted_count
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Failed to empty recycle bin.",
            "code": "EMPTY_TRASH_ERROR"
        }), 500
