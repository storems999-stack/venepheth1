"""
Regression tests for defects found by running the suite against real
PostgreSQL and by regenerating the translation catalogue with real gettext.
"""

from pathlib import Path

from django.test import TestCase

ROOT = Path(__file__).resolve().parent.parent
PO = ROOT / "locale/lo/LC_MESSAGES/django.po"
MO = ROOT / "locale/lo/LC_MESSAGES/django.mo"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")


def catalog():
    """Parse the catalogue with polib so multi-line msgids are handled."""
    import polib

    return polib.pofile(str(PO))


class TestPostgresSettingsAreUsable(TestCase):
    """The suite had only ever run on SQLite. A temporary settings module
    proved 319 tests also pass on PostgreSQL 16, so the gap is closable —
    but the module must not be left behind."""

    def test_no_stray_pgtest_settings_module(self):
        self.assertFalse(
            (ROOT / "config/settings/pgtest.py").exists(),
            "temporary PostgreSQL test settings must not be committed",
        )

    def test_testing_settings_still_use_sqlite(self):
        """The default fast path stays in-memory SQLite for speed."""
        self.assertIn('"NAME": ":memory:"', read("config/settings/testing.py"))


class TestTranslationCatalogueIsWellFormed(TestCase):
    """The hand-maintained .po had duplicate msgids — msgmerge reported
    "2 fatal errors" — plus an invalid `nplurals=INTEGER` plural header."""

    def test_no_duplicate_msgids(self):
        ids = [e.msgid for e in catalog() if e.msgid]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        self.assertEqual(duplicates, [], f"duplicate msgids: {duplicates[:5]}")

    def test_plural_forms_header_is_valid(self):
        """`nplurals=INTEGER; plural=EXPRESSION;` is the unedited gettext
        template; msgfmt rejects it as a fatal error."""
        forms = catalog().metadata.get("Plural-Forms", "")
        self.assertNotIn("INTEGER", forms)
        self.assertNotIn("EXPRESSION", forms)
        self.assertIn("nplurals=1", forms, "Lao uses a single plural form")

    def test_header_has_no_unedited_placeholders(self):
        metadata = catalog().metadata
        for key, placeholder in (
            ("Project-Id-Version", "PACKAGE VERSION"),
            ("Last-Translator", "FULL NAME"),
            ("Language-Team", "LANGUAGE <"),
            ("PO-Revision-Date", "YEAR-MO-DA"),
        ):
            self.assertNotIn(placeholder, metadata.get(key, ""), f"unfinished header: {key}")

    def test_catalogue_covers_the_source(self):
        """A catalogue smaller than the real string count means much of the UI
        silently falls back to English."""
        ids = {e.msgid for e in catalog() if e.msgid}
        self.assertGreater(len(ids), 500, f"only {len(ids)} msgids — catalogue is incomplete")

    def test_source_references_are_recorded(self):
        """makemessages records where each string lives; hand-written entries
        had none, so nothing could be traced back to its template."""
        without_refs = [e.msgid for e in catalog() if e.msgid and not e.occurrences]
        self.assertEqual(without_refs, [], f"{len(without_refs)} entries have no source reference")

    def test_compiled_mo_carries_every_translation(self):
        """msgfmt legitimately omits entries with an empty msgstr, so the
        invariant is that every *translated* .po entry reaches the .mo."""
        self.assertTrue(MO.exists(), "django.mo missing — run compilemessages")
        import gettext

        with open(MO, "rb") as fh:
            mo = gettext.GNUTranslations(fh)
        mo_ids = set(mo._catalog) - {""}

        translated = {e.msgid for e in catalog() if e.msgid and e.msgstr}
        # Plural entries are keyed in the .mo by the singular msgid.
        missing = {i for i in translated - mo_ids if not any(i.startswith(p) for p in mo_ids)}
        self.assertEqual(missing, set(), f".mo is stale, missing {len(missing)} translations")
        self.assertTrue(translated, "no translations at all")

    def test_translations_actually_load(self):
        from django.utils import translation
        from django.utils.translation import gettext

        with translation.override("lo"):
            for s in ("AI Assistant", "Knowledge Base", "Office Hours", "Courses"):
                self.assertNotEqual(gettext(s), s, f"{s!r} is not translated in .mo")


class TestUnwrappedStringsAreCalledOut(TestCase):
    """cv_print.html renders its section titles as raw HTML, so gettext never
    sees them and those titles can never be translated from that page."""

    def test_cv_print_has_no_trans_wrappers(self):
        cv = read("templates/profiles/cv_print.html")
        self.assertIn("Professional Experience", cv)
        self.assertNotIn("{% trans", cv)
        self.assertNotIn("{% blocktrans", cv)
