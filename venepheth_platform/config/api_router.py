"""
API Router configuration for DRF.
"""

from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from apps.blog.api_views import ArticleViewSet
from apps.courses.api_views import CourseCategoryViewSet, CourseViewSet
from apps.events.api_views import EventViewSet
from apps.profiles.api_views import ProfileViewSet
from apps.research.api_views import PublicationViewSet, ResearchProjectViewSet
from apps.resources.api_views import ResourceCategoryViewSet, ResourceViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("profiles", ProfileViewSet, basename="profile")
router.register("courses", CourseViewSet, basename="course")
router.register("course-categories", CourseCategoryViewSet, basename="course-category")
router.register("articles", ArticleViewSet, basename="article")
router.register("research", ResearchProjectViewSet, basename="research")
router.register("publications", PublicationViewSet, basename="publication")
router.register("events", EventViewSet, basename="event")
router.register("resources", ResourceViewSet, basename="resource")
router.register("resource-categories", ResourceCategoryViewSet, basename="resource-category")

app_name = "api"
urlpatterns = router.urls
