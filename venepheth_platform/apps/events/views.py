"""Events views."""

import logging

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models import Event

logger = logging.getLogger("apps.events")


@require_GET
def event_list(request):
    """Public events listing (past events paginated)."""
    now = timezone.now()
    event_type = request.GET.get("type", "")

    qs = Event.objects.filter(status="published")
    if event_type:
        qs = qs.filter(event_type=event_type)

    upcoming_events = qs.filter(start_time__gte=now).order_by("start_time")
    past_qs = qs.filter(start_time__lt=now).order_by("-start_time")

    past_paginator = Paginator(past_qs, 9)
    past_events = past_paginator.get_page(request.GET.get("past_page"))

    types = Event.EventType.choices

    return render(
        request,
        "events/list.html",
        {
            "upcoming_events": upcoming_events,
            "past_events": past_events,
            "types": types,
            "selected_type": event_type,
        },
    )


@require_GET
def event_detail(request, slug):
    """Event detail page."""
    event = get_object_or_404(Event, slug=slug, status="published")
    return render(
        request,
        "events/detail.html",
        {
            "event": event,
            "is_past": event.start_time < timezone.now(),
            "meta_title": event.seo_title or event.title,
            "meta_description": event.seo_description or event.description[:200],
        },
    )
