"""Core API router — assembles all /api/v1/ endpoints."""

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # API Schema
    path("schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    # App endpoints
    path("profile/", include("apps.profiles.api_urls")),
    path("courses/", include("apps.courses.api_urls")),
    path("research/", include("apps.research.api_urls")),
    path("publications/", include("apps.publications.api_urls")),
    path("resources/", include("apps.resources.api_urls")),
    path("blog/", include("apps.blog.api_urls")),
    path("search/", include("apps.search.api_urls")),
]
