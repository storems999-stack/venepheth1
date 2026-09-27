"""Research views."""
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_GET
from django.core.paginator import Paginator
from django.views.decorators.cache import cache_page
from .models import ResearchProject, ResearchTopic, Publication

logger = logging.getLogger("apps.research")


@require_GET
@cache_page(60 * 15)  # Cache for 15 minutes
def research_list(request):
    """Public research projects listing."""
    status_filter = request.GET.get("status", "")
    topic_slug = request.GET.get("topic", "")
    
    qs = ResearchProject.objects.filter(status="published").prefetch_related("topics")
    
    if status_filter:
        qs = qs.filter(research_status=status_filter)
    if topic_slug:
        qs = qs.filter(topics__slug=topic_slug)
    
    topics = ResearchTopic.objects.all()
    statuses = ResearchProject.ResearchStatus.choices
    
    paginator = Paginator(qs, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    template_name = "research/partials/project_grid.html" if request.headers.get("HX-Request") else "research/list.html"
    
    return render(request, template_name, {
        "projects": page_obj,
        "page_obj": page_obj,
        "topics": topics,
        "statuses": statuses,
        "selected_status": status_filter,
        "selected_topic": topic_slug,
    })


@require_GET
def project_detail(request, slug):
    """Research project detail."""
    project = get_object_or_404(ResearchProject, slug=slug, status="published")
    related_publications = project.publications.filter(status="published").order_by("-year")[:5]
    
    return render(request, "research/detail.html", {
        "project": project,
        "related_publications": related_publications,
        "meta_title": project.seo_title or project.title,
        "meta_description": project.seo_description or project.abstract[:200],
        "meta_image": project.cover_image.url if getattr(project, 'cover_image', None) else None,
    })


@require_GET
def publications_redirect(request):
    """Redirect /research/publications/ → /publications/."""
    return redirect("publications:list", permanent=True)
