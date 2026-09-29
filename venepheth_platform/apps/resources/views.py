"""Digital Resources views."""

import logging

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .models import Resource, ResourceCategory

logger = logging.getLogger("apps.resources")


@require_GET
def resource_list(request):
    """Public resources library."""
    category_slug = request.GET.get("category", "")
    resource_type = request.GET.get("type", "")

    # Only show public resources by default
    qs = Resource.objects.filter(visibility=Resource.Visibility.PUBLIC).select_related("category")

    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if resource_type:
        qs = qs.filter(resource_type=resource_type)

    categories = ResourceCategory.objects.all()
    types = Resource.ResourceType.choices

    paginator = Paginator(qs, 9)
    page_obj = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    return render(
        request,
        "resources/list.html",
        {
            "resources": page_obj,
            "page_obj": page_obj,
            "querystring": params.urlencode(),
            "categories": categories,
            "types": types,
            "selected_category": category_slug,
            "selected_type": resource_type,
        },
    )


@require_GET
def resource_detail(request, slug):
    """Resource detail and download page."""
    resource = get_object_or_404(Resource, slug=slug)
    gate = _check_resource_access(request, resource)
    if gate is not None:
        return gate

    # Increment view count (atomic — avoids lost-update races).
    # queryset.update() does not refresh the in-memory instance, so bump the
    # attribute too; otherwise the template renders a count one behind.
    Resource.objects.filter(pk=resource.pk).update(view_count=F("view_count") + 1)
    resource.view_count += 1

    related = Resource.objects.filter(visibility=Resource.Visibility.PUBLIC).exclude(pk=resource.pk)
    if resource.category_id:
        related = related.filter(category=resource.category)
    related = related.select_related("category")[:4]

    return render(
        request,
        "resources/detail.html",
        {
            "resource": resource,
            "related": related,
        },
    )


def _check_resource_access(request, resource):
    """Shared visibility gate for detail + download. Returns redirect/404 or None."""
    if resource.visibility == Resource.Visibility.PRIVATE:
        raise Http404()
    if resource.visibility == Resource.Visibility.STUDENTS and not request.user.is_authenticated:
        return redirect(f"{settings.LOGIN_URL}?next={request.path}")
    return None


@require_GET
def resource_download(request, slug):
    """Permission-checked file download (direct /media/ URLs are denied in prod)."""
    from apps.core.sendfile import send_protected_file

    resource = get_object_or_404(Resource, slug=slug)
    gate = _check_resource_access(request, resource)
    if gate is not None:
        return gate
    if not getattr(resource.file, "name", None):
        raise Http404()

    Resource.objects.filter(pk=resource.pk).update(download_count=F("download_count") + 1)
    return send_protected_file(resource.file)
