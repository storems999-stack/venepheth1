"""Profile and CV views."""

import logging

from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import Profile

try:
    from apps.research.models import Publication, ResearchProject

    _HAS_RESEARCH = True
except ImportError:
    _HAS_RESEARCH = False

try:
    from apps.courses.models import Course

    _HAS_COURSES = True
except ImportError:
    _HAS_COURSES = False

logger = logging.getLogger("apps.profiles")


@require_GET
def profile_detail(request):
    """View to display the main profile (Academic CV)."""
    # Assuming the first active profile is the primary one
    profile = (
        Profile.objects.prefetch_related(
            "educations", "experiences", "certifications", "awards", "memberships", "languages", "interests"
        )
        .filter(is_active=True)
        .first()
    )
    if profile is None:
        raise Http404()

    return render(
        request,
        "profiles/detail.html",
        {
            "profile": profile,
            "meta_title": f"Academic Profile — {profile.full_name}",
            "meta_description": profile.short_bio,
        },
    )


@require_GET
def cv_print(request):
    """Print-optimised CV page — user saves as PDF via browser print dialog."""
    profile = (
        Profile.objects.prefetch_related(
            "educations",
            "experiences",
            "certifications",
            "awards",
            "memberships",
            "languages",
            "interests",
        )
        .filter(is_active=True)
        .first()
    )
    if profile is None:
        raise Http404()

    context = {
        "profile": profile,
        "education_list": profile.educations.all() if profile else [],
        "experience_list": profile.experiences.all() if profile else [],
        "certifications": profile.certifications.all() if profile else [],
        "awards": profile.awards.all() if profile else [],
        "memberships": profile.memberships.all() if profile else [],
        "languages": profile.languages.all() if profile else [],
        "academic_interests": profile.interests.all() if profile else [],
    }

    if _HAS_RESEARCH:
        context["research_projects"] = (
            ResearchProject.objects.filter(
                status="published",
                research_status__in=["ongoing", "completed", "published"],
            )
            .prefetch_related("topics")
            .order_by("-start_date")[:20]
        )
        context["publications"] = (
            Publication.objects.filter(status="published")
            .prefetch_related("topics")
            .order_by("-year", "-created_at")[:30]
        )

    if _HAS_COURSES:
        context["courses"] = (
            Course.objects.filter(status="published", visibility="public")
            .select_related("category")
            .order_by("-academic_year", "name")[:20]
        )

    logger.info("CV print page accessed from %s", request.META.get("REMOTE_ADDR", "unknown"))
    return render(request, "profiles/cv_print.html", context)
