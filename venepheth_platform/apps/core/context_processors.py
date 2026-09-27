"""Core context processors."""
from django.conf import settings


def site_settings(request):
    """Inject site-wide settings into every template context."""
    from apps.profiles.models import Profile
    from django.utils import timezone
    
    profile = Profile.objects.filter(is_active=True).first()
    
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Venepheth SAYAVONG"),
        "SITE_TAGLINE": getattr(settings, "SITE_TAGLINE", "Lecturer · Researcher · Academic"),
        "DEBUG": settings.DEBUG,
        "CURRENT_YEAR": timezone.now().year,
        "global_profile": profile,
    }
