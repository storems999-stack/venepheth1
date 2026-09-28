from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny

from apps.core.decorators import api_rate_limit

from .models import Resource, ResourceCategory
from .serializers import ResourceCategorySerializer, ResourceSerializer


@api_rate_limit
class ResourceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows resources to be viewed.
    """

    queryset = Resource.objects.filter(visibility=Resource.Visibility.PUBLIC).select_related("category")
    serializer_class = ResourceSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["resource_type", "category__slug", "is_featured", "language"]
    search_fields = ["title", "description", "author", "tags"]
    ordering_fields = ["created_at", "download_count", "view_count"]
    ordering = ["-created_at"]
    lookup_field = "slug"


@api_rate_limit
class ResourceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows resource categories to be viewed.
    """

    queryset = ResourceCategory.objects.all()
    serializer_class = ResourceCategorySerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
