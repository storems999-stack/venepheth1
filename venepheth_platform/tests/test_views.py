"""Unit and integration tests for public views and HTMX partials."""

from django.test import Client, TestCase
from django.urls import reverse

from apps.blog.models import Article, ArticleTag
from apps.courses.models import Course, CourseCategory
from apps.profiles.models import Profile
from apps.research.models import ResearchProject, ResearchTopic


class ViewTests(TestCase):
    """Test public-facing views and HTMX interactions."""

    def setUp(self):
        self.client = Client()

        # Active profile (public pages 404 without one)
        self.profile = Profile.objects.create(
            full_name="Venepheth SAYAVONG",
            title="Lecturer",
            is_active=True,
        )

        # Blog data
        self.tag = ArticleTag.objects.create(name="Economics", slug="economics")
        self.article = Article.objects.create(
            title="Introduction to Microeconomics",
            slug="intro-microeconomics",
            content_raw="<p>An introduction to economic theory.</p>",
            category=Article.Category.ACADEMIC,
            status=Article.Status.PUBLISHED,
        )
        self.article.tags.add(self.tag)

        self.draft_article = Article.objects.create(
            title="Draft Research Notes",
            slug="draft-research-notes",
            content_raw="<p>Work in progress.</p>",
            category=Article.Category.ARTICLE,
            status=Article.Status.DRAFT,
        )

        # Research data
        self.topic = ResearchTopic.objects.create(name="Macro Policy", slug="macro-policy")
        self.project = ResearchProject.objects.create(
            title="Sustainable Growth in Laos",
            slug="sustainable-growth-laos",
            abstract="Study on sustainable development indicators.",
            research_status=ResearchProject.ResearchStatus.ONGOING,
            status="published",
        )
        self.project.topics.add(self.topic)

        # Course data
        self.cat = CourseCategory.objects.create(name="Business", slug="business")
        self.course = Course.objects.create(
            name="Strategic Management",
            slug="strategic-management",
            code="MGT301",
            description="Core principles of business management.",
            category=self.cat,
            level="Undergraduate",
            visibility="public",
            status="published",
        )

    # ── Home ──────────────────────────────────────────────────────────────────

    def test_home_page_ok(self):
        """Home page returns 200."""
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    # ── Blog ──────────────────────────────────────────────────────────────────

    def test_blog_list_standard(self):
        """Blog list standard GET returns 200 and shows article."""
        response = self.client.get(reverse("blog:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)

    def test_blog_list_htmx_partial(self):
        """Blog list with HX-Request returns partial template only."""
        response = self.client.get(reverse("blog:list"), HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        # Should NOT contain the full navbar (base.html structure)
        self.assertNotContains(response, "<html")
        # Should contain article data
        self.assertContains(response, self.article.title)

    def test_blog_list_category_filter(self):
        """Category filter reduces to matching articles."""
        response = self.client.get(reverse("blog:list"), {"category": Article.Category.ACADEMIC})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)

    def test_blog_list_tag_filter(self):
        """Tag filter shows tagged articles."""
        response = self.client.get(reverse("blog:list"), {"tag": self.tag.slug})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)

    def test_blog_detail_published(self):
        """Detail view for a published article returns 200 and increments view_count."""
        url = reverse("blog:detail", kwargs={"slug": self.article.slug})
        initial_views = self.article.view_count
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)
        self.article.refresh_from_db()
        self.assertEqual(self.article.view_count, initial_views + 1)

    def test_blog_detail_draft_404(self):
        """Draft articles return 404 for unauthenticated visitors."""
        url = reverse("blog:detail", kwargs={"slug": self.draft_article.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    # ── Research ──────────────────────────────────────────────────────────────

    def test_research_list_standard(self):
        """Research list returns 200 and shows project."""
        response = self.client.get(reverse("research:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.title)

    def test_research_list_htmx_partial(self):
        """Research list with HX-Request returns partial HTML (no <html> tag)."""
        response = self.client.get(reverse("research:list"), HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<html")
        self.assertContains(response, self.project.title)

    def test_research_list_status_filter(self):
        """Status filter shows projects with matching research_status."""
        response = self.client.get(reverse("research:list"), {"status": "ongoing"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.title)

    def test_research_detail(self):
        """Research project detail page returns 200."""
        url = reverse("research:project_detail", kwargs={"slug": self.project.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.title)

    def test_research_publications_redirect(self):
        """Redirect from /research/publications/ to /publications/."""
        url = reverse("research:publications")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, reverse("publications:list"))

    # ── Courses ───────────────────────────────────────────────────────────────

    def test_courses_list_standard(self):
        """Courses list returns 200 and shows course."""
        response = self.client.get(reverse("courses:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.name)

    def test_courses_list_htmx_partial(self):
        """Courses list with HX-Request returns partial HTML (no <html> tag)."""
        response = self.client.get(reverse("courses:list"), HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<html")
        self.assertContains(response, self.course.name)

    def test_courses_list_level_filter(self):
        """Level filter shows courses matching that level."""
        response = self.client.get(reverse("courses:list"), {"level": "Undergraduate"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.name)

    def test_courses_detail(self):
        """Course detail page returns 200."""
        url = reverse("courses:detail", kwargs={"slug": self.course.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.name)

    # ── Search ────────────────────────────────────────────────────────────────

    def test_search_results_view(self):
        """Search view returns 200 for queries."""
        url = reverse("search:results")
        response = self.client.get(url, {"q": "Economics"})
        self.assertEqual(response.status_code, 200)

    def test_contact_form_get(self):
        """Contact form GET returns 200."""
        response = self.client.get(reverse("contact:form"))
        self.assertEqual(response.status_code, 200)

    # ── SEO & Feeds ───────────────────────────────────────────────────────────

    def test_sitemap_xml(self):
        """Sitemap XML returns 200 and contains URLs."""
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertContains(response, self.article.get_absolute_url())

    def test_robots_txt(self):
        """Robots.txt returns 200."""
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertContains(response, "Sitemap:")

    def test_rss_feed(self):
        """RSS Feed returns 200 and contains article."""
        response = self.client.get(reverse("blog:feed"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/rss+xml; charset=utf-8")
        self.assertContains(response, self.article.title)

    def test_atom_feed(self):
        """Atom Feed returns 200."""
        response = self.client.get(reverse("blog:feed_atom"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/atom+xml; charset=utf-8")

    # ── REST API & Schema ─────────────────────────────────────────────────────

    def test_api_schema(self):
        """OpenAPI schema generation returns 200."""
        response = self.client.get(reverse("api-schema"))
        self.assertEqual(response.status_code, 200)

    def test_api_swagger_docs(self):
        """Swagger UI returns 200."""
        response = self.client.get(reverse("api-docs"))
        self.assertEqual(response.status_code, 200)

    def test_api_redoc(self):
        """Redoc UI returns 200."""
        response = self.client.get(reverse("api-redoc"))
        self.assertEqual(response.status_code, 200)

    # ── Profile & CV & Error Views ───────────────────────────────────────────

    def test_profile_detail_view(self):
        """Profile detail view returns 200."""
        response = self.client.get(reverse("profiles:detail"))
        self.assertEqual(response.status_code, 200)

    def test_profile_cv_print_view(self):
        """Standalone CV print/PDF view returns 200."""
        response = self.client.get(reverse("profiles:cv_print"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Curriculum Vitae")

    def test_profile_detail_no_active_profile_404(self):
        """No active profile → 404 (not an empty 200 page)."""
        Profile.objects.all().delete()
        self.assertEqual(self.client.get(reverse("profiles:detail")).status_code, 404)
        self.assertEqual(self.client.get(reverse("profiles:cv_print")).status_code, 404)

    def test_error_503_view(self):
        """503 Service Unavailable view returns 503 status code."""
        response = self.client.get(reverse("core:error_503"))
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "503", status_code=503)

    # ── Academic Studio Dashboard Views ──────────────────────────────────────

    def test_dashboard_unauthenticated_redirects(self):
        """Unauthenticated visitor is redirected to login."""
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_dashboard_regular_user_redirects_home(self):
        """Non-staff user is redirected to home."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        student = User.objects.create_user(email="student@example.com", password="Password123!", is_staff=False)
        self.client.force_login(student)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("core:home"))

    def test_dashboard_staff_user_renders_studio(self):
        """Authenticated staff member accesses Academic Studio dashboard."""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff_user = User.objects.create_user(
            email="lecturer_test@example.com",
            password="SecurePassword123!",
            is_staff=True,
            first_name="Venepheth",
            last_name="SAYAVONG",
        )
        self.client.force_login(staff_user)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Academic Studio")
        self.assertIn("stats", response.context)
        self.assertIn("courses_total", response.context["stats"])
        self.assertIn("system_status", response.context)
