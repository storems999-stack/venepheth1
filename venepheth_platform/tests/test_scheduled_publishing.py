from datetime import timedelta
from importlib import import_module
from unittest.mock import Mock

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.blog.admin import ArticleAdmin
from apps.blog.admin import make_archived as archive_articles
from apps.blog.admin import make_draft as draft_articles
from apps.blog.admin import make_published as publish_articles
from apps.blog.models import Article
from apps.core.tasks import publish_scheduled_content
from apps.courses.admin import CourseAdmin
from apps.courses.models import Announcement, Course
from apps.research.admin import make_archived as archive_research
from apps.research.admin import make_published as publish_research
from apps.research.models import Publication, ResearchProject
from apps.teaching.models import StudentAnnouncement
from tests.factories import ArticleFactory, CourseFactory, PublicationFactory, ResearchProjectFactory


class ScheduledPublishingTests(TestCase):
    def test_scheduled_content_requires_a_release_time(self):
        article = ArticleFactory.create(status="scheduled")

        with self.assertRaises(ValidationError) as error:
            article.full_clean()

        self.assertIn("scheduled_at", error.exception.message_dict)

    def test_published_content_records_publication_time_on_save(self):
        course = CourseFactory.create()
        published_items = [
            ArticleFactory.create(status="published"),
            CourseFactory.create(status="published"),
            PublicationFactory.create(status="published"),
            ResearchProjectFactory.create(status="published"),
            Announcement.objects.create(
                course=course,
                title="Course announcement",
                content="Details",
                status="published",
            ),
            StudentAnnouncement.objects.create(
                title="Student announcement",
                body="Details",
                status="published",
            ),
        ]

        for item in published_items:
            with self.subTest(model=type(item).__name__):
                self.assertIsNotNone(item.published_at)

    def test_publish_timestamp_is_saved_when_update_fields_is_limited(self):
        article = ArticleFactory.create(status="draft")
        article.status = "published"
        article.save(update_fields=["status"])

        article.refresh_from_db()
        self.assertEqual(article.status, "published")
        self.assertIsNotNone(article.published_at)

    def test_publish_with_generator_update_fields_saves_all_fields_and_timestamp(self):
        article = ArticleFactory.create(status="draft")
        article.title = "Generator save"
        article.status = "published"
        article.save(update_fields=(field for field in ("title", "status")))

        article.refresh_from_db()
        self.assertEqual(article.title, "Generator save")
        self.assertEqual(article.status, "published")
        self.assertIsNotNone(article.published_at)

    def test_scheduled_publish_is_recorded_in_content_history(self):
        due_at = timezone.now() - timedelta(minutes=2)
        article = ArticleFactory.create(status="scheduled")
        article.scheduled_at = due_at
        article.save(update_fields=["scheduled_at"])
        history_count_before = article.history.count()

        publish_scheduled_content.apply().get()

        self.assertEqual(article.history.count(), history_count_before + 1)
        latest_history = article.history.first()
        self.assertEqual(latest_history.status, "published")
        self.assertEqual(latest_history.published_at, due_at)

    def test_blog_and_research_bulk_actions_create_history(self):
        actions = (
            (ArticleFactory.create(status="draft"), publish_articles),
            (ArticleFactory.create(status="published"), archive_articles),
            (ArticleFactory.create(status="published"), draft_articles),
            (ResearchProjectFactory.create(status="draft"), publish_research),
            (ResearchProjectFactory.create(status="published"), archive_research),
            (PublicationFactory.create(status="draft"), publish_research),
        )

        for item, action in actions:
            with self.subTest(model=type(item).__name__, action=action.__name__):
                history_count_before = item.history.count()
                updated_at_before = item.updated_at
                action(Mock(), None, type(item).objects.filter(pk=item.pk))
                item.refresh_from_db()
                self.assertEqual(item.history.count(), history_count_before + 1)
                self.assertGreater(item.updated_at, updated_at_before)

    def test_due_items_publish_across_content_types_but_future_items_wait(self):
        due_at = timezone.now() - timedelta(minutes=2)
        future_at = timezone.now() + timedelta(hours=1)
        scheduled_models = (
            (Article, ArticleFactory.create),
            (Course, CourseFactory.create),
            (Publication, PublicationFactory.create),
            (ResearchProject, ResearchProjectFactory.create),
        )
        due_items = []
        future_items = []

        for model, factory in scheduled_models:
            due_item = factory(status="scheduled")
            due_item.scheduled_at = due_at
            due_item.save(update_fields=["scheduled_at"])
            due_items.append(due_item)
            future_item = factory(status="scheduled")
            future_item.scheduled_at = future_at
            future_item.save(update_fields=["scheduled_at"])
            future_items.append(future_item)

        course = CourseFactory.create()
        due_items.append(
            Announcement.objects.create(
                course=course,
                title="Due course announcement",
                content="Details",
                status="scheduled",
                scheduled_at=due_at,
            )
        )
        future_items.append(
            Announcement.objects.create(
                course=course,
                title="Future course announcement",
                content="Details",
                status="scheduled",
                scheduled_at=future_at,
            )
        )
        due_items.append(
            StudentAnnouncement.objects.create(
                title="Due student announcement",
                body="Details",
                status="scheduled",
                scheduled_at=due_at,
            )
        )
        future_items.append(
            StudentAnnouncement.objects.create(
                title="Future student announcement",
                body="Details",
                status="scheduled",
                scheduled_at=future_at,
            )
        )

        result = publish_scheduled_content.apply().get()

        self.assertEqual(result, len(due_items))
        for item in due_items:
            item.refresh_from_db()
            self.assertEqual(item.status, "published")
            self.assertEqual(item.published_at, due_at)
        for item in future_items:
            item.refresh_from_db()
            self.assertEqual(item.status, "scheduled")
            self.assertIsNone(item.published_at)

    def test_celery_beat_schedule_is_installed(self):
        from django.apps import apps as django_apps
        from django_celery_beat.models import IntervalSchedule, PeriodicTask

        migration = import_module("apps.core.migrations.0002_schedule_content_publishing")
        migration.create_scheduled_publishing_task(django_apps, schema_editor=None)
        task = PeriodicTask.objects.get(name="Publish Scheduled Content")
        self.assertEqual(task.task, "apps.core.tasks.publish_scheduled_content")
        self.assertTrue(task.enabled)
        self.assertEqual(task.interval.every, 1)
        self.assertEqual(task.interval.period, IntervalSchedule.MINUTES)

    def test_admin_forms_expose_schedule_time(self):
        article_admin = ArticleAdmin(Article, admin.site)
        course_admin = CourseAdmin(Course, admin.site)
        article_fields = {field for _, fieldset in article_admin.get_fieldsets(None) for field in fieldset["fields"]}
        course_fields = {field for _, fieldset in course_admin.get_fieldsets(None) for field in fieldset["fields"]}

        self.assertIn("scheduled_at", article_fields)
        self.assertIn("scheduled_at", course_fields)
