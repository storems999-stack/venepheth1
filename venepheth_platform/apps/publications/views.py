"""Publications views."""

import logging

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.research.models import Publication, ResearchTopic

logger = logging.getLogger("apps.publications")


@require_GET
def publication_list(request):
    """Public publications listing."""
    pub_type = request.GET.get("type", "")
    year = request.GET.get("year", "")
    topic_slug = request.GET.get("topic", "")

    qs = Publication.objects.filter(status="published").prefetch_related("topics")

    if pub_type:
        qs = qs.filter(publication_type=pub_type)
    if year:
        try:
            qs = qs.filter(year=int(year))
        except (TypeError, ValueError):
            logger.warning("Invalid year filter ignored: %r", year)
    if topic_slug:
        qs = qs.filter(topics__slug=topic_slug)

    # Available filter options
    pub_types = Publication.PublicationType.choices
    years = (
        Publication.objects.filter(status="published")
        .exclude(year__isnull=True)
        .values_list("year", flat=True)
        .distinct()
        .order_by("-year")
    )
    topics = ResearchTopic.objects.all()

    paginator = Paginator(qs, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "publications/list.html",
        {
            "publications": page_obj,
            "page_obj": page_obj,
            "pub_types": pub_types,
            "years": years,
            "topics": topics,
            "selected_type": pub_type,
            "selected_year": year,
            "selected_topic": topic_slug,
        },
    )


@require_GET
def publication_detail(request, slug):
    """Publication detail."""
    pub = get_object_or_404(Publication, slug=slug, status="published")
    related = (
        Publication.objects.filter(status="published", topics__in=pub.topics.all())
        .exclude(pk=pub.pk)
        .distinct()
        .order_by("-year")[:5]
    )

    return render(
        request,
        "publications/detail.html",
        {
            "pub": pub,
            "related": related,
            "meta_title": pub.seo_title or pub.title,
            "meta_description": pub.seo_description or pub.abstract[:200],
        },
    )
