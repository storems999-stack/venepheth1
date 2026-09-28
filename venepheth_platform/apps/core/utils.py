"""Shared core utilities."""


def get_client_ip(request):
    """Return the client IP address, respecting proxy headers."""
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
