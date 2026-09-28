"""
Tests for Internationalization (i18n) and Lao Language Support.
"""

from django.test import TestCase
from django.urls import reverse
from django.utils.translation import activate
from django.utils.translation import gettext as _


class LaoInternationalizationTests(TestCase):
    """Tests verifying Lao locale translation and language switcher."""

    def test_gettext_lao_translation(self):
        """Verify that gettext returns Lao translations when 'lo' locale is active."""
        activate("lo")
        self.assertEqual(_("Home"), "ໜ້າຫຼັກ")
        self.assertEqual(_("Courses"), "ວິຊາຮຽນ")
        self.assertEqual(_("Teaching"), "ການສິດສອນ")
        self.assertEqual(_("Contact"), "ຕິດຕໍ່")
        self.assertEqual(_("Research"), "ການຄົ້ນຄ້ວາ")
        self.assertEqual(_("Publications"), "ສິ່ງຕີພິມ")
        self.assertEqual(_("Academic Leader"), "ຜູ້ນໍາທາງວິຊາການ")

    def test_gettext_english_translation(self):
        """Verify that gettext returns English when 'en' locale is active."""
        activate("en")
        self.assertEqual(_("Home"), "Home")
        self.assertEqual(_("Courses"), "Courses")
        self.assertEqual(_("Teaching"), "Teaching")
        self.assertEqual(_("Contact"), "Contact")

    def test_home_page_renders_english_by_default(self):
        """Verify default language on home page is English."""
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Courses", content)
        self.assertIn("Teaching", content)

    def test_home_page_renders_lao_when_cookie_set(self):
        """Verify home page renders in Lao when django_language cookie is set to 'lo'."""
        self.client.cookies.load({"django_language": "lo"})
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # Check translated navbar terms
        self.assertIn("ໜ້າຫຼັກ", content)
        self.assertIn("ວິຊາຮຽນ", content)
        self.assertIn("ການສິດສອນ", content)
        self.assertIn("ຕິດຕໍ່", content)

    def test_set_language_endpoint_switches_to_lao(self):
        """Verify posting to set_language switches language to Lao."""
        response = self.client.post(
            reverse("set_language"),
            {"language": "lo", "next": reverse("core:home")},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.cookies.get("django_language").value, "lo")

        # Following redirect to home page should show Lao text
        home_resp = self.client.get(reverse("core:home"))
        content = home_resp.content.decode("utf-8")
        self.assertIn("ໜ້າຫຼັກ", content)
        self.assertIn("ວິຊາຮຽນ", content)

    def test_set_language_endpoint_switches_back_to_english(self):
        """Verify posting to set_language switches language back to English."""
        self.client.cookies.load({"django_language": "lo"})
        response = self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("core:home")},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.cookies.get("django_language").value, "en")

        home_resp = self.client.get(reverse("core:home"))
        content = home_resp.content.decode("utf-8")
        self.assertIn("Courses", content)
