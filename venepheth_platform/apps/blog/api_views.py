from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny

from apps.core.decorators import api_rate_limit

from .models import Article
from .serializers import ArticleDetailSerializer, ArticleListSerializer


@api_rate_limit
class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows articles to be viewed.
    """

    queryset = Article.objects.filter(status=Article.Status.PUBLISHED).prefetch_related("tags")
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "is_featured", "tags__slug"]
    search_fields = ["title", "subtitle", "excerpt", "content_raw"]
    ordering_fields = ["published_at", "title"]
    ordering = ["-published_at"]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ArticleDetailSerializer
        return ArticleListSerializer
