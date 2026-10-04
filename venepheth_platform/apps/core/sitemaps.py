"""Sitemap classes for core/static pages."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.blog.models import Article
from apps.courses.models import Course
from apps.research.models import Publication, ResearchProject
from apps.resources.models import Resource


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return ["core:home", "profiles:detail", "contact:form"]

    def location(self, item):
        return reverse(item)


class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Article.objects.filter(status="published")

    def lastmod(self, obj):
        return obj.updated_at


class ResearchProjectSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return ResearchProject.objects.filter(status="published")

    def lastmod(self, obj):
        return obj.updated_at


class CourseSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Course.objects.filter(status="published", visibility="public")

    def lastmod(self, obj):
        return obj.updated_at


class PublicationSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Publication.objects.filter(status="published")

    def lastmod(self, obj):
        return obj.updated_at


class ResourceSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Resource.objects.filter(visibility="public")

    def lastmod(self, obj):
        return obj.updated_at
