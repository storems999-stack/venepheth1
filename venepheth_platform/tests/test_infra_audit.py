"""
Regression tests for defects found in the 2026-09-30 infrastructure/infra
audit. These files are not exercised by the app test suite, so each test pins
one deploy- or restore-level bug.
"""

import re
from pathlib import Path

from django.test import TestCase
from django.urls import reverse

ROOT = Path(__file__).resolve().parent.parent


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")


def staff_user(email: str, *, role=None, with_mfa: bool = False):
    """A staff account that can actually reach the view under test.

    Two gates stand in the way: SecurityEnforcementMiddleware 302s any user
    with require_mfa=True to allauth's 2FA setup, and the accounts post_save
    signal force-enables require_mfa for admin/lecturer roles. So privileged
    roles also need an enrolled Authenticator row (see `with_mfa`).
    """
    from django.contrib.auth import get_user_model

    role_model = get_user_model()
    user = role_model.objects.create_user(email=email, password="SecurePass123!", is_staff=True)
    updates = {"require_mfa": False, "must_change_password": False}
    if role is not None:
        updates["role"] = role
    for field, value in updates.items():
        setattr(user, field, value)
    user.save(update_fields=list(updates))
    if with_mfa:
        from allauth.mfa.models import Authenticator

        Authenticator.objects.create(user=user, type=Authenticator.Type.TOTP, data={"secret": "test", "label": "test"})
    return user


class TestDockerBuildDoesNotLeakSecrets(TestCase):
    """`COPY . .` with no .dockerignore baked .env, backup_key.bin and both
    virtualenvs into the image, and CI pushes those layers to GHCR."""

    def test_dockerignore_exists(self):
        self.assertTrue((ROOT / ".dockerignore").exists())

    def test_dockerignore_excludes_secrets(self):
        patterns = {
            line.strip()
            for line in read(".dockerignore").splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        for required in (".env", "backup_key.bin", "*.sqlite3", "venv/", ".venv/"):
            self.assertIn(required, patterns, f"{required} must never enter the image")

    def test_dockerignore_keeps_env_examples(self):
        lines = read(".dockerignore").splitlines()
        self.assertIn("!.env.example", lines)
        self.assertIn("!.env.prod.example", lines)

    def test_dockerfile_has_postgres_client(self):
        """pg_dump/pg_restore are used by backup_platform/restore_platform."""
        dockerfile = read("Dockerfile")
        self.assertIn("postgresql-client", dockerfile)


class TestNginxCspAllowsFrontendCdn(TestCase):
    """Django emits its own CSP; the browser enforces the intersection of both.
    nginx's script-src omitted cdn.tailwindcss.com and unpkg.com, so Tailwind,
    HTMX and Lucide were blocked in production — unstyled, non-interactive."""

    def test_nginx_csp_is_superset_of_django_csp(self):
        nginx = read("docker/nginx/nginx.prod.conf")
        match = re.search(r'script-src ([^"]+)', nginx)
        self.assertIsNotNone(match, "nginx.prod.conf sets no script-src")
        nginx_sources = match.group(1)

        # CDNs the templates actually load.
        base = read("templates/base.html")
        for cdn in ("cdn.tailwindcss.com", "unpkg.com"):
            self.assertIn(cdn, base, f"{cdn} should still be used by base.html")
            self.assertIn(cdn, nginx_sources, f"nginx CSP must allow {cdn}")


class TestLetsencryptDomainIsWired(TestCase):
    """init-letsencrypt.sh wrote certs for $DOMAIN while nginx.prod.conf
    hardcoded YOUR_DOMAIN, so nginx never found its certificate."""

    def test_init_script_requires_domain(self):
        script = read("docker/nginx/init-letsencrypt.sh")
        self.assertIn(': "${DOMAIN:?', script, "DOMAIN must be required, not hardcoded")
        self.assertIn("yourdomain.com", script.replace("admin@", ""), "usage example should exist")

    def test_init_script_substitutes_placeholder(self):
        script = read("docker/nginx/init-letsencrypt.sh")
        self.assertIn("YOUR_DOMAIN", script, "script must rewrite the nginx placeholder")

    def test_init_script_cd_to_project_root(self):
        script = read("docker/nginx/init-letsencrypt.sh")
        self.assertIn('cd "$(dirname "$0")', script)


class TestDeployWorkflowIsSound(TestCase):
    def test_deploy_pulls_the_image_ci_built(self):
        """CI pushes to ghcr.io; the old deploy pulled venepheth_platform:prod,
        which was never published, so the built artifact was never deployed."""
        deploy = read(".github/workflows/deploy.yml")
        self.assertIn("ghcr.io", deploy)
        self.assertIn("VENEPHETH_IMAGE", deploy)

    def test_compose_honours_the_deployed_image(self):
        compose = read("docker-compose.prod.yml")
        self.assertIn("VENEPHETH_IMAGE", compose, "compose must accept the pushed image tag")

    def test_certbot_runs_on_deploy_host(self):
        deploy = read(".github/workflows/deploy.yml")
        # It must be inside the ssh-action script block, not a runner `run:`.
        script_start = deploy.index("script: |")
        script_end = deploy.index("Notify on failure")
        ssh_block = deploy[script_start:script_end]
        self.assertIn("certbot renew", ssh_block)
        self.assertLess(script_start, deploy.index("certbot renew"))

    def test_health_check_can_actually_fail(self):
        """Port 80 answers 301 for every non-ACME path and curl -f does not
        treat 3xx as an error, so the old check could never fail a bad deploy."""
        deploy = read(".github/workflows/deploy.yml")
        self.assertNotIn("curl -f http://localhost/health/", deploy)
        self.assertIn("curl -fsS http://localhost:8000/health/", deploy)
        self.assertIn("healthy=0", deploy, "health result must gate the deploy")

    def test_wait_for_ci_actually_checks_ci(self):
        deploy = read(".github/workflows/deploy.yml")
        self.assertIn("gh run list", deploy)
        self.assertIn("workflow ci.yml", deploy)

    def test_deploy_script_is_strict(self):
        deploy = read(".github/workflows/deploy.yml")
        self.assertIn("set -euo pipefail", deploy)


class TestCiWorkflowIsSound(TestCase):
    def test_coverage_xml_generated_before_gate(self):
        """`set -e` meant a failing --fail-under skipped xml, leaving the
        upload step with no file."""
        ci = read(".github/workflows/ci.yml")
        self.assertLess(ci.index("coverage xml"), ci.index("coverage report --fail-under"))

    def test_migrations_checked_against_postgres(self):
        """config.settings.testing pins sqlite + DisableMigrations, so the old
        migrate step validated nothing and never touched the Postgres service."""
        ci = read(".github/workflows/ci.yml")
        self.assertIn("config.settings.development", ci)
        self.assertIn("makemigrations --check --dry-run", ci)


class TestRestoreIsAtomicAndCleansUp(TestCase):
    """flush + loaddata ran as two autocommit operations, so a mid-load
    failure left production empty — and the decrypted archive was never
    removed, leaving a plaintext DB dump on disk."""

    def test_flush_and_loaddata_are_atomic(self):
        source = read("apps/core/management/commands/restore_platform.py")
        self.assertIn("transaction.atomic()", source)

    def test_decrypted_archive_is_removed(self):
        source = read("apps/core/management/commands/restore_platform.py")
        self.assertIn("decrypted_path", source)
        self.assertIn("unlink()", source)

    def test_restore_script_cleans_up_and_cds(self):
        script = read("scripts/restore.sh")
        self.assertIn('cd "$(dirname "$0")', script)
        self.assertIn('rm -f "${ARCHIVE%.enc}"', script)

    def test_backup_script_cds_to_project_root(self):
        self.assertIn('cd "$(dirname "$0")', read("scripts/backup.sh"))


class TestRedisBrokerCarriesPassword(TestCase):
    """docker-compose starts redis with --requirepass, but a missing REDIS_URL
    fell back to redis://redis:6379/0 with no credentials, crash-looping the
    worker and scheduler."""

    def test_broker_reuses_the_resolved_redis_url(self):
        source = read("config/settings/base.py")
        self.assertIn("REDIS_PASSWORD = env(", source)
        self.assertIn("REDIS_URL = env(", source)
        # The broker must reuse the resolved value, not re-read REDIS_URL.
        self.assertIn("CELERY_BROKER_URL = REDIS_URL", source)

    def test_fallback_url_carries_the_password(self):
        """Import base settings in isolation: no .env file, only REDIS_PASSWORD.

        The module calls environ.Env.read_env(BASE_DIR / '.env'), so a developer's
        .env would otherwise inject its own REDIS_URL and the fallback branch
        would never be exercised.
        """
        import importlib
        import os
        import sys
        from unittest import mock

        saved = {k: os.environ.get(k) for k in ("REDIS_URL", "REDIS_PASSWORD")}
        os.environ.pop("REDIS_URL", None)
        for name in list(sys.modules):
            if name.startswith("config.settings"):
                del sys.modules[name]
        try:
            with mock.patch.dict(os.environ, {"REDIS_PASSWORD": "s3cret"}, clear=False):
                with mock.patch("environ.Env.read_env", lambda self, *a, **k: None):
                    settings_mod = importlib.import_module("config.settings.base")
                    self.assertIn(":s3cret@", settings_mod.REDIS_URL)
                    self.assertEqual(settings_mod.CELERY_BROKER_URL, settings_mod.REDIS_URL)
        finally:
            for name in list(sys.modules):
                if name.startswith("config.settings"):
                    del sys.modules[name]
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


class TestOfficeHoursWeekdayOrdering(TestCase):
    """Without weekday_ordering(), Meta.ordering=["start_time"] made the
    assistant answer with the earliest clock times instead of the first days."""

    def test_overview_is_monday_first(self):
        import datetime

        from apps.assistant.services.retriever import AcademicRetriever
        from apps.teaching.models import OfficeHours

        OfficeHours.objects.all().delete()
        # Insert out of order: Friday 08:00, then Monday 17:00. Clock order
        # would put Friday first; weekday order must put Monday first.
        OfficeHours.objects.create(
            day=OfficeHours.Day.FRI, start_time=datetime.time(8, 0), end_time=datetime.time(9, 0)
        )
        OfficeHours.objects.create(
            day=OfficeHours.Day.MON, start_time=datetime.time(17, 0), end_time=datetime.time(18, 0)
        )
        results = AcademicRetriever.retrieve("", limit=5)
        titles = [r["title"] for r in results if r["type"] == "Office Hours"]
        self.assertTrue(titles, "expected office hours in the default overview")
        self.assertIn("Monday", titles[0])

    def test_matched_office_hours_are_weekday_ordered(self):
        import datetime

        from apps.assistant.services.retriever import AcademicRetriever
        from apps.teaching.models import OfficeHours

        OfficeHours.objects.all().delete()
        OfficeHours.objects.create(
            day=OfficeHours.Day.FRI,
            start_time=datetime.time(8, 0),
            end_time=datetime.time(9, 0),
            location="Zzz Room",
        )
        OfficeHours.objects.create(
            day=OfficeHours.Day.MON,
            start_time=datetime.time(17, 0),
            end_time=datetime.time(18, 0),
            location="Zzz Room",
        )
        results = AcademicRetriever.retrieve("Zzz", limit=5)
        titles = [r["title"] for r in results if r["type"] == "Office Hours"]
        self.assertTrue(titles)
        self.assertIn("Monday", titles[0])


class TestDashboardCourseTotalIncludesAllStatuses(TestCase):
    """courses_total summed only published+draft, dropping scheduled and
    archived while the sibling tiles counted every row."""

    def test_total_counts_all_statuses(self):
        from apps.courses.models import Course
        from tests.factories import CourseFactory

        CourseFactory.create(status="published")
        CourseFactory.create(status="draft")
        CourseFactory.create(status="scheduled")
        CourseFactory.create(status="archived")
        self.assertEqual(Course.objects.count(), 4)

    def test_view_reports_full_total(self):
        from apps.courses.models import Course
        from tests.factories import CourseFactory

        CourseFactory.create(status="published")
        CourseFactory.create(status="draft")
        CourseFactory.create(status="scheduled")
        CourseFactory.create(status="archived")

        self.client.force_login(staff_user("dash-audit@test.com"))
        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["stats"]["courses_total"], Course.objects.count())


class TestUserListIsPaginated(TestCase):
    def test_user_list_paginates(self):
        from apps.accounts.models import CustomUser

        # user_list requires is_admin_or_above, so this user needs the ADMIN
        # role plus an enrolled authenticator: the accounts post_save signal
        # force-enables require_mfa for admins and the middleware would
        # otherwise 302 us to /accounts/2fa/ before the view runs.
        admin = staff_user("pager-audit@test.com", role=CustomUser.Role.ADMIN, with_mfa=True)
        self.client.force_login(admin)
        for i in range(30):
            CustomUser.objects.create_user(email=f"bulk{i}@example.com", password="SecurePass123!")

        resp = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(resp.status_code, 200)
        page_obj = resp.context["page_obj"]
        self.assertLessEqual(len(page_obj.object_list), 25)
        self.assertEqual(resp.context["total_users"], CustomUser.objects.count())


class TestDockerDevStackPostRequestsWork(TestCase):
    """Deployed via docker compose, every POST returned 403 "Origin checking
    failed": development.py overrode .env's CSRF_TRUSTED_ORIGINS with a list that
    omitted the compose ports, and Django's origin check compares host AND
    port. Contact form, login, AI chat and the language switch were all broken
    at http://localhost:8080."""

    def test_dev_settings_include_the_compose_ports(self):
        source = read("config/settings/development.py")
        for port in ("8080", "9080"):
            self.assertIn(f"http://localhost:{port}", source, f"port {port} must be trusted")

    def test_dev_settings_respect_the_env_var(self):
        """It used to hardcode the list, so CSRF_TRUSTED_ORIGINS in .env was
        silently ignored."""
        source = read("config/settings/development.py")
        self.assertIn("CSRF_TRUSTED_ORIGINS = _dev_env.list(", source)

    def test_nginx_health_location_sends_the_host_header(self):
        """Without proxy_set_header Host, nginx forwards the upstream name
        ("django"), which is not in ALLOWED_HOSTS, so /health/ answered 400
        through the proxy while returning 200 directly."""
        conf = read("docker/nginx/nginx.dev.conf")
        health_block = conf[conf.index("location /health/") :]
        self.assertIn("proxy_set_header Host $host;", health_block)


class TestSqliteDatabaseUrlWorks(TestCase):
    """base.py injected the libpq `connect_timeout` option unconditionally, so
    any SQLite DATABASE_URL crashed with "Connection() got an unexpected keyword
    argument 'connect_timeout'" — including base.py's own default."""

    def test_connect_timeout_only_for_postgres(self):
        source = read("config/settings/base.py")
        self.assertIn('if "postgresql" in DATABASES["default"]["ENGINE"]:', source)
        # The option must be inside that guard, not set unconditionally.
        self.assertNotIn(
            'DATABASES["default"]["OPTIONS"] = {"connect_timeout": 10}\n',
            source.replace('    DATABASES["default"]["OPTIONS"] = {"connect_timeout": 10}', "X"),
        )

    def test_sqlite_settings_load(self):
        from django.conf import settings

        self.assertIn("sqlite3", settings.DATABASES["default"]["ENGINE"])
        self.assertNotIn("connect_timeout", settings.DATABASES["default"].get("OPTIONS", {}))


class TestReindexCommandActuallyReindexes(TestCase):
    """An audit claimed saving inside .iterator() broke on PostgreSQL, which
    would make the command report "Re-indexed 0/N" forever. Verified against
    PostgreSQL 16 with 2500 documents: it works, because Django fetches in
    chunks of 2000. These tests therefore assert the behaviour that actually
    matters — every attached file ends up indexed — rather than pinning a
    defect that does not exist."""

    def _make(self, count, prefix):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.assistant.models import KnowledgeDocument

        made = []
        for i in range(count):
            doc = KnowledgeDocument(title=f"{prefix} {i}")
            doc.file.save(
                f"{prefix}-{i}.txt",
                SimpleUploadedFile(f"{prefix}-{i}.txt", f"payload {prefix} {i}".encode()),
                save=False,
            )
            doc.save()
            made.append(doc)
        # Simulate rows written before extraction existed.
        KnowledgeDocument.objects.filter(pk__in=[d.pk for d in made]).update(file_text="")
        return made

    def test_reindex_backfills_a_single_document(self):
        from django.core.management import call_command

        doc = self._make(1, "Iter")[0]
        call_command("reindex_knowledge")
        doc.refresh_from_db()
        self.assertIn("payload Iter 0", doc.file_text)

    def test_reindex_backfills_many_documents(self):
        """More rows than one query result, to catch any per-row skip."""
        from django.core.management import call_command

        from apps.assistant.models import KnowledgeDocument

        made = self._make(25, "Bulk")
        call_command("reindex_knowledge")
        remaining = KnowledgeDocument.objects.filter(pk__in=[d.pk for d in made], file_text="").count()
        self.assertEqual(remaining, 0, "every attached file must end up indexed")
        self.assertEqual(KnowledgeDocument.objects.filter(pk__in=[d.pk for d in made]).count(), 25)

    def test_reindex_does_not_n_plus_one(self):
        """Re-querying each pk would add one SELECT per document; keep it at a
        single queryset iteration."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        from django.core.management import call_command

        made = self._make(10, "Query")
        with CaptureQueriesContext(connection) as ctx:
            call_command("reindex_knowledge")
        # 10 UPDATEs + a little slack, not 10 extra SELECTs.
        self.assertLess(len(ctx.captured_queries), 30, f"queries: {len(ctx.captured_queries)}")
        selects = [q for q in ctx.captured_queries if q["sql"].lstrip().upper().startswith("SELECT")]
        self.assertLessEqual(len(selects), 3, f"unexpected SELECT fan-out: {selects}")
        self.assertTrue(made)


class TestSignalsDoNotSilentlySwallowFailures(TestCase):
    def test_login_failure_logging_uses_logger_exception(self):
        source = read("apps/accounts/signals.py")
        self.assertNotIn("    except Exception:\n        pass", source)
        self.assertIn("logger.exception", source)

    def test_audit_object_metadata_failure_is_logged(self):
        source = read("apps/audit/models.py")
        self.assertIn("could not resolve object", source)

    def test_resource_hash_failure_includes_traceback(self):
        source = read("apps/resources/models.py")
        self.assertIn("exc_info=True", source)
