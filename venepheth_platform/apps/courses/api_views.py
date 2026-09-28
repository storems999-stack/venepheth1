from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny

from apps.core.decorators import api_rate_limit

from .models import Course, CourseCategory, CourseModule
from .serializers import (
    CourseCategorySerializer,
    CourseDetailSerializer,
    CourseListSerializer,
)


@api_rate_limit
class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows courses to be viewed (public courses only).
    """

    queryset = Course.objects.filter(status="published", visibility=Course.Visibility.PUBLIC).select_related("category")
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category__slug", "level", "semester", "featured"]
    search_fields = ["name", "code", "short_description", "description"]
    ordering_fields = ["published_at", "name", "code"]
    ordering = ["-published_at"]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "retrieve":
            qs = qs.prefetch_related(
                Prefetch("modules", queryset=CourseModule.objects.filter(is_visible=True)),
                "outcomes",
            )
        return qs


@api_rate_limit
class CourseCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows course categories to be viewed.
    """

    queryset = CourseCategory.objects.all()
    serializer_class = CourseCategorySerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
