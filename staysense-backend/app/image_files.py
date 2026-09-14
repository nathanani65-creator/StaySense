"""Real file-upload handling for accommodation/room-type images: content
validation (actually decoding the file, not trusting the extension), size
limits, EXIF stripping, resizing, thumbnail generation, and unique naming.
Files are saved to disk under settings.upload_dir and served statically by
main.py at /uploads/... — see app/routers/images.py for the endpoints that
call this."""

import io
import uuid
from datetime import date
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from .config import get_settings

settings = get_settings()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_FILES_PER_UPLOAD = 10
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAIN_MAX_DIMENSION = 1920
THUMB_MAX_DIMENSION = 480

UPLOAD_ROOT = Path(settings.upload_dir)


def _group_dir(group: str) -> Path:
    d = UPLOAD_ROOT / group
    d.mkdir(parents=True, exist_ok=True)
    return d


def _resized(img: Image.Image, max_dim: int) -> Image.Image:
    """Downscale to fit within max_dim x max_dim, preserving aspect ratio.
    Never upscales a smaller source image."""
    w, h = img.size
    if max(w, h) <= max_dim:
        return img
    scale = max_dim / max(w, h)
    return img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)


def validate_upload_batch(files: list[UploadFile]) -> None:
    if not files:
        raise HTTPException(status_code=400, detail="ไม่มีไฟล์รูปภาพ")
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(status_code=400, detail=f"อัปโหลดได้สูงสุด {MAX_FILES_PER_UPLOAD} รูปต่อครั้ง")


def save_image_upload(raw: bytes, content_type: str | None, *, group: str, owner_code: str) -> dict:
    """Validates, strips metadata, compresses, and saves one image + its
    thumbnail to disk. Returns {"url", "thumbnailUrl"}. Raises HTTPException
    (400) on any validation failure — nothing partial is left on disk."""
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="ขนาดไฟล์ต้องไม่เกิน 5 MB")
    if content_type and content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์ JPG, PNG หรือ WebP เท่านั้น")

    # Validate the ACTUAL file content, not just the declared content-type —
    # verify() decodes enough of the file to confirm it's a real, intact image.
    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="ไฟล์นี้ไม่ใช่รูปภาพที่ถูกต้อง")

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="ไม่สามารถอ่านไฟล์รูปภาพนี้ได้")

    if img.mode != "RGB":
        img = img.convert("RGB")

    stamp = date.today().strftime("%Y%m%d")
    unique = uuid.uuid4().hex[:12]
    # server-generated filename only — never derived from the uploaded filename
    base_name = f"{owner_code}_{stamp}_{unique}"
    target_dir = _group_dir(group)

    main_path = target_dir / f"{base_name}.webp"
    thumb_path = target_dir / f"{base_name}_thumb.webp"

    try:
        # re-saving through Pillow without forwarding img.info strips EXIF/GPS
        # metadata by construction — nothing exif-related is passed to save()
        main_img = _resized(img, MAIN_MAX_DIMENSION)
        main_img.save(main_path, format="WEBP", quality=82, method=6)

        thumb_img = _resized(img, THUMB_MAX_DIMENSION)
        thumb_img.save(thumb_path, format="WEBP", quality=78, method=6)
    except Exception:
        for p in (main_path, thumb_path):
            if p.exists():
                p.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="บันทึกไฟล์รูปภาพไม่สำเร็จ")

    return {
        "url": f"{settings.public_base_url}/uploads/{group}/{main_path.name}",
        "thumbnailUrl": f"{settings.public_base_url}/uploads/{group}/{thumb_path.name}",
    }
