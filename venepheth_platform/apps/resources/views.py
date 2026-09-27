"""Digital Resources views."""
import logging
from django.shortcuts import render, get_object_or_404
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
    
    return render(request, "resources/list.html", {
        "resources": qs,
        "categories": categories,
        "types": types,
        "selected_category": category_slug,
        "selected_type": resource_type,
    })

@require_GET
def resource_detail(request, slug):
    """Resource detail and download page."""
    # Allow students to see student-only resources if we had auth (for now just check if not private)
    resource = get_object_or_404(Resource.objects.exclude(visibility=Resource.Visibility.PRIVATE), slug=slug)
    
    # Increment view count
    Resource.objects.filter(pk=resource.pk).update(view_count=resource.view_count + 1)
    
    related = Resource.objects.filter(
        visibility=Resource.Visibility.PUBLIC,
        category=resource.category
    ).exclude(pk=resource.pk)[:4]
    
    return render(request, "resources/detail.html", {
        "resource": resource,
        "related": related,
    })
