"""RSS Feed for Blog articles."""

from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed

from apps.blog.models import Article


class LatestArticlesFeed(Feed):
    title = "Venepheth SAYAVONG - Latest Articles"
    link = "/blog/"
    description = "Updates on new articles and research notes from Venepheth Sayavong."

    def items(self):
        return Article.objects.filter(status="published").order_by("-published_at")[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        # NOTE: `content` is bleach-sanitized on save; never expose `content_raw`.
        return item.excerpt or item.content[:200]

    def item_pubdate(self, item):
        return item.published_at or item.created_at


class AtomLatestArticlesFeed(LatestArticlesFeed):
    feed_type = Atom1Feed
    subtitle = LatestArticlesFeed.description
