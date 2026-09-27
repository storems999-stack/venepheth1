from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.decorators import api_rate_limit
from .models import Event
from .serializers import EventSerializer


@api_rate_limit
class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows events to be viewed.
    """
    queryset = Event.objects.filter(status="published")
    serializer_class = EventSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['event_type', 'is_virtual']
    search_fields = ['title', 'description', 'location', 'organizer']
    ordering_fields = ['start_time', 'published_at']
    ordering = ['start_time']
    lookup_field = "slug"
