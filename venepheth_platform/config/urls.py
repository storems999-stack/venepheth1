"""
Main URL configuration for Venepheth SAYAVONG Academic Platform.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# ─── Admin URL & Branding ────────────────────────────────────────────────────────
ADMIN_URL = getattr(settings, "ADMIN_URL", "admin/")

admin.site.site_header = "Venepheth SAYAVONG Administration"
admin.site.site_title = "Admin Portal"
admin.site.index_title = "Welcome to the Academic Platform Admin"

from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from apps.core.sitemaps import StaticViewSitemap, ArticleSitemap, ResearchProjectSitemap, CourseSitemap

sitemaps = {
    "static": StaticViewSitemap,
    "blog": ArticleSitemap,
    "research": ResearchProjectSitemap,
    "courses": CourseSitemap,
}

urlpatterns = [
    # ── Admin ──────────────────────────────────────────────────────────────────
    path(ADMIN_URL, admin.site.urls),

    # ── SEO ────────────────────────────────────────────────────────────────────
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="core/robots.txt", content_type="text/plain"),
    ),

    # ── Auth & i18n ───────────────────────────────────────────────────────────
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("allauth.urls")),

    # ── Public ─────────────────────────────────────────────────────────────────
    path("", include("apps.core.urls", namespace="core")),
    path("courses/", include("apps.courses.urls", namespace="courses")),
    path("blog/", include("apps.blog.urls", namespace="blog")),
    path("research/", include("apps.research.urls", namespace="research")),
    path("publications/", include("apps.publications.urls", namespace="publications")),
    path("contact/", include("apps.contact.urls", namespace="contact")),
    path("search/", include("apps.search.urls", namespace="search")),
    path("profile/", include("apps.profiles.urls", namespace="profiles")),
    path("resources/", include("apps.resources.urls", namespace="resources")),
    path("events/", include("apps.events.urls", namespace="events")),
    path("teaching/", include("apps.teaching.urls", namespace="teaching")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("assistant/", include("apps.assistant.urls", namespace="assistant")),

    # ── API ────────────────────────────────────────────────────────────────────
    path("api/v1/", include("config.api_router", namespace="api")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-redoc"),
]

# ─── Static & Media (development only) ────────────────────────────────────────
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ─── Custom Error Handlers ────────────────────────────────────────────────────
handler400 = "apps.core.views.error_400"
handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler429 = "apps.core.views.error_429"
handler500 = "apps.core.views.error_500"
