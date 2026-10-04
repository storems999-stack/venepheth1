"""
Regression tests for bugs found in the 2026-09-30 full-app audit.

Each test pins a defect that shipped: wrong model field names in templates,
fabricated homepage stat fallbacks, and inline handlers blocked by CSP.
"""

from django.test import TestCase
from django.urls import reverse

from tests.factories import CourseFactory, PublicationFactory, ResearchProjectFactory


class TestCvPrintUsesRealModelFields(TestCase):
    """cv_print.html referenced funding_agency/journal/conference — none exist
    on the models, so funding and every venue line rendered empty."""

    @classmethod
    def setUpTestData(cls):
        from apps.profiles.models import Profile
        from apps.research.models import ResearchProject

        cls.profile = Profile.objects.create(full_name="CV Auditor")
        cls.project = ResearchProjectFactory.create(title="Funded Project")
        # The factory ignores unknown kwargs — set the audited field directly.
        ResearchProject.objects.filter(pk=cls.project.pk).update(funding_source="National Research Council")
        cls.pub = PublicationFactory.create(
            title="A Paper",
            journal_name="Journal of Testing",
            year=2025,
        )

    def test_cv_shows_funding_source(self):
        resp = self.client.get(reverse("profiles:cv_print"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "National Research Council")

    def test_cv_shows_journal_name(self):
        resp = self.client.get(reverse("profiles:cv_print"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Journal of Testing")


class TestHomepageStatsAreNotFabricated(TestCase):
    """`{{ stats.x|default:"10" }}` fired on 0, so an empty site advertised
    "10+ Courses". The view always supplies the real counts."""

    def test_zero_counts_render_zero_not_placeholder(self):
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertNotIn(">10+<", html)
        self.assertNotIn(">20+<", html)
        self.assertNotIn(">5+<", html)

    def test_real_counts_render(self):
        CourseFactory.create()
        resp = self.client.get(reverse("core:home"))
        self.assertContains(resp, ">1<")


class TestCspSafeFilters(TestCase):
    """Filter dropdowns used inline onchange, which the CSP header bans."""

    def test_no_inline_event_handlers_in_templates(self):
        from pathlib import Path

        offenders = []
        for path in Path("templates").rglob("*.html"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for attr in ("onchange=", "onclick=", "onsubmit=", "onload=", "onerror="):
                if attr in text:
                    offenders.append(f"{path}: {attr}")
        self.assertEqual(offenders, [], "inline handlers are blocked by CSP")

    def test_publications_filter_is_a_get_form(self):
        resp = self.client.get(reverse("publications:list"), {"year": "2025"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "data-auto-submit-form")

    def test_resources_filter_is_a_get_form(self):
        resp = self.client.get(reverse("resources:list"), {"type": "pdf"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "data-auto-submit-form")
        self.assertContains(resp, 'name="category"')


class TestTemplateCommentsDoNotLeak(TestCase):
    """Django's {# #} is single-line only — a multi-line one renders as literal
    text into the page, which shipped once on the widget and the CV."""

    def test_no_multiline_django_comments(self):
        import re
        from pathlib import Path

        offenders = []
        for path in Path("templates").rglob("*.html"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(r"\{#.*?#\}", text, re.DOTALL):
                if "\n" in match.group(0):
                    offenders.append(str(path))
                    break
        self.assertEqual(offenders, [], "multi-line {# #} renders as visible text")

    def test_comment_markers_absent_from_rendered_home(self):
        html = self.client.get(reverse("core:home")).content.decode()
        self.assertNotIn("{#", html)
        self.assertNotIn("#}", html)


class TestStaticAssetsAreShipped(TestCase):
    """.gitignore used to ignore static/ wholesale, so site.js,
    tailwind-config.js and assistant.js were missing from every fresh clone —
    the site loaded with no JS and no Tailwind theme."""

    REQUIRED_JS = ("static/js/site.js", "static/js/tailwind-config.js", "static/js/assistant.js")

    def test_required_js_exists(self):
        from pathlib import Path

        for rel in self.REQUIRED_JS:
            self.assertTrue(Path(rel).exists(), f"{rel} missing")

    def test_static_dir_is_not_gitignored(self):
        from pathlib import Path

        patterns = [
            line.strip()
            for line in Path(".gitignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        self.assertNotIn("static/", patterns, "static/ holds source assets and must be tracked")
        self.assertIn("staticfiles/", patterns, "only the collectstatic output should be ignored")

    def test_every_static_reference_in_templates_exists(self):
        import re
        from pathlib import Path

        missing = []
        for template in Path("templates").rglob("*.html"):
            text = template.read_text(encoding="utf-8", errors="ignore")
            for ref in re.findall(r"\{%\s*static\s+['\"]([^'\"]+)['\"]", text):
                if not (Path("static") / ref).exists():
                    missing.append(f"{template} -> {ref}")
        self.assertEqual(missing, [], "templates reference missing static files")


class TestScriptTagsAreWellFormed(TestCase):
    """An unterminated <script src=...> makes the HTML parser swallow the next
    script element as text. The site.js tag shipped without a closing tag, so
    assistant.js was never created and the whole AI widget stayed inert — while
    every HTML validator-lite check and the full test suite passed."""

    def test_every_script_tag_is_closed(self):
        """Parse the rendered page the way a browser would and count scripts."""
        from html.parser import HTMLParser

        class ScriptCounter(HTMLParser):
            def __init__(self):
                super().__init__()
                self.opened = []
                self.srcs = []
                self.inside = False

            def handle_starttag(self, tag, attrs):
                if tag == "script":
                    self.opened.append(dict(attrs))
                    self.inside = True

            def handle_endtag(self, tag):
                if tag == "script":
                    self.inside = False

            def handle_data(self, data):
                # Text found while a script element is open but never closed.
                if self.inside and "<script" in data:
                    self.srcs.append(data.strip()[:80])

        for url in ("/", "/assistant/", "/courses/"):
            html = self.client.get(url).content.decode()
            parser = ScriptCounter()
            parser.feed(html)
            self.assertEqual(parser.srcs, [], f"{url}: a <script> tag is missing its </script>")

    def test_assistant_js_script_element_exists(self):
        """Regression: the tag was in the source but not in the DOM."""
        html = self.client.get("/").content.decode()
        self.assertIn('<script src="/static/js/assistant.js" defer></script>', html)
        self.assertIn('<script src="/static/js/site.js" defer></script>', html)

    def test_cv_print_has_no_inline_script(self):
        """The print handler moved to site.js; an inline block is CSP-blocked."""
        html = self.client.get(reverse("profiles:cv_print")).content.decode()
        self.assertNotIn("<script nonce", html)
        self.assertIn('src="/static/js/site.js"', html)


class TestAssistantUiIsVanillaJs(TestCase):
    """The chat page and widget were Alpine.js components, but Alpine is not
    loaded anywhere (project banned it for CSP) — the whole AI UI was inert.
    They must ship data-* hooks driven by static/js/assistant.js instead."""

    def test_chat_page_has_no_alpine_directives(self):
        resp = self.client.get(reverse("assistant:chat"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        for attr in ("x-data=", "x-show=", "x-model=", "@click=", "@submit"):
            self.assertNotIn(attr, html, f"{attr} requires Alpine.js, which is not loaded")

    def test_chat_page_has_vanilla_hooks(self):
        html = self.client.get(reverse("assistant:chat")).content.decode()
        for hook in ("data-assistant-form", "data-assistant-input", "data-assistant-send", "data-assistant-avatar"):
            self.assertIn(hook, html)

    def test_widget_has_vanilla_hooks(self):
        html = self.client.get(reverse("core:home")).content.decode()
        for hook in ("data-assistant-widget", "data-assistant-widget-toggle", "data-assistant-widget-form"):
            self.assertIn(hook, html)

    def test_assistant_js_is_loaded_on_every_page(self):
        html = self.client.get(reverse("core:home")).content.decode()
        self.assertIn("js/assistant.js", html)

    def test_assistant_js_exists_on_disk(self):
        from pathlib import Path

        js = Path("static/js/assistant.js")
        self.assertTrue(js.exists())
        text = js.read_text(encoding="utf-8")
        # No eval and no framework bootstrap — the CSP bans both.
        self.assertNotIn("eval(", text)
        for marker in ("x-data", "Alpine.start", "new Function("):
            self.assertNotIn(marker, text)
