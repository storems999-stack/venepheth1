from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.blog.models import Article
from apps.courses.models import Course
from apps.profiles.models import Education, Experience, Profile
from apps.research.models import Publication, ResearchProject
from apps.resources.models import Resource


class ImportCvDataTests(TestCase):
    def setUp(self):
        self.profile = Profile.objects.create(
            full_name="Venepheth SAYAVONG",
            title="Lecturer & Researcher in Business Administration",
            email="venepheth@university.edu.la",
        )

        Education.objects.create(
            profile=self.profile,
            degree="Master of Business Administration (MBA)",
            field="Strategic Management",
            institution="Chiang Mai University",
            country="Thailand",
            year_start=2011,
            year_end=2013,
        )
        Experience.objects.create(
            profile=self.profile,
            position="Research Fellow",
            organization="ASEAN Business Research Network",
            year_start=2021,
            is_current=True,
        )
        Course.objects.create(
            code="BUS301", name="Strategic Management", slug="strategic-management", description="Demo"
        )
        Course.objects.create(code="REAL1", name="Manually added course", slug="manual-course", description="Keep")
        ResearchProject.objects.create(
            title="Digital Transformation of SMEs in Laos PDR: Barriers and Enablers",
            slug="digital-transformation-of-smes",
            abstract="Demo",
        )
        ResearchProject.objects.create(title="Manually added project", slug="manual-project", abstract="Keep")
        Publication.objects.create(
            title="Digital Transformation Readiness of SMEs: Evidence from Laos PDR",
            slug="demo-publication",
            publication_type="journal",
            authors="Sayavong, V.",
        )
        Article.objects.create(
            title="Why Digital Transformation Matters for SMEs in Laos",
            slug="demo-article",
            content_raw="<p>Demo</p>",
        )
        Article.objects.create(title="Manually added article", slug="manual-article", content_raw="<p>Keep</p>")
        Resource.objects.create(
            title="Lao SME Survey Dataset 2025",
            slug="demo-resource",
            external_url="https://example.com/dataset.csv",
        )
        Resource.objects.create(title="Manually added resource", slug="manual-resource")

    def test_imports_cv_verified_profile_courses_education_and_publications_idempotently(self):
        call_command("import_cv_data")
        call_command("import_cv_data")

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.title, "Lecturer & Academic Researcher")
        self.assertEqual(self.profile.email, "v.sayavong@nuol.edu.la")
        self.assertEqual(self.profile.website, "https://venepheth.online")
        self.assertEqual(Education.objects.filter(profile=self.profile).count(), 4)
        self.assertEqual(Experience.objects.filter(profile=self.profile).count(), 2)
        self.assertEqual(
            Publication.objects.filter(
                doi__in=[
                    "10.71026/ss.2025.01007",
                    "10.7176/EJBM/13-12-01",
                ]
            ).count(),
            2,
        )
        self.assertEqual(
            Publication.objects.filter(
                title__startswith="Organizational Culture and Organizational Commitment"
            ).count(),
            1,
        )
        self.assertEqual(
            Course.objects.filter(level="BBA", status=Course.Status.PUBLISHED).count(),
            4,
        )
        response = self.client.get(reverse("core:home"))
        for course_name in (
            "Total Quality Management",
            "Logistics and Supply Chain Management",
            "Project Management",
            "Management of Information System",
        ):
            self.assertContains(response, course_name)
        self.assertNotContains(response, "credits")

    def test_explicit_cleanup_removes_only_known_demo_records(self):
        call_command("import_cv_data", remove_demo_data=True)

        self.assertFalse(Course.objects.filter(code="BUS301").exists())
        self.assertTrue(Course.objects.filter(code="REAL1").exists())
        self.assertEqual(
            Course.objects.filter(level="BBA", status=Course.Status.PUBLISHED).count(),
            4,
        )
        self.assertFalse(ResearchProject.objects.filter(slug="digital-transformation-of-smes").exists())
        self.assertTrue(ResearchProject.objects.filter(slug="manual-project").exists())
        self.assertFalse(Article.objects.filter(slug="demo-article").exists())
        self.assertTrue(Article.objects.filter(slug="manual-article").exists())
        self.assertFalse(Resource.objects.filter(slug="demo-resource").exists())
        self.assertTrue(Resource.objects.filter(slug="manual-resource").exists())

        self.assertFalse(
            Education.objects.filter(
                profile=self.profile,
                institution="Chiang Mai University",
            ).exists()
        )
        self.assertEqual(
            Education.objects.filter(
                profile=self.profile,
                institution="Kasetsart University, Faculty of Management Sciences",
            ).count(),
            1,
        )
        self.assertEqual(
            Experience.objects.filter(
                profile=self.profile,
                position="Lecturer & Academic Researcher",
            ).count(),
            1,
        )
        self.assertEqual(Publication.objects.filter(doi="10.71026/ss.2025.01007").count(), 1)
