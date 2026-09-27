"""Shared decorators."""
from django.utils.decorators import method_decorator
from django_ratelimit import ALL
from django_ratelimit.decorators import ratelimit

api_rate_limit = method_decorator(
    ratelimit(key="ip", rate="100/m", method=ALL, block=True),
    name="dispatch",
)
