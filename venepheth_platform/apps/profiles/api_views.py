from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny

from apps.core.decorators import api_rate_limit

from .models import Profile
from .serializers import ProfileSerializer


@api_rate_limit
class ProfileViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API endpoint that allows academic profiles to be viewed.
    List returns all active profiles.
    """

    queryset = Profile.objects.filter(is_active=True).prefetch_related(
        "educations", "experiences", "languages", "interests"
    )
    serializer_class = ProfileSerializer
    permission_classes = [AllowAny]
