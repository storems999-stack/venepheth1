"""Blog views."""
import logging
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_GET
from django.core.paginator import Paginator
from django.views.decorators.cache import cache_page
from .models import Article, ArticleTag

logger = logging.getLogger("apps.blog")


@require_GET
@cache_page(60 * 15)  # Cache for 15 minutes
def article_list(request):
    """Public blog listing."""
    category = request.GET.get("category", "")
    tag_slug = request.GET.get("tag", "")
    
    qs = Article.objects.filter(status=Article.Status.PUBLISHED).prefetch_related("tags")
    
    if category:
        qs = qs.filter(category=category)
    if tag_slug:
        qs = qs.filter(tags__slug=tag_slug)
    
    tags = ArticleTag.objects.all()
    categories = Article.Category.choices
    
    paginator = Paginator(qs, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    template_name = "blog/partials/article_grid.html" if request.headers.get("HX-Request") else "blog/list.html"
    
    return render(request, template_name, {
        "articles": page_obj,
        "page_obj": page_obj,
        "tags": tags,
        "categories": categories,
        "selected_category": category,
        "selected_tag": tag_slug,
    })


@require_GET
def article_detail(request, slug):
    """Blog article detail."""
    article = get_object_or_404(Article, slug=slug, status=Article.Status.PUBLISHED)
    
    # Increment view count
    Article.objects.filter(pk=article.pk).update(view_count=article.view_count + 1)
    
    # Related articles
    related = Article.objects.filter(
        status=Article.Status.PUBLISHED,
        category=article.category,
    ).exclude(pk=article.pk).prefetch_related("tags").order_by("-published_at")[:3]
    
    return render(request, "blog/detail.html", {
        "article": article,
        "related": related,
        "meta_title": article.seo_title or article.title,
        "meta_description": article.seo_description or article.excerpt,
        "meta_image": article.thumbnail.url if getattr(article, 'thumbnail', None) else None,
    })


@require_GET
def article_by_tag(request, tag_slug):
    """Filter articles by tag."""
    tag = get_object_or_404(ArticleTag, slug=tag_slug)
    articles = Article.objects.filter(
        status=Article.Status.PUBLISHED,
        tags=tag,
    ).prefetch_related("tags")
    
    paginator = Paginator(articles, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "blog/list.html", {
        "articles": page_obj,
        "page_obj": page_obj,
        "tags": ArticleTag.objects.all(),
        "categories": Article.Category.choices,
        "selected_tag": tag_slug,
        "current_tag": tag,
    })
