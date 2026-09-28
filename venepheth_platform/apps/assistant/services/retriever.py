"""
Academic Knowledge Retriever (RAG).
Retrieves relevant academic records from Courses, Teaching, Research, Publications,
and Articles for grounding the AI assistant.

Only published/public records are ever returned. Field names below must match
the real models (Course.name, TeachingPhilosophy.headline/body, ...).
"""

import logging
from typing import Any

from django.db.models import Q
from django.urls import reverse
from django.utils.html import strip_tags

logger = logging.getLogger("apps.assistant")

_MAX_TOKENS = 10


def _search_terms(query: str) -> list[str]:
    """Token list plus the full raw query (so spaceless Lao phrases still match)."""
    tokens = [t for t in query.split() if len(t) > 1][:_MAX_TOKENS]
    terms = list(dict.fromkeys([query, *tokens]))
    return [t for t in terms if t]


def _or_icontains(fields: list[str], terms: list[str]) -> Q:
    """OR-combined icontains across fields x terms. Empty terms → match nothing."""
    q = Q(pk__in=[])
    for field in fields:
        for term in terms:
            q |= Q(**{f"{field}__icontains": term})
    return q


class AcademicRetriever:
    """Multi-module academic content retriever."""

    @classmethod
    def retrieve(cls, query: str, limit: int = 8) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return cls._get_default_overview()
        terms = _search_terms(query)
        if not terms:
            return cls._get_default_overview()

        results: list[dict[str, Any]] = []
        results.extend(cls._office_hours(terms))
        results.extend(cls._courses(terms))
        results.extend(cls._publications(terms))
        results.extend(cls._research_projects(terms))
        results.extend(cls._articles(terms))

        # Highest score first, then truncate.
        results.sort(key=lambda item: item.get("score", 0), reverse=True)

        if not results:
            results = cls._get_default_overview()
        return results[:limit]

    # ─── Branch helpers (each fail-safe on its own) ──────────────────────────

    @classmethod
    def _office_hours(cls, terms: list[str]) -> list[dict[str, Any]]:
        try:
            from apps.teaching.models import OfficeHours, TeachingPhilosophy

            items: list[dict[str, Any]] = []
            q = _or_icontains(["location", "notes", "day"], terms)
            for oh in OfficeHours.objects.filter(is_active=True).filter(q)[:3]:
                items.append(
                    {
                        "type": "Office Hours",
                        "title": f"Office Hours: {oh.get_day_display()} {oh.start_time:%H:%M}–{oh.end_time:%H:%M}",
                        "summary": f"Location: {oh.location or 'TBA'}. Notes: {oh.notes or '-'}",
                        "url": reverse("teaching:overview"),
                        "score": 3,
                    }
                )
            # Philosophy only when the query actually matches it (intent-gated).
            q_tp = _or_icontains(["headline", "body"], terms)
            for tp in TeachingPhilosophy.objects.filter(is_active=True).filter(q_tp)[:1]:
                items.append(
                    {
                        "type": "Teaching Philosophy",
                        "title": tp.headline,
                        "summary": tp.body[:300],
                        "url": reverse("teaching:overview"),
                        "score": 2,
                    }
                )
            return items
        except Exception:
            logger.exception("Assistant retriever: office-hours branch failed")
            return []

    @classmethod
    def _courses(cls, terms: list[str]) -> list[dict[str, Any]]:
        try:
            from apps.courses.models import Course

            items: list[dict[str, Any]] = []
            q = _or_icontains(["name", "code", "description"], terms)
            qs = Course.objects.filter(status="published", visibility=Course.Visibility.PUBLIC).filter(q)[:4]
            for course in qs:
                description = course.description or ""
                items.append(
                    {
                        "type": "Course",
                        "title": f"{course.code}: {course.name}" if course.code else course.name,
                        "summary": description[:250],
                        "url": course.get_absolute_url(),
                        "extra": f"Level: {course.level or '-'} | Credits: {course.credits}",
                        "score": 4,
                    }
                )
            return items
        except Exception:
            logger.exception("Assistant retriever: courses branch failed")
            return []

    @classmethod
    def _publications(cls, terms: list[str]) -> list[dict[str, Any]]:
        try:
            from apps.research.models import Publication

            items: list[dict[str, Any]] = []
            q = _or_icontains(["title", "abstract", "journal_name", "authors", "keywords"], terms)
            for pub in Publication.objects.filter(status="published").filter(q)[:4]:
                abstract = pub.abstract or ""
                items.append(
                    {
                        "type": "Publication",
                        "title": pub.title,
                        "summary": abstract[:250],
                        "url": pub.get_absolute_url(),
                        "extra": f"Journal: {pub.journal_name or 'N/A'} ({pub.year or ''})",
                        "score": 4,
                    }
                )
            return items
        except Exception:
            logger.exception("Assistant retriever: publications branch failed")
            return []

    @classmethod
    def _research_projects(cls, terms: list[str]) -> list[dict[str, Any]]:
        try:
            from apps.research.models import ResearchProject

            items: list[dict[str, Any]] = []
            q = _or_icontains(["title", "abstract", "collaborators", "funding_source"], terms)
            for proj in ResearchProject.objects.filter(status="published").filter(q)[:3]:
                abstract = proj.abstract or ""
                items.append(
                    {
                        "type": "Research Project",
                        "title": proj.title,
                        "summary": abstract[:250],
                        "url": proj.get_absolute_url(),
                        "extra": f"Status: {proj.get_research_status_display()}",
                        "score": 3,
                    }
                )
            return items
        except Exception:
            logger.exception("Assistant retriever: research branch failed")
            return []

    @classmethod
    def _articles(cls, terms: list[str]) -> list[dict[str, Any]]:
        try:
            from apps.blog.models import Article

            items: list[dict[str, Any]] = []
            q = _or_icontains(["title", "excerpt", "content"], terms)
            for art in Article.objects.filter(status=Article.Status.PUBLISHED).filter(q)[:3]:
                summary = art.excerpt or strip_tags(art.content or "")[:200]
                items.append(
                    {
                        "type": "Article",
                        "title": art.title,
                        "summary": summary,
                        "url": art.get_absolute_url(),
                        "score": 2,
                    }
                )
            return items
        except Exception:
            logger.exception("Assistant retriever: articles branch failed")
            return []

    @classmethod
    def _get_default_overview(cls) -> list[dict[str, Any]]:
        overview: list[dict[str, Any]] = []
        try:
            from apps.teaching.models import OfficeHours

            for oh in OfficeHours.objects.filter(is_active=True)[:2]:
                overview.append(
                    {
                        "type": "Office Hours",
                        "title": f"Office Hours: {oh.get_day_display()} {oh.start_time:%H:%M}–{oh.end_time:%H:%M}",
                        "summary": f"Location: {oh.location or 'TBA'}",
                        "url": reverse("teaching:overview"),
                    }
                )
        except Exception:
            logger.exception("Assistant retriever: overview office-hours failed")

        try:
            from apps.courses.models import Course

            for c in Course.objects.filter(status="published", visibility=Course.Visibility.PUBLIC, featured=True)[:3]:
                overview.append(
                    {
                        "type": "Featured Course",
                        "title": f"{c.code}: {c.name}" if c.code else c.name,
                        "summary": (c.description or "")[:200],
                        "url": c.get_absolute_url(),
                    }
                )
        except Exception:
            logger.exception("Assistant retriever: overview courses failed")

        return overview
