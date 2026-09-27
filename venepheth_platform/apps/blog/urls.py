"""Blog app URL configuration."""
from django.urls import path
from . import views, feeds

app_name = "blog"

urlpatterns = [
    path("", views.article_list, name="list"),
    path("feed/", feeds.LatestArticlesFeed(), name="feed"),
    path("feed/atom/", feeds.AtomLatestArticlesFeed(), name="feed_atom"),
    path("<slug:slug>/", views.article_detail, name="detail"),
    path("tag/<slug:tag_slug>/", views.article_by_tag, name="by_tag"),
]
