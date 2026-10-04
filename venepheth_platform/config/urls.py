"""
Main URL configuration for Venepheth SAYAVONG Academic Platform.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.generic import RedirectView, TemplateView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.sitemaps import (
    ArticleSitemap,
    CourseSitemap,
    PublicationSitemap,
    ResearchProjectSitemap,
    ResourceSitemap,
    StaticViewSitemap,
)
from apps.core.views import protected_media_not_found

# ─── Admin URL & Branding ────────────────────────────────────────────────────────
ADMIN_URL = getattr(settings, "ADMIN_URL", "admin/")

admin.site.site_header = "Venepheth SAYAVONG Administration"
admin.site.site_title = "Admin Portal"
admin.site.index_title = "Welcome to the Academic Platform Admin"

sitemaps = {
    "static": StaticViewSitemap,
    "blog": ArticleSitemap,
    "research": ResearchProjectSitemap,
    "courses": CourseSitemap,
    "publications": PublicationSitemap,
    "resources": ResourceSitemap,
}

urlpatterns = [
    # Permission-gated uploads must not bypass their download views through
    # Django's DEBUG media route.
    re_path(
        r"^media/(?:resources|publications|courses/resources|assistant/knowledge)/(?P<private_path>.*)$",
        protected_media_not_found,
    ),
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
    # Public registration CLOSED (apps/accounts/adapter.py) — send signup traffic to login.
    path("accounts/signup/", RedirectView.as_view(url="/accounts/login/", permanent=False)),
    path("accounts/", include("allauth.urls")),
    path("my/", include("apps.accounts.urls", namespace="accounts")),
    # ── Health Checks (vision §43) ────────────────────────────────────────────
    path("health/", include("apps.core.health_urls")),
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
    path("teaching/", include("apps.teaching.urls", namespace="teaching")),
    # AI Academic Assistant (vision §49/§50)
    path("assistant/", include("apps.assistant.urls", namespace="assistant")),
    # PARKED — these apps do not exist yet; uncomment when created:
    # path("events/", include("apps.events.urls", namespace="events")),
    # path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    # path("search/topics/...") — see apps/search/urls.py
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
