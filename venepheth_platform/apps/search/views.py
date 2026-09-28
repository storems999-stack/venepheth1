"""Search views."""

import logging

from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET
from django_ratelimit.decorators import ratelimit

from apps.blog.models import Article
from apps.courses.models import Course
from apps.research.models import Publication, ResearchProject

from .knowledge_graph import build_knowledge_graph, get_topic_detail

logger = logging.getLogger("apps.search")


@ratelimit(key="ip", rate="10/m", method="GET", block=True)
@require_GET
def search_results(request):
    """Full-text search across all content types."""
    q = request.GET.get("q", "").strip()[:200]
    results = {
        "courses": [],
        "articles": [],
        "research": [],
        "publications": [],
    }

    if q and len(q) >= 2:
        results["courses"] = Course.objects.filter(
            status="published",
            visibility=Course.Visibility.PUBLIC,
            name__icontains=q,
        ).select_related("category")[:5]
        results["articles"] = Article.objects.filter(
            status=Article.Status.PUBLISHED,
            title__icontains=q,
        ).prefetch_related("tags")[:5]
        results["research"] = ResearchProject.objects.filter(
            status="published",
            title__icontains=q,
        ).prefetch_related("topics")[:5]
        results["publications"] = Publication.objects.filter(
            status="published",
            title__icontains=q,
        ).prefetch_related("topics")[:5]

        total = sum(len(v) for v in results.values())
    else:
        total = 0

    return render(
        request,
        "search/results.html",
        {
            "q": q,
            "results": results,
            "total": total,
            "meta_title": f"Search: {q}" if q else "Search",
        },
    )


@cache_page(60 * 10)  # Cache 10 minutes
@require_GET
def knowledge_graph_view(request):
    """Academic Knowledge Graph — visual topic map across all content."""
    topics = build_knowledge_graph(min_count=1)
    return render(
        request,
        "search/knowledge_graph.html",
        {
            "topics": topics,
            "meta_title": "Academic Knowledge Graph",
            "meta_description": "Explore interconnected academic topics across courses, research, publications and blog.",
            "total_topics": len(topics),
        },
    )


@ratelimit(key="ip", rate="10/m", method="GET", block=True)
@require_GET
def topic_detail_view(request, topic_name: str):
    """Detail view for a single topic node — aggregated content."""
    topic_data = get_topic_detail(topic_name)
    return render(
        request,
        "search/topic_detail.html",
        {
            "topic": topic_name,
            "data": topic_data,
            "meta_title": f"Topic: {topic_name}",
            "meta_description": f"All academic content related to {topic_name}.",
        },
    )
