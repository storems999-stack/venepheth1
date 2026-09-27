"""
Knowledge Graph Service — Academic Topic Aggregation.
Generates a "topic node" view by aggregating tags/topics across all
platform content types (Articles, Research Projects, Courses, Publications).

Zero-cost: uses Django ORM + Counter, no external graph DB required.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import TypedDict

from django.db.models import Count


class TopicNode(TypedDict):
    name: str
    slug: str
    count: int
    types: list[str]
    related: list[str]


def _safe_import(module_path: str, model_name: str):
    """Lazily import a model to avoid circular imports."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, model_name, None)
    except (ImportError, AttributeError):
        return None


def build_knowledge_graph(min_count: int = 1) -> list[TopicNode]:
    """
    Aggregate tags / topics from all platform content and produce a
    list of TopicNode dicts, sorted by frequency (descending).

    Supported content types: Article, ResearchProject, Course, Publication.
    """
    # topic_name → {count, types, slugs of related topics (co-occurring)}
    topic_counts: Counter[str] = Counter()
    topic_types: dict[str, set[str]] = defaultdict(set)
    # co-occurrence: topic → Counter of co-occurring topics
    co_occur: dict[str, Counter[str]] = defaultdict(Counter)

    # ── 1. Blog Articles (tags) ────────────────────────────────────────────────
    Article = _safe_import("apps.blog.models", "Article")
    if Article is not None:
        try:
            for row in (
                Article.objects
                .filter(status="published")
                .values_list("tags__name", flat=True)
            ):
                if row:
                    topic_counts[row] += 1
                    topic_types[row].add("blog")
        except Exception:
            pass

    # ── 2. Research Projects (topics M2M → ResearchTopic) ────────────────────
    ResearchProject = _safe_import("apps.research.models", "ResearchProject")
    if ResearchProject is not None:
        try:
            for row in (
                ResearchProject.objects
                .filter(research_status__in=["ongoing", "completed", "published"])
                .values_list("topics__name", flat=True)
            ):
                if row:
                    topic_counts[row] += 1
                    topic_types[row].add("research")
        except Exception:
            pass

    # ── 3. Courses (tags / category) ──────────────────────────────────────────
    Course = _safe_import("apps.courses.models", "Course")
    if Course is not None:
        try:
            for row in (
                Course.objects
                .filter(status="published")
                .values_list("tags__name", flat=True)
            ):
                if row:
                    topic_counts[row] += 1
                    topic_types[row].add("course")
        except Exception:
            pass

    # ── 4. Publications (keywords CharField — split by comma) ──────────────────
    Publication = _safe_import("apps.research.models", "Publication")
    if Publication is not None:
        try:
            for row in (
                Publication.objects
                .filter(status="published")
                .values_list("keywords", flat=True)
            ):
                if row:
                    for kw in (k.strip() for k in row.split(",") if k.strip()):
                        topic_counts[kw] += 1
                        topic_types[kw].add("publication")
        except Exception:
            pass

    # ── Build result list ──────────────────────────────────────────────────────
    results: list[TopicNode] = []
    for name, count in topic_counts.most_common():
        if count < min_count:
            continue
        slug = name.lower().replace(" ", "-").replace("/", "-")
        node: TopicNode = {
            "name": name,
            "slug": slug,
            "count": count,
            "types": sorted(topic_types[name]),
            "related": [],  # future: co-occurrence expansion
        }
        results.append(node)

    return results


def get_topic_detail(topic_name: str) -> dict:
    """
    Return aggregated content for a single topic node.
    Used by the topic detail view to show all related items.
    """
    result: dict = {
        "topic": topic_name,
        "articles": [],
        "research": [],
        "courses": [],
        "publications": [],
    }

    Article = _safe_import("apps.blog.models", "Article")
    if Article is not None:
        try:
            result["articles"] = list(
                Article.objects.filter(
                    status="published", tags__name__iexact=topic_name
                ).values("title", "slug", "published_at")[:10]
            )
        except Exception:
            pass

    ResearchProject = _safe_import("apps.research.models", "ResearchProject")
    if ResearchProject is not None:
        try:
            result["research"] = list(
                ResearchProject.objects.filter(
                    topics__name__iexact=topic_name
                ).values("title", "slug")[:10]
            )
        except Exception:
            pass

    Course = _safe_import("apps.courses.models", "Course")
    if Course is not None:
        try:
            result["courses"] = list(
                Course.objects.filter(
                    status="published", tags__name__iexact=topic_name
                ).values("title", "slug")[:10]
            )
        except Exception:
            pass

    Publication = _safe_import("apps.research.models", "Publication")
    if Publication is not None:
        try:
            result["publications"] = list(
                Publication.objects.filter(
                    status="published",
                    keywords__icontains=topic_name,
                ).values("title", "slug")[:10]
            )
        except Exception:
            pass

    return result
