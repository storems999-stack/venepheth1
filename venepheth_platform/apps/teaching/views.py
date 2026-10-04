"""Teaching app views."""

import logging

from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.courses.models import Course

from .models import OfficeHours, StudentAnnouncement, TeachingPhilosophy, weekday_ordering

logger = logging.getLogger("apps.teaching")


@require_GET
def teaching_overview(request):
    """Teaching overview: office hours, philosophy, recent announcements."""
    office_hours = (
        OfficeHours.objects.filter(is_active=True)
        .annotate(_day_order=weekday_ordering())
        .order_by("_day_order", "start_time")
    )
    philosophy = TeachingPhilosophy.objects.filter(is_active=True).first()
    announcements = StudentAnnouncement.objects.filter(status="published").order_by("-created_at")[:5]
    current_courses = (
        Course.objects.filter(status="published", visibility="public")
        .select_related("category")
        .order_by("-academic_year")[:6]
    )

    return render(
        request,
        "teaching/overview.html",
        {
            "office_hours": office_hours,
            "philosophy": philosophy,
            "announcements": announcements,
            "current_courses": current_courses,
            "meta_title": "Teaching",
            "meta_description": "Office hours, teaching philosophy, and current courses taught by Venepheth Sayavong.",
        },
    )
