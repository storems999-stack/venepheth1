"""
File security validation utilities.
"""

import hashlib
import logging
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger("apps.security")

# MIME detection is required for upload safety; never trust the filename when it
# is unavailable.
try:
    import magic

    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    logger.error("python-magic is unavailable; file uploads will fail MIME validation")


EXPECTED_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".ppt": {"application/vnd.ms-powerpoint"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    ".xls": {"application/vnd.ms-excel"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
    # SVG is deliberately excluded because media files are served inline.
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".gif": {"image/gif"},
    ".webp": {"image/webp"},
    ".mp4": {"video/mp4"},
    ".webm": {"video/webm"},
    ".mov": {"video/quicktime"},
    ".zip": {"application/zip"},
}


def validate_file_extension(value):
    """Validate file extension against the allowed list."""
    ext = Path(value.name).suffix.lower()
    all_allowed = set()
    for extensions in settings.ALLOWED_UPLOAD_EXTENSIONS.values():
        all_allowed.update(extensions)
    if ext not in all_allowed:
        raise ValidationError(
            _("File extension '%(ext)s' is not allowed. Allowed types: %(allowed)s")
            % {
                "ext": ext,
                "allowed": ", ".join(sorted(all_allowed)),
            }
        )


def validate_file_size(value):
    """Validate file does not exceed max upload size."""
    if value.size > settings.MAX_UPLOAD_SIZE:
        max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise ValidationError(
            _("File size %(size)s MB exceeds maximum allowed %(max)s MB.")
            % {
                "size": round(value.size / (1024 * 1024), 2),
                "max": max_mb,
            }
        )


def validate_file_mime(value):
    """Validate MIME type matches allowed list using python-magic."""
    if not HAS_MAGIC:
        raise ValidationError(_("File type detection is unavailable; uploads are temporarily disabled."))

    value.seek(0)
    header = value.read(1024)
    value.seek(0)

    mime = magic.from_buffer(header, mime=True)

    extension = Path(value.name).suffix.lower()
    expected_mimes = EXPECTED_MIME_TYPES.get(extension, set())
    if mime not in expected_mimes:
        logger.warning("Blocked upload with MIME type: %s, filename: %s", mime, value.name)
        raise ValidationError(
            _("File type '%(mime)s' is not permitted for '%(extension)s' files.")
            % {"mime": mime, "extension": extension}
        )


def normalize_filename(filename: str) -> str:
    """
    Normalize a filename:
    - Remove path components
    - Slugify the stem
    - Keep the extension
    """
    from slugify import slugify

    path = Path(filename)
    stem = slugify(path.stem, allow_unicode=False)[:100]  # Limit length
    ext = path.suffix.lower()
    return f"{stem}{ext}" if stem else f"file{ext}"


def compute_file_hash(file_obj) -> str:
    """Compute SHA-256 hash of a file for deduplication."""
    sha256 = hashlib.sha256()
    file_obj.seek(0)
    for chunk in iter(lambda: file_obj.read(8192), b""):
        sha256.update(chunk)
    file_obj.seek(0)
    return sha256.hexdigest()


def secure_upload_path(instance, filename, subdir="uploads"):
    """Generate a secure upload path with normalized filename."""
    from django.utils import timezone

    safe_name = normalize_filename(filename)
    date_path = timezone.now().strftime("%Y/%m/%d")
    return f"{subdir}/{date_path}/{safe_name}"
