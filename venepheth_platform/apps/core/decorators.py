"""Shared decorators."""

from functools import wraps

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_ratelimit import ALL
from django_ratelimit.decorators import ratelimit

api_rate_limit = method_decorator(
    ratelimit(key="ip", rate="100/m", method=ALL, block=True),
    name="dispatch",
)


def cache_page_unless_htmx(timeout):
    """
    Like cache_page, but HTMX partial requests bypass the cache.

    Rationale: @cache_page keys on URL only, so a cached full page would be
    served for an HTMX partial request (and vice versa) when a view renders
    different templates per HX-Request.
    """

    def decorator(view):
        cached_view = cache_page(timeout)(view)

        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.headers.get("HX-Request"):
                return view(request, *args, **kwargs)
            return cached_view(request, *args, **kwargs)

        return wrapper

    return decorator
