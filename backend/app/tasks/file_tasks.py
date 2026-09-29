import io
import os
import logging
from PIL import Image
import pypdf

from app.celery_app import celery
from app import create_app
from app.extensions import db
from app.models.file import File
from app.models.file_version import FileVersion
from app.services.storage_service import storage_service
from app.services.cache_service import cache_service

logger = logging.getLogger("cloudbox.tasks")

@celery.task(name="app.tasks.file_tasks.process_file_pipeline", bind=True, max_retries=2)
def process_file_pipeline(self, file_id_str: str, version_id_str: str = None):
    """
    Asynchronous file processing worker task:
    1. Thumbnail generation for image formats (JPEG, PNG, WebP, GIF).
    2. PDF metadata extraction (page count, encryption status).
    3. Media & document metadata profiling.
    4. Processing status tracking and cache invalidation.
    """
    app = create_app()
    with app.app_context():
        try:
            file = db.session.get(File, file_id_str)
            if not file:
                logger.warning(f"Task aborted: File '{file_id_str}' not found in database.")
                return {"status": "not_found"}

            file.processing_status = "processing"
            db.session.commit()

            object_key = file.object_key
            if version_id_str:
                version = db.session.get(FileVersion, version_id_str)
                if version:
                    object_key = version.object_key

            stream_resp = storage_service.get_file_stream(object_key)
            if not stream_resp:
                raise ValueError(f"Storage stream unavailable for object '{object_key}'")

            file_bytes = b"".join(stream_resp.stream(32 * 1024))
            extracted_meta = {}
            filename_lower = (file.original_filename or "").lower()
            content_type = (file.content_type or "").lower()

            # 1. Image Thumbnail & Dimension Processing
            if any(filename_lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"]) or content_type.startswith("image/"):
                try:
                    img = Image.open(io.BytesIO(file_bytes))
                    extracted_meta = {
                        "type": "image",
                        "width": img.width,
                        "height": img.height,
                        "format": img.format or "UNKNOWN",
                        "mode": img.mode
                    }

                    # Generate high-quality thumbnail (256x256 max bounds)
                    img.thumbnail((256, 256), Image.Resampling.LANCZOS)
                    thumb_buf = io.BytesIO()
                    
                    # Convert RGBA to RGB for JPEG if needed
                    if img.mode in ("RGBA", "LA", "P"):
                        img_rgb = img.convert("RGB")
                        img_rgb.save(thumb_buf, format="JPEG", quality=85)
                    else:
                        img.save(thumb_buf, format="JPEG", quality=85)
                        
                    thumb_bytes = thumb_buf.getvalue()
                    thumb_key = f"thumbnails/{file.owner_id}/{file.id}_thumb.jpg"
                    
                    # Store thumbnail in MinIO
                    storage_service.upload_file(
                        object_key=thumb_key,
                        data_stream=io.BytesIO(thumb_bytes),
                        length=len(thumb_bytes),
                        content_type="image/jpeg"
                    )
                    file.thumbnail_object_key = thumb_key
                except Exception as img_err:
                    logger.warning(f"Image processing failed for {file.id}: {img_err}")
                    extracted_meta["image_error"] = str(img_err)

            # 2. PDF Document Metadata Processing
            elif filename_lower.endswith(".pdf") or "pdf" in content_type:
                try:
                    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                    extracted_meta = {
                        "type": "pdf",
                        "page_count": len(reader.pages),
                        "is_encrypted": reader.is_encrypted,
                    }
                    if reader.metadata:
                        if reader.metadata.title:
                            extracted_meta["title"] = str(reader.metadata.title)[:100]
                        if reader.metadata.author:
                            extracted_meta["author"] = str(reader.metadata.author)[:100]
                except Exception as pdf_err:
                    logger.warning(f"PDF metadata extraction error for {file.id}: {pdf_err}")
                    extracted_meta["pdf_error"] = str(pdf_err)

            # 3. Generic File Profiling
            else:
                extracted_meta = {
                    "type": "generic",
                    "size_bytes": len(file_bytes),
                    "content_type": file.content_type
                }

            # Update database status
            file.processing_status = "completed"
            file.extracted_metadata = extracted_meta
            file.error_message = None
            db.session.commit()

            # Invalidate cached file and user lists
            cache_service.invalidate_user_cache(str(file.owner_id))
            cache_service.invalidate_file_cache(str(file.id))

            logger.info(f"[+] Background processing completed successfully for file {file.id}")
            return {"status": "completed", "file_id": str(file.id), "metadata": extracted_meta}

        except Exception as exc:
            logger.error(f"[-] Processing pipeline failed for file {file_id_str}: {exc}")
            try:
                file = db.session.get(File, file_id_str)
                if file:
                    file.processing_status = "failed"
                    file.error_message = str(exc)
                    db.session.commit()
            except Exception:
                db.session.rollback()
            raise self.retry(exc=exc, countdown=5)
