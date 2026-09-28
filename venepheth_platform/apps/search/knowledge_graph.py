"""
Knowledge Graph Service — Academic Topic Aggregation.
Generates a "topic node" view by aggregating tags/topics across all
platform content types (Articles, Research Projects, Courses, Publications).

Zero-cost: uses Django ORM + Counter, no external graph DB required.
Only published/public records are ever aggregated.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import TypedDict

logger = logging.getLogger("apps.search")


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
    # topic_name → {count, types}
    topic_counts: Counter[str] = Counter()
    topic_types: dict[str, set[str]] = defaultdict(set)

    # ── 1. Blog Articles (tags) ────────────────────────────────────────────────
    Article = _safe_import("apps.blog.models", "Article")
    if Article is not None:
        try:
            for row in Article.objects.filter(status="published").values_list("tags__name", flat=True):
                if row:
                    topic_counts[row] += 1
                    topic_types[row].add("blog")
        except Exception:
            logger.exception("Knowledge graph: article aggregation failed")

    # ── 2. Research Projects (topics M2M → ResearchTopic) ────────────────────
    ResearchProject = _safe_import("apps.research.models", "ResearchProject")
    if ResearchProject is not None:
        try:
            for row in ResearchProject.objects.filter(
                status="published",
                research_status__in=["ongoing", "completed", "published"],
            ).values_list("topics__name", flat=True):
                if row:
                    topic_counts[row] += 1
                    topic_types[row].add("research")
        except Exception:
            logger.exception("Knowledge graph: research aggregation failed")

    # ── 3. Courses (category name — Course has no tags field) ────────────────
    Course = _safe_import("apps.courses.models", "Course")
    if Course is not None:
        try:
            for row in Course.objects.filter(status="published", visibility="public").values_list(
                "category__name", flat=True
            ):
                if row:
                    topic_counts[row] += 1
                    topic_types[row].add("course")
        except Exception:
            logger.exception("Knowledge graph: course aggregation failed")

    # ── 4. Publications (keywords CharField — split by comma) ──────────────────
    Publication = _safe_import("apps.research.models", "Publication")
    if Publication is not None:
        try:
            for row in Publication.objects.filter(status="published").values_list("keywords", flat=True):
                if row:
                    for kw in (k.strip() for k in row.split(",") if k.strip()):
                        topic_counts[kw] += 1
                        topic_types[kw].add("publication")
        except Exception:
            logger.exception("Knowledge graph: publication aggregation failed")

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
    topic_name = (topic_name or "")[:100]
    result: dict = {
        "topic": topic_name,
        "articles": [],
        "research": [],
        "courses": [],
        "publications": [],
    }
    if not topic_name:
        return result

    Article = _safe_import("apps.blog.models", "Article")
    if Article is not None:
        try:
            result["articles"] = list(
                Article.objects.filter(status="published", tags__name__iexact=topic_name).values(
                    "title", "slug", "published_at"
                )[:10]
            )
        except Exception:
            logger.exception("Knowledge graph: article detail failed")

    ResearchProject = _safe_import("apps.research.models", "ResearchProject")
    if ResearchProject is not None:
        try:
            result["research"] = list(
                ResearchProject.objects.filter(status="published", topics__name__iexact=topic_name).values(
                    "title", "slug"
                )[:10]
            )
        except Exception:
            logger.exception("Knowledge graph: research detail failed")

    Course = _safe_import("apps.courses.models", "Course")
    if Course is not None:
        try:
            # Course.name → exposed as "title" for the shared template.
            rows = Course.objects.filter(
                status="published",
                visibility="public",
                category__name__iexact=topic_name,
            ).values("name", "slug")[:10]
            result["courses"] = [{"title": row["name"], "slug": row["slug"]} for row in rows]
        except Exception:
            logger.exception("Knowledge graph: course detail failed")

    Publication = _safe_import("apps.research.models", "Publication")
    if Publication is not None:
        try:
            # Whole-keyword match in Python: icontains("art") must not match "earth".
            wanted = topic_name.lower()
            matches = []
            rows = (
                Publication.objects.filter(status="published")
                .exclude(keywords="")
                .values("title", "slug", "keywords")[:50]
            )
            for row in rows:
                keywords = [k.strip().lower() for k in (row["keywords"] or "").split(",")]
                if wanted in keywords:
                    matches.append({"title": row["title"], "slug": row["slug"]})
                    if len(matches) >= 10:
                        break
            result["publications"] = matches
        except Exception:
            logger.exception("Knowledge graph: publication detail failed")

    return result
