"""Protected file serving.

Files with visibility rules (library resources, publication PDFs, course
files) must never be linked directly under /media/ — nginx denies those
paths (see docker/nginx/nginx.prod.conf) and Django serves them through
permission-checked download views instead.

- Production (SENDFILE_ENABLED=True): zero-copy via X-Accel-Redirect,
  nginx serves bytes from an `internal` location.
- Development/tests: plain FileResponse.
"""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


def send_protected_file(field_file, download_name: str | None = None):
    """Serve a FileField/FileFieldFile after the caller checked permissions."""
    name = getattr(field_file, "name", "") or ""
    if not name or ".." in Path(name).parts:
        raise Http404()
    try:
        storage_path = Path(field_file.path)
    except (NotImplementedError, ValueError):
        raise Http404()
    if not storage_path.is_file():
        raise Http404()

    # Defence in depth: the resolved path must stay inside MEDIA_ROOT. The
    # upload_to slugify already guarantees this, but a name that ever came from
    # elsewhere must not be able to read outside the media tree.
    media_root = Path(getattr(settings, "MEDIA_ROOT", "")).resolve()
    try:
        resolved = storage_path.resolve()
        resolved.relative_to(media_root)
    except (ValueError, OSError):
        raise Http404()

    filename = download_name or storage_path.name
    if getattr(settings, "SENDFILE_ENABLED", False):
        import mimetypes

        response = HttpResponse(status=200)
        response["X-Accel-Redirect"] = f"/protected-media/{name}"
        content_type, _ = mimetypes.guess_type(filename)
        response["Content-Type"] = content_type or "application/octet-stream"
        # Escape quotes/backslashes: Django rejects CR/LF in headers but happily
        # accepts a bare `"`, which would terminate the quoted filename early.
        safe_name = filename.replace("\\", "\\\\").replace('"', '\\"')
        response["Content-Disposition"] = f'attachment; filename="{safe_name}"'
        return response
    return FileResponse(field_file.open("rb"), as_attachment=True, filename=filename)
