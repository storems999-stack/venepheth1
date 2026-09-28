from django.contrib import admin

from .models import (
    AcademicInterest,
    Award,
    Certification,
    Education,
    Experience,
    Language,
    Membership,
    Profile,
)


class AcademicInterestInline(admin.TabularInline):
    model = AcademicInterest
    extra = 1


class EducationInline(admin.StackedInline):
    model = Education
    extra = 1


class ExperienceInline(admin.StackedInline):
    model = Experience
    extra = 1


class CertificationInline(admin.TabularInline):
    model = Certification
    extra = 1


class AwardInline(admin.TabularInline):
    model = Award
    extra = 1


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 1


class LanguageInline(admin.TabularInline):
    model = Language
    extra = 1


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "title", "email", "is_active")
    list_filter = ("is_active",)
    search_fields = ("full_name", "title", "email")
    inlines = [
        AcademicInterestInline,
        EducationInline,
        ExperienceInline,
        CertificationInline,
        AwardInline,
        MembershipInline,
        LanguageInline,
    ]
