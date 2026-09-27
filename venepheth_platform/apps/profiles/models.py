"""
Profile and Academic CV models.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.core.file_security import validate_file_extension, validate_file_size, validate_file_mime


class Profile(TimeStampedModel):
    """Main profile of Venepheth SAYAVONG."""
    full_name = models.CharField(_("full name"), max_length=200)
    title = models.CharField(_("professional title"), max_length=200, blank=True)
    short_bio = models.TextField(_("short bio"), max_length=500, blank=True)
    bio = models.TextField(_("biography"), blank=True)
    photo = models.ImageField(
        _("photo"), upload_to="profile/", null=True, blank=True,
        validators=[validate_file_extension, validate_file_size, validate_file_mime],
    )
    email = models.EmailField(_("contact email"), blank=True)
    phone = models.CharField(_("phone"), max_length=50, blank=True)
    office = models.CharField(_("office location"), max_length=200, blank=True)
    website = models.URLField(_("website"), blank=True)
    orcid = models.CharField(_("ORCID"), max_length=50, blank=True)
    google_scholar_url = models.URLField(_("Google Scholar"), blank=True)
    researchgate_url = models.URLField(_("ResearchGate"), blank=True)
    linkedin_url = models.URLField(_("LinkedIn"), blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("profile")

    def __str__(self):
        return self.full_name


class AcademicInterest(TimeStampedModel):
    """Academic interests / expertise areas."""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="interests")
    name = models.CharField(_("interest"), max_length=200)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Education(TimeStampedModel):
    """Academic education history."""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="educations")
    degree = models.CharField(_("degree"), max_length=200)
    field = models.CharField(_("field of study"), max_length=200)
    institution = models.CharField(_("institution"), max_length=300)
    country = models.CharField(_("country"), max_length=100, blank=True)
    year_start = models.PositiveSmallIntegerField(_("start year"), null=True, blank=True)
    year_end = models.PositiveSmallIntegerField(_("end year"), null=True, blank=True)
    is_current = models.BooleanField(_("current"), default=False)
    description = models.TextField(_("description"), blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-year_end", "-year_start", "order"]

    def __str__(self):
        return f"{self.degree} — {self.institution}"


class Experience(TimeStampedModel):
    """Professional / academic experience."""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="experiences")
    position = models.CharField(_("position"), max_length=200)
    organization = models.CharField(_("organization"), max_length=300)
    department = models.CharField(_("department"), max_length=200, blank=True)
    country = models.CharField(_("country"), max_length=100, blank=True)
    year_start = models.PositiveSmallIntegerField(_("start year"), null=True, blank=True)
    year_end = models.PositiveSmallIntegerField(_("end year"), null=True, blank=True)
    is_current = models.BooleanField(_("current"), default=False)
    description = models.TextField(_("description"), blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-year_end", "-year_start"]

    def __str__(self):
        return f"{self.position} — {self.organization}"


class Certification(TimeStampedModel):
    """Professional certifications."""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(_("name"), max_length=200)
    issuer = models.CharField(_("issuer"), max_length=200)
    year = models.PositiveSmallIntegerField(_("year"), null=True, blank=True)
    expiry_year = models.PositiveSmallIntegerField(_("expiry year"), null=True, blank=True)
    credential_id = models.CharField(_("credential ID"), max_length=100, blank=True)
    credential_url = models.URLField(_("credential URL"), blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-year"]

    def __str__(self):
        return self.name


class Award(TimeStampedModel):
    """Academic awards and honors."""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="awards")
    name = models.CharField(_("award name"), max_length=200)
    organization = models.CharField(_("organization"), max_length=200, blank=True)
    year = models.PositiveSmallIntegerField(_("year"), null=True, blank=True)
    description = models.TextField(_("description"), blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-year"]

    def __str__(self):
        return self.name


class Membership(TimeStampedModel):
    """Professional memberships."""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="memberships")
    organization = models.CharField(_("organization"), max_length=200)
    role = models.CharField(_("role"), max_length=200, blank=True)
    year_start = models.PositiveSmallIntegerField(_("since"), null=True, blank=True)
    is_current = models.BooleanField(_("current"), default=True)
    website = models.URLField(_("website"), blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "organization"]

    def __str__(self):
        return self.organization


class Language(TimeStampedModel):
    """Languages spoken."""

    class Proficiency(models.TextChoices):
        NATIVE = "native", _("Native")
        FLUENT = "fluent", _("Fluent")
        ADVANCED = "advanced", _("Advanced")
        INTERMEDIATE = "intermediate", _("Intermediate")
        BASIC = "basic", _("Basic")

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="languages")
    name = models.CharField(_("language"), max_length=100)
    proficiency = models.CharField(_("proficiency"), max_length=20, choices=Proficiency.choices)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.name} ({self.proficiency})"
