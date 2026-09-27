from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.decorators import api_rate_limit
from .models import ResearchProject, Publication
from .serializers import ResearchProjectSerializer, PublicationSerializer


@api_rate_limit
class ResearchProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows research projects to be viewed.
    """
    queryset = ResearchProject.objects.filter(status="published").prefetch_related("topics")
    serializer_class = ResearchProjectSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['research_status', 'featured', 'topics__slug']
    search_fields = ['title', 'abstract']
    ordering_fields = ['published_at', 'start_date']
    ordering = ['-published_at']
    lookup_field = "slug"

@api_rate_limit
class PublicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows publications to be viewed.
    """
    queryset = Publication.objects.filter(status="published").prefetch_related("topics")
    serializer_class = PublicationSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['publication_type', 'year', 'featured', 'topics__slug']
    search_fields = ['title', 'abstract', 'authors', 'journal_name', 'keywords']
    ordering_fields = ['year', 'published_at', 'cited_by']
    ordering = ['-year', '-published_at']
    lookup_field = "slug"
