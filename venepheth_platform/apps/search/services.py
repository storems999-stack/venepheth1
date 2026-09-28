"""
Search services using PostgreSQL Full-Text Search.
"""

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

from apps.blog.models import Article
from apps.courses.models import Course
from apps.research.models import Publication, ResearchProject
from apps.resources.models import Resource


def search_all(query_text):
    """
    Search across all major content types and return mixed results.
    Note: For a very large system, this should be done with Elasticsearch/OpenSearch.
    For this scale, PostgreSQL FTS is excellent.
    """
    if not query_text:
        return []

    search_query = SearchQuery(query_text)

    # 1. Search Courses
    courses = (
        Course.objects.filter(status=Course.Status.PUBLISHED)
        .annotate(rank=SearchRank(SearchVector("name", "description", "code"), search_query))
        .filter(rank__gte=0.1)
        .order_by("-rank")[:10]
    )

    # 2. Search Publications
    publications = (
        Publication.objects.filter(status=Publication.Status.PUBLISHED)
        .annotate(rank=SearchRank(SearchVector("title", "abstract", "authors", "keywords"), search_query))
        .filter(rank__gte=0.1)
        .order_by("-rank")[:10]
    )

    # 3. Search Research Projects
    projects = (
        ResearchProject.objects.filter(status=ResearchProject.Status.PUBLISHED)
        .annotate(rank=SearchRank(SearchVector("title", "abstract", "funding_source"), search_query))
        .filter(rank__gte=0.1)
        .order_by("-rank")[:10]
    )

    # 4. Search Articles
    articles = (
        Article.objects.filter(status=Article.Status.PUBLISHED)
        .annotate(rank=SearchRank(SearchVector("title", "excerpt", "content"), search_query))
        .filter(rank__gte=0.1)
        .order_by("-rank")[:10]
    )

    # 5. Search Resources (Public only)
    resources = (
        Resource.objects.filter(visibility=Resource.Visibility.PUBLIC)
        .annotate(rank=SearchRank(SearchVector("title", "description", "tags"), search_query))
        .filter(rank__gte=0.1)
        .order_by("-rank")[:10]
    )

    # Combine and sort by rank
    results = []
    for item in list(courses) + list(publications) + list(projects) + list(articles) + list(resources):
        results.append(
            {
                "type": item._meta.verbose_name,
                "title": str(item),
                "url": item.get_absolute_url() if hasattr(item, "get_absolute_url") else "#",
                "rank": item.rank,
            }
        )

    results.sort(key=lambda x: x["rank"], reverse=True)
    return results[:20]
