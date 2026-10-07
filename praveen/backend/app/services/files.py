"""
services/files.py — File validation, storage, serving, and deletion.
Only jpg/jpeg/png/pdf allowed (checked by extension AND magic bytes).
Files stored under UPLOAD_DIR with UUID names; no path traversal.
"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile

from app.config import get_settings

logger = logging.getLogger(__name__)

MAGIC_BYTES: dict[str, list[bytes]] = {
    ".jpg": [b"\xff\xd8"],
    ".jpeg": [b"\xff\xd8"],
    ".jfif": [b"\xff\xd8"],
    ".png": [b"\x89PNG"],
    ".pdf": [b"%PDF"],
    ".webp": [b"RIFF"],
}

ALLOWED_EXTENSIONS = set(MAGIC_BYTES.keys())

CONTENT_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".jfif": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
    ".webp": "image/webp",
}


def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _check_magic(data: bytes, ext: str) -> bool:
    if ext == ".webp":
        return data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP"
    signatures = MAGIC_BYTES.get(ext, [])
    return any(data.startswith(sig) for sig in signatures)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def validate_and_read_upload(file: UploadFile) -> tuple[bytes, str, str]:
    """
    Read upload, validate extension and magic bytes, enforce size limit.
    Returns (file_bytes, extension, sha256_hex).
    Raises HTTPException on validation failure.
    """
    settings = get_settings()

    # Extension check
    ext = _get_extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail={"error": {"code": "INVALID_FILE_TYPE",
                              "message": f"Only jpg, jpeg, png, pdf are allowed. Got: '{ext}'"}}
        )

    # Read content
    content = await file.read(settings.max_upload_bytes + 1)

    # Size check
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail={"error": {"code": "FILE_TOO_LARGE",
                              "message": f"File exceeds {settings.max_upload_mb} MB limit."}}
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "EMPTY_FILE", "message": "Uploaded file is empty."}}
        )

    # Magic bytes check
    if not _check_magic(content, ext):
        raise HTTPException(
            status_code=415,
            detail={"error": {"code": "INVALID_FILE_CONTENT",
                              "message": "File content does not match the declared extension."}}
        )

    sha = _sha256(content)
    return content, ext, sha


def save_file(content: bytes, ext: str) -> tuple[Path, str]:
    """
    Save file bytes to UPLOAD_DIR with a UUID filename.
    Uses atomic write: write to temp file, then rename.
    Returns (final_path, relative_path_str).
    """
    settings = get_settings()
    upload_dir = settings.upload_dir_resolved
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4()}{ext}"
    final_path = upload_dir / filename
    tmp_path = upload_dir / f".tmp_{filename}"

    try:
        tmp_path.write_bytes(content)
        tmp_path.rename(final_path)
    except Exception as exc:
        # Clean up temp file if rename failed
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                logger.warning("Could not remove tmp file: %s (filename only logged)", filename)
        raise exc

    return final_path, str(final_path)


def get_file_path(file_path_str: str) -> Optional[Path]:
    """
    Resolve file path safely (prevents traversal).
    Returns None if path is outside UPLOAD_DIR.
    """
    settings = get_settings()
    upload_dir = settings.upload_dir_resolved
    try:
        resolved = Path(file_path_str).resolve()
        if not resolved.is_relative_to(upload_dir):
            logger.warning("Path traversal attempt detected (path omitted from log)")
            return None
        return resolved if resolved.is_file() else None
    except Exception:
        return None


def delete_file(file_path_str: str) -> bool:
    """Delete a stored file safely. Returns True if deleted."""
    path = get_file_path(file_path_str)
    if path and path.exists():
        try:
            path.unlink()
            return True
        except Exception as exc:
            logger.warning("Could not delete file (filename omitted): %s", type(exc).__name__)
    return False


def get_content_type(ext: str) -> str:
    return CONTENT_TYPE_MAP.get(ext, "application/octet-stream")
