import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, g
from sqlalchemy import func

from app.extensions import db
from app.models.file import File
from app.models.file_version import FileVersion
from app.models.share_link import ShareLink
from app.services.security import jwt_required
from app.services.cache_service import cache_service

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")

EXTENSION_CATEGORIES = {
    "Documents": {
        "pdf", "doc", "docx", "txt", "rtf", "odt", "ppt", "pptx",
        "xls", "xlsx", "csv", "tsv", "md", "epub"
    },
    "Images": {
        "png", "jpg", "jpeg", "gif", "svg", "webp", "bmp", "ico",
        "tiff", "psd", "ai", "raw"
    },
    "Video": {
        "mp4", "mkv", "mov", "avi", "webm", "wmv", "flv", "m4v"
    },
    "Audio": {
        "mp3", "wav", "flac", "aac", "ogg", "m4a", "wma"
    },
    "Archives": {
        "zip", "tar", "gz", "7z", "rar", "bz2", "xz", "iso"
    },
    "Code": {
        "py", "js", "jsx", "ts", "tsx", "html", "css", "json",
        "yaml", "yml", "sql", "sh", "c", "cpp", "h", "go",
        "rs", "java", "php", "rb", "env"
    }
}

def classify_file(filename: str, content_type: str = "") -> str:
    """Classify file into high-level categories based on extension and MIME type."""
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    for category, extensions in EXTENSION_CATEGORIES.items():
        if ext in extensions:
            return category
            
    if content_type:
        ct = content_type.lower()
        if ct.startswith("image/"):
            return "Images"
        if ct.startswith("video/"):
            return "Video"
        if ct.startswith("audio/"):
            return "Audio"
        if ct.startswith("text/") or "pdf" in ct or "word" in ct or "spreadsheet" in ct:
            return "Documents"
            
    return "Other"

@analytics_bp.route("/overview", methods=["GET"])
@jwt_required
def get_analytics_overview():
    """
    Return comprehensive, user-isolated storage and usage analytics.
    Excludes files belonging to other users. Caches results in Redis with 60s TTL.
    """
    user = g.current_user
    cache_key = f"user:{user.id}:analytics"
    cached = cache_service.get_json(cache_key)
    if cached is not None:
        return jsonify(cached), 200

    now = datetime.now(timezone.utc)

    # 1. Active logical files metrics
    active_files = File.query.filter(File.owner_id == user.id, File.deleted_at.is_(None)).all()
    active_files_count = len(active_files)
    active_storage_bytes = sum(f.size_bytes for f in active_files)

    # 2. Recycle bin files metrics
    trash_files = File.query.filter(File.owner_id == user.id, File.deleted_at.isnot(None)).all()
    trash_files_count = len(trash_files)
    trash_storage_bytes = sum(f.size_bytes for f in trash_files)

    # 3. Versioning metrics across all user's files
    total_versions_count = (
        db.session.query(func.count(FileVersion.id))
        .join(File, FileVersion.file_id == File.id)
        .filter(File.owner_id == user.id)
        .scalar()
        or 0
    )

    total_all_versions_storage_bytes = (
        db.session.query(func.coalesce(func.sum(FileVersion.size_bytes), 0))
        .join(File, FileVersion.file_id == File.id)
        .filter(File.owner_id == user.id)
        .scalar()
        or 0
    )

    # 4. Sharing links metrics
    all_shares = ShareLink.query.filter_by(created_by=user.id).all()
    total_shares_count = len(all_shares)
    
    # Active shares: not revoked, not expired, download count under limit, and parent file not in trash
    trashed_file_ids = {f.id for f in trash_files}
    active_shares_count = sum(
        1 for s in all_shares 
        if s.is_active and s.file_id not in trashed_file_ids
    )

    # 5. File type distribution (active files)
    categories_breakdown = {
        "Documents": {"count": 0, "size_bytes": 0},
        "Images": {"count": 0, "size_bytes": 0},
        "Video": {"count": 0, "size_bytes": 0},
        "Audio": {"count": 0, "size_bytes": 0},
        "Archives": {"count": 0, "size_bytes": 0},
        "Code": {"count": 0, "size_bytes": 0},
        "Other": {"count": 0, "size_bytes": 0},
    }

    for f in active_files:
        cat = classify_file(f.original_filename, f.content_type)
        if cat in categories_breakdown:
            categories_breakdown[cat]["count"] += 1
            categories_breakdown[cat]["size_bytes"] += f.size_bytes
        else:
            categories_breakdown["Other"]["count"] += 1
            categories_breakdown["Other"]["size_bytes"] += f.size_bytes

    # Calculate percentage shares
    type_distribution = []
    for cat_name, data in categories_breakdown.items():
        pct_storage = round((data["size_bytes"] / active_storage_bytes * 100), 1) if active_storage_bytes > 0 else 0.0
        pct_count = round((data["count"] / active_files_count * 100), 1) if active_files_count > 0 else 0.0
        type_distribution.append({
            "category": cat_name,
            "count": data["count"],
            "size_bytes": data["size_bytes"],
            "percentage_storage": pct_storage,
            "percentage_count": pct_count,
        })

    # 6. Upload timeline activity (grouped by date)
    date_buckets = {}
    for f in active_files:
        if f.created_at:
            d_str = f.created_at.strftime("%Y-%m-%d")
            if d_str not in date_buckets:
                date_buckets[d_str] = {"date": d_str, "count": 0, "size_bytes": 0}
            date_buckets[d_str]["count"] += 1
            date_buckets[d_str]["size_bytes"] += f.size_bytes

    # Sort chronological
    timeline = sorted(date_buckets.values(), key=lambda x: x["date"])

    response_payload = {
        "status": "success",
        "timestamp": now.isoformat(),
        "user_id": str(user.id),
        "username": user.username,
        "summary": {
            "active_files_count": active_files_count,
            "active_storage_bytes": active_storage_bytes,
            "trash_files_count": trash_files_count,
            "trash_storage_bytes": trash_storage_bytes,
            "total_versions_count": total_versions_count if total_versions_count > 0 else active_files_count,
            "total_all_versions_storage_bytes": total_all_versions_storage_bytes if total_all_versions_storage_bytes > 0 else active_storage_bytes,
            "total_shares_count": total_shares_count,
            "active_shares_count": active_shares_count,
        },
        "file_type_distribution": type_distribution,
        "upload_timeline": timeline,
    }

    cache_service.set_json(cache_key, response_payload, ttl_seconds=60)
    return jsonify(response_payload), 200
