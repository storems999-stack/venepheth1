"""
Regression tests for defects found by simulating a fresh clone and building the
real image. These bugs only appear when the local working copy cannot paper
over them, so nothing in the app suite caught them.
"""

from pathlib import Path

from django.test import TestCase

ROOT = Path(__file__).resolve().parent.parent


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")


class TestSuiteDoesNotDependOnGitignoredFiles(TestCase):
    """`test_encrypted_backup_roundtrip` relied on <BASE_DIR>/backup_key.bin,
    which is git-ignored. It passed on the developer's machine and failed on
    every fresh clone and in CI."""

    def test_backup_key_is_gitignored(self):
        entries = {line.strip() for line in read(".gitignore").splitlines() if line.strip()}
        self.assertIn("backup_key.bin", entries)

    def test_encrypted_backup_test_provisions_its_own_key(self):
        source = read("tests/test_additional.py")
        self.assertIn("BACKUP_ENCRYPTION_KEY", source)
        # The key must be generated in the test, never read from disk.
        self.assertIn("Fernet.generate_key()", source)
        # And the decrypt step must reuse that same key.
        self.assertIn("Fernet(key.encode()).decrypt", source)


class TestRequirementsAreInstallableTogether(TestCase):
    """`fido2<2.0.0` pins cryptography<45, which made the production image fail
    to build once cryptography was bumped for its CVEs. The build died with
    ResolutionImpossible at `pip install /wheels/*`."""

    def test_fido2_pin_allows_patched_cryptography(self):
        base = read("requirements/base.txt")
        self.assertIn("fido2>=2.0.0,<3.0.0", base)
        self.assertNotIn("fido2<2.0.0", base, "1.x caps cryptography<45 and breaks the build")

    def test_cryptography_pin_is_present(self):
        self.assertIn("cryptography==", read("requirements/base.txt"))


class TestNginxConfigIsValid(TestCase):
    """Changes to nginx.prod.conf are only checked by `nginx -t` inside the
    image; a broken upstream block stops the container from starting."""

    def test_resolve_requires_a_zone(self):
        """`server web:8000 resolve;` without `zone` is a hard startup error:
        "resolving names at run time requires upstream ... to be in shared memory"."""
        conf = read("docker/nginx/nginx.prod.conf")
        self.assertIn("resolve;", conf)
        self.assertIn("zone django_app", conf)

    def test_embedded_dns_resolver_is_declared(self):
        self.assertIn("resolver 127.0.0.11", read("docker/nginx/nginx.prod.conf"))

    def test_no_deprecated_listen_http2(self):
        """nginx 1.25+ deprecates `listen 443 ssl http2`; removed in 1.29."""
        conf = read("docker/nginx/nginx.prod.conf")
        self.assertNotIn("listen 443 ssl http2", conf)
        self.assertIn("http2 on;", conf)


class TestMonitoringConfigIsShipped(TestCase):
    """docker-compose mounted ./docker/grafana/provisioning, which did not
    exist, so Grafana started with no datasource."""

    def test_provisioning_datasources_exist(self):
        self.assertTrue((ROOT / "docker/grafana/provisioning/datasources/prometheus.yml").exists())

    def test_compose_mount_matches_a_real_directory(self):
        compose = read("docker-compose.yml")
        self.assertIn("./docker/grafana/provisioning", compose)
        for mount in (
            "./docker/nginx/nginx.prod.conf",
            "./docker/nginx/nginx.dev.conf",
            "./docker/postgres/init.sql",
            "./docker/prometheus/prometheus.yml",
        ):
            self.assertTrue((ROOT / mount[2:]).exists(), f"compose mounts {mount} but it does not exist")


class TestComposeFilesAreValid(TestCase):
    def test_image_is_resolvable(self):
        """The deploy workflow exports VENEPHETH_IMAGE; compose must accept it
        or the server pulls a tag CI never published."""
        self.assertIn("VENEPHETH_IMAGE", read("docker-compose.prod.yml"))

    def test_env_examples_are_tracked(self):
        self.assertTrue((ROOT / ".env.example").exists())
        self.assertTrue((ROOT / ".env.prod.example").exists())
