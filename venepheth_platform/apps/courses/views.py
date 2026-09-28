"""Courses views."""

import logging

from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET

from .models import Course, CourseCategory

logger = logging.getLogger("apps.courses")


@require_GET
@cache_page(60 * 15)  # Cache for 15 minutes
def course_list(request):
    """Public list of all published courses."""
    category_slug = request.GET.get("category", "")
    level = request.GET.get("level", "")

    qs = Course.objects.filter(status="published", visibility="public").select_related("category")

    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if level:
        qs = qs.filter(level__icontains=level)

    categories = CourseCategory.objects.all()

    paginator = Paginator(qs, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    template_name = "courses/partials/course_grid.html" if request.headers.get("HX-Request") else "courses/list.html"

    return render(
        request,
        template_name,
        {
            "courses": page_obj,
            "page_obj": page_obj,
            "categories": categories,
            "selected_category": category_slug,
            "selected_level": level,
            "levels": ["Undergraduate", "Graduate", "PhD"],
        },
    )


@require_GET
def course_detail(request, slug):
    """Course detail page (public courses only)."""
    course = get_object_or_404(Course, slug=slug, status="published", visibility=Course.Visibility.PUBLIC)
    modules = course.modules.filter(is_visible=True).prefetch_related("resources")
    outcomes = course.outcomes.all()
    resources = course.resources.filter(visibility="public")
    announcements = course.announcements.filter(status="published").order_by("-is_pinned", "-published_at")[:5]

    return render(
        request,
        "courses/detail.html",
        {
            "course": course,
            "modules": modules,
            "outcomes": outcomes,
            "resources": resources,
            "announcements": announcements,
            "meta_title": course.seo_title or course.name,
            "meta_description": course.seo_description or course.short_description,
            "meta_image": course.thumbnail.url if getattr(course, "thumbnail", None) else None,
        },
    )
