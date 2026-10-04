"""Search views."""

import logging

from django.db.models import Q
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
    """Full-text search across all content types (incl. AI Knowledge Box)."""
    q = request.GET.get("q", "").strip()[:200]
    results = {
        "courses": [],
        "articles": [],
        "research": [],
        "publications": [],
        "knowledge": [],
    }

    if q and len(q) >= 2:
        querysets = {
            "courses": (
                Course.objects.filter(
                    status="published",
                    visibility=Course.Visibility.PUBLIC,
                )
                .filter(
                    Q(name__icontains=q)
                    | Q(code__icontains=q)
                    | Q(description__icontains=q)
                    | Q(short_description__icontains=q)
                    | Q(category__name__icontains=q)
                )
                .select_related("category")
            ),
            "articles": (
                Article.objects.filter(
                    status=Article.Status.PUBLISHED,
                )
                .filter(
                    Q(title__icontains=q)
                    | Q(subtitle__icontains=q)
                    | Q(excerpt__icontains=q)
                    | Q(content__icontains=q)
                    | Q(tags__name__icontains=q)
                )
                .distinct()
                .prefetch_related("tags")
            ),
            "research": (
                ResearchProject.objects.filter(
                    status="published",
                )
                .filter(
                    Q(title__icontains=q)
                    | Q(short_title__icontains=q)
                    | Q(abstract__icontains=q)
                    | Q(collaborators__icontains=q)
                    | Q(topics__name__icontains=q)
                )
                .distinct()
                .prefetch_related("topics")
            ),
            "publications": (
                Publication.objects.filter(
                    status="published",
                )
                .filter(
                    Q(title__icontains=q)
                    | Q(abstract__icontains=q)
                    | Q(authors__icontains=q)
                    | Q(journal_name__icontains=q)
                    | Q(doi__icontains=q)
                    | Q(keywords__icontains=q)
                    | Q(topics__name__icontains=q)
                )
                .distinct()
                .prefetch_related("topics")
            ),
        }
        # Curated Knowledge Box — same pool the AI cites, so visitors can
        # verify AI answers through the regular search page.
        from apps.assistant.models import KnowledgeDocument

        querysets["knowledge"] = KnowledgeDocument.objects.filter(
            Q(title__icontains=q)
            | Q(summary__icontains=q)
            | Q(content__icontains=q)
            | Q(file_text__icontains=q)
            | Q(tags__icontains=q),
            is_active=True,
        )

        total = sum(queryset.count() for queryset in querysets.values())
        results = {name: list(queryset[:5]) for name, queryset in querysets.items()}
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
