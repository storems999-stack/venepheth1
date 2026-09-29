"""Courses views."""

import logging

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import F, Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from apps.core.decorators import cache_page_unless_htmx

from .models import Course, CourseCategory, CourseResource

logger = logging.getLogger("apps.courses")


@require_GET
@cache_page_unless_htmx(60 * 15)  # Cache for 15 minutes (HTMX partials bypass)
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
    modules = course.modules.filter(is_visible=True).prefetch_related(
        Prefetch("resources", queryset=CourseResource.objects.filter(visibility=CourseResource.Visibility.PUBLIC))
    )
    outcomes = course.outcomes.all()
    # Sidebar resources must be module-less only. That fixes two bugs at once:
    #  - resources attached to a hidden module were listed here (leaking their
    #    title/external_url) even though the download view 404s on
    #    module.is_visible=False;
    #  - module-owned resources were ALSO rendered by the `modules` prefetch
    #    above, so every module file appeared twice with two download buttons.
    resources = course.resources.filter(visibility=CourseResource.Visibility.PUBLIC, module__isnull=True)
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
            "meta_image": course.thumbnail.url if getattr(course.thumbnail, "name", None) else None,
        },
    )


@require_GET
def course_resource_download(request, pk):
    """Permission-checked course file download (direct /media/ URLs are denied in prod)."""
    from apps.core.sendfile import send_protected_file

    resource = get_object_or_404(
        CourseResource.objects.select_related("course", "module"),
        pk=pk,
        course__status="published",
        course__visibility=Course.Visibility.PUBLIC,
    )
    if resource.visibility == CourseResource.Visibility.PRIVATE:
        raise Http404()
    if resource.visibility == CourseResource.Visibility.STUDENTS and not request.user.is_authenticated:
        return redirect(f"{settings.LOGIN_URL}?next={request.path}")
    if resource.module is not None and not resource.module.is_visible:
        raise Http404()
    if not getattr(resource.file, "name", None):
        raise Http404()

    CourseResource.objects.filter(pk=resource.pk).update(download_count=F("download_count") + 1)
    return send_protected_file(resource.file)
