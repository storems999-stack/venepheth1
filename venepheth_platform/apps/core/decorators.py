"""Shared decorators."""

from functools import wraps

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django_ratelimit import ALL
from django_ratelimit.decorators import ratelimit

api_rate_limit = method_decorator(
    ratelimit(key="ip", rate="100/m", method=ALL, block=True),
    name="dispatch",
)


def cache_page_unless_htmx(timeout):
    """
    Cache safe full-page responses without mixing user or CSRF state.

    HTMX partial requests and requests without a CSRF cookie bypass the cache.
    Cached responses vary by cookie so session-specific navigation and CSRF
    tokens are never shared between visitors.
    """

    def decorator(view):
        cached_view = cache_page(timeout)(vary_on_cookie(view))

        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.headers.get("HX-Request") or settings.CSRF_COOKIE_NAME not in request.COOKIES:
                return view(request, *args, **kwargs)
            return cached_view(request, *args, **kwargs)

        return wrapper

    return decorator
