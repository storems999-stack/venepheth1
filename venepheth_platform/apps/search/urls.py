"""Search app URL configuration."""

from django.urls import path

from . import views

app_name = "search"

urlpatterns = [
    path("", views.search_results, name="results"),
    path("topics/", views.knowledge_graph_view, name="knowledge_graph"),
    path("topics/<str:topic_name>/", views.topic_detail_view, name="topic_detail"),
]
