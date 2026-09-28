"""
File security validation utilities.
"""

import hashlib
import logging
import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger("apps.security")

# Try to use python-magic for MIME detection
try:
    import magic

    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    logger.warning("python-magic not available; falling back to mimetypes for MIME detection")


ALLOWED_MIME_TYPES = {
    # Documents
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/markdown",
    # Images (no SVG — served inline from /media/, executes JavaScript)
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    # Video
    "video/mp4",
    "video/webm",
    "video/quicktime",
    # Archive
    "application/zip",
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
    value.seek(0)
    header = value.read(1024)
    value.seek(0)

    if HAS_MAGIC:
        mime = magic.from_buffer(header, mime=True)
    else:
        mime, _encoding = mimetypes.guess_type(value.name)
        mime = mime or "application/octet-stream"

    if mime not in ALLOWED_MIME_TYPES:
        logger.warning("Blocked upload with MIME type: %s, filename: %s", mime, value.name)
        raise ValidationError(_("File type '%(mime)s' is not permitted.") % {"mime": mime})


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
