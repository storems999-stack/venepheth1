"""
Academic Knowledge Retriever (RAG).
Retrieves relevant academic records from Courses, Teaching, Research, Publications,
and Articles for grounding the AI assistant.
"""

from typing import Any

from django.db.models import Q
from django.urls import reverse


class AcademicRetriever:
    """Multi-module academic content retriever."""

    @classmethod
    def retrieve(cls, query: str, limit: int = 8) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return cls._get_default_overview()

        results = []
        tokens = [t for t in query.split() if len(t) > 1]

        # 1. Office Hours & Teaching
        try:
            from apps.teaching.models import OfficeHours, TeachingPhilosophy

            q_oh = Q()
            for t in tokens:
                q_oh |= Q(location__icontains=t) | Q(day_of_week__icontains=t) | Q(notes__icontains=t)

            for oh in OfficeHours.objects.filter(is_active=True).filter(q_oh)[:3]:
                results.append(
                    {
                        "type": "Office Hours",
                        "title": f"Office Hours: {oh.get_day_of_week_display()} {oh.start_time.strftime('%H:%M')}–{oh.end_time.strftime('%H:%M')}",
                        "summary": f"Location: {oh.location}. Meeting link: {oh.meeting_link or 'In-person'}. Notes: {oh.notes}",
                        "url": reverse("teaching:overview"),
                        "score": 3,
                    }
                )

            # Teaching Philosophy query
            for tp in TeachingPhilosophy.objects.filter(is_active=True)[:1]:
                results.append(
                    {
                        "type": "Teaching Philosophy",
                        "title": tp.title,
                        "summary": tp.statement[:300] + "...",
                        "url": reverse("teaching:overview"),
                        "score": 2,
                    }
                )
        except Exception:
            pass

        # 2. Courses
        try:
            from apps.courses.models import Course

            q_course = Q()
            for t in tokens:
                q_course |= Q(title__icontains=t) | Q(code__icontains=t) | Q(description__icontains=t)

            for course in Course.objects.filter(status="published").filter(q_course)[:4]:
                results.append(
                    {
                        "type": "Course",
                        "title": f"{course.code}: {course.title}",
                        "summary": course.description[:250] + "..."
                        if len(course.description) > 250
                        else course.description,
                        "url": course.get_absolute_url()
                        if hasattr(course, "get_absolute_url")
                        else reverse("courses:detail", kwargs={"slug": course.slug}),
                        "extra": f"Level: {course.level} | Credits: {course.credits}",
                        "score": 4,
                    }
                )
        except Exception:
            pass

        # 3. Publications
        try:
            from apps.research.models import Publication

            q_pub = Q()
            for t in tokens:
                q_pub |= Q(title__icontains=t) | Q(abstract__icontains=t) | Q(journal_name__icontains=t)

            for pub in Publication.objects.filter(status="published").filter(q_pub)[:4]:
                results.append(
                    {
                        "type": "Publication",
                        "title": pub.title,
                        "summary": pub.abstract[:250] + "..." if len(pub.abstract) > 250 else pub.abstract,
                        "url": reverse("publications:detail", kwargs={"slug": pub.slug}),
                        "extra": f"Journal: {pub.journal_name or 'N/A'} ({pub.year or ''})",
                        "score": 4,
                    }
                )
        except Exception:
            pass

        # 4. Research Projects
        try:
            from apps.research.models import ResearchProject

            q_res = Q()
            for t in tokens:
                q_res |= Q(title__icontains=t) | Q(abstract__icontains=t) | Q(keywords__icontains=t)

            for proj in ResearchProject.objects.filter(status="published").filter(q_res)[:3]:
                results.append(
                    {
                        "type": "Research Project",
                        "title": proj.title,
                        "summary": proj.abstract[:250] + "..." if len(proj.abstract) > 250 else proj.abstract,
                        "url": reverse("research:detail", kwargs={"slug": proj.slug}),
                        "extra": f"Status: {proj.status}",
                        "score": 3,
                    }
                )
        except Exception:
            pass

        # 5. Articles
        try:
            from apps.blog.models import Article

            q_art = Q()
            for t in tokens:
                q_art |= Q(title__icontains=t) | Q(excerpt__icontains=t)

            for art in Article.objects.filter(status=Article.Status.PUBLISHED).filter(q_art)[:3]:
                results.append(
                    {
                        "type": "Article",
                        "title": art.title,
                        "summary": art.excerpt or art.body[:200] + "...",
                        "url": reverse("blog:detail", kwargs={"slug": art.slug}),
                        "score": 2,
                    }
                )
        except Exception:
            pass

        # If specific search returned nothing, fallback to top featured courses & publications
        if not results:
            results = cls._get_default_overview()

        return results[:limit]

    @classmethod
    def _get_default_overview(cls) -> list[dict[str, Any]]:
        overview = []
        try:
            from apps.teaching.models import OfficeHours

            for oh in OfficeHours.objects.filter(is_active=True)[:2]:
                overview.append(
                    {
                        "type": "Office Hours",
                        "title": f"Office Hours: {oh.get_day_of_week_display()} {oh.start_time.strftime('%H:%M')}–{oh.end_time.strftime('%H:%M')}",
                        "summary": f"Location: {oh.location}. Link: {oh.meeting_link or 'In-person'}",
                        "url": reverse("teaching:overview"),
                    }
                )
        except Exception:
            pass

        try:
            from apps.courses.models import Course

            for c in Course.objects.filter(status="published", featured=True)[:3]:
                overview.append(
                    {
                        "type": "Featured Course",
                        "title": f"{c.code}: {c.title}",
                        "summary": c.description[:200] + "...",
                        "url": reverse("courses:detail", kwargs={"slug": c.slug}),
                    }
                )
        except Exception:
            pass

        return overview
