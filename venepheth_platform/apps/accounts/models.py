"""
Custom User model with email-based auth and role-based access control.
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone as django_timezone
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """Manager for CustomUser model with email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", CustomUser.Role.SUPERADMIN)
        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True."))
        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model using email as the primary identifier.

    Roles:
        SUPERADMIN — Full system access
        ADMIN      — Platform administration
        LECTURER   — The platform owner
        EDITOR     — Content editing
        RESEARCHER — Research module access
        STUDENT    — Read-only academic content access
    """

    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", _("Super Admin")
        ADMIN = "admin", _("Admin")
        LECTURER = "lecturer", _("Lecturer")
        EDITOR = "editor", _("Editor")
        RESEARCHER = "researcher", _("Researcher")
        STUDENT = "student", _("Student")

    # ─── Identity Fields ────────────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)

    # ─── Role ───────────────────────────────────────────────────────────────────
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )

    # ─── Status ─────────────────────────────────────────────────────────────────
    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)
    email_verified = models.BooleanField(_("email verified"), default=False)

    # ─── Security ───────────────────────────────────────────────────────────────
    require_mfa = models.BooleanField(
        _("require MFA"),
        default=False,
        help_text=_("Force this user to set up MFA before accessing the system."),
    )
    last_login_ip = models.GenericIPAddressField(_("last login IP"), null=True, blank=True)
    password_changed_at = models.DateTimeField(_("password changed at"), null=True, blank=True)
    must_change_password = models.BooleanField(_("must change password"), default=False)

    # ─── Preferences ────────────────────────────────────────────────────────────
    language = models.CharField(_("language"), max_length=10, default="en")
    timezone = models.CharField(_("timezone"), max_length=50, default="Asia/Vientiane")

    # ─── Timestamps ─────────────────────────────────────────────────────────────
    date_joined = models.DateTimeField(_("date joined"), default=django_timezone.now)

    # ─── Meta ───────────────────────────────────────────────────────────────────
    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["email"]

    def __str__(self):
        return self.get_full_name() or self.email

    def get_full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email

    def get_short_name(self):
        return self.first_name or self.email.split("@")[0]

    # ─── Role Helpers ───────────────────────────────────────────────────────────
    @property
    def is_superadmin(self):
        return self.role == self.Role.SUPERADMIN

    @property
    def is_admin_or_above(self):
        return self.role in (self.Role.SUPERADMIN, self.Role.ADMIN)

    @property
    def is_lecturer(self):
        return self.role == self.Role.LECTURER

    @property
    def is_editor_or_above(self):
        return self.role in (
            self.Role.SUPERADMIN,
            self.Role.ADMIN,
            self.Role.LECTURER,
            self.Role.EDITOR,
        )

    @property
    def can_manage_research(self):
        return self.role in (
            self.Role.SUPERADMIN,
            self.Role.ADMIN,
            self.Role.LECTURER,
            self.Role.RESEARCHER,
        )

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.password_changed_at = django_timezone.now()
