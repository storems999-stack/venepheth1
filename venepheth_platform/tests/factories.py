"""
Model factories for testing using standard Django ORM.
Self-contained, fast, and does not require third-party factory libraries.
"""

from django.contrib.auth import get_user_model
from django.utils.text import slugify

from apps.blog.models import Article
from apps.courses.models import Course
from apps.research.models import Publication, ResearchProject

User = get_user_model()
_counter = 0


def _next_id():
    global _counter
    _counter += 1
    return _counter


class UserFactory:
    @classmethod
    def create(cls, **kwargs):
        cid = _next_id()
        email = kwargs.get("email", f"user{cid}@example.com")
        role = kwargs.get("role", User.Role.STUDENT)
        password = kwargs.get("password", "TestPass123456!")
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=kwargs.get("first_name", f"First{cid}"),
            last_name=kwargs.get("last_name", f"Last{cid}"),
            role=role,
            is_active=kwargs.get("is_active", True),
            is_staff=kwargs.get("is_staff", False),
            is_superuser=kwargs.get("is_superuser", False),
        )
        return user


class AdminUserFactory:
    @classmethod
    def create(cls, **kwargs):
        kwargs.setdefault("role", User.Role.ADMIN)
        kwargs.setdefault("is_staff", True)
        kwargs.setdefault("is_superuser", True)
        return UserFactory.create(**kwargs)


class LecturerUserFactory:
    @classmethod
    def create(cls, **kwargs):
        kwargs.setdefault("role", User.Role.LECTURER)
        kwargs.setdefault("is_staff", True)
        return UserFactory.create(**kwargs)


class CourseFactory:
    @classmethod
    def create(cls, **kwargs):
        cid = _next_id()
        code = kwargs.get("code", f"CS{100 + cid}")
        name = kwargs.get("name", f"Introduction to CS {cid}")
        slug = kwargs.get("slug", slugify(code))
        return Course.objects.create(
            code=code,
            name=name,
            slug=slug,
            description=kwargs.get("description", "A sample course description."),
            status=kwargs.get("status", "published"),
            credits=kwargs.get("credits", 3),
            level=kwargs.get("level", "undergraduate"),
        )


class ArticleFactory:
    @classmethod
    def create(cls, **kwargs):
        cid = _next_id()
        title = kwargs.get("title", f"Sample Article {cid}")
        slug = kwargs.get("slug", f"sample-article-{cid}")
        return Article.objects.create(
            title=title,
            slug=slug,
            content_raw=kwargs.get("content_raw", "<p>Sample article body content.</p>"),
            excerpt=kwargs.get("excerpt", "Summary of sample article."),
            status=kwargs.get("status", "published"),
        )


class ResearchProjectFactory:
    @classmethod
    def create(cls, **kwargs):
        cid = _next_id()
        title = kwargs.get("title", f"Research Project {cid}")
        slug = kwargs.get("slug", f"research-project-{cid}")
        return ResearchProject.objects.create(
            title=title,
            slug=slug,
            abstract=kwargs.get("abstract", "Sample research project abstract."),
            research_status=kwargs.get("research_status", "ongoing"),
            status=kwargs.get("status", "published"),
        )


class PublicationFactory:
    @classmethod
    def create(cls, **kwargs):
        cid = _next_id()
        title = kwargs.get("title", f"Publication {cid}")
        slug = kwargs.get("slug", f"publication-{cid}")
        return Publication.objects.create(
            title=title,
            slug=slug,
            abstract=kwargs.get("abstract", "Sample publication abstract."),
            publication_type=kwargs.get("publication_type", "journal"),
            authors=kwargs.get("authors", "Venepheth SAYAVONG"),
            year=kwargs.get("year", 2026),
            journal_name=kwargs.get("journal_name", "Journal of Advanced Computing"),
            status=kwargs.get("status", "published"),
        )
