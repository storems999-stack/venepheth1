"""
Forms for the accounts app — profile update, admin user creation.
Auth forms (login, signup, password reset) are handled by django-allauth.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

# Common timezone choices (abbreviated for brevity)
TIMEZONE_CHOICES = [
    ("Asia/Vientiane", "Asia/Vientiane (ICT, UTC+7)"),
    ("Asia/Bangkok", "Asia/Bangkok (ICT, UTC+7)"),
    ("Asia/Phnom_Penh", "Asia/Phnom_Penh (ICT, UTC+7)"),
    ("Asia/Ho_Chi_Minh", "Asia/Ho_Chi_Minh (ICT, UTC+7)"),
    ("Asia/Singapore", "Asia/Singapore (SGT, UTC+8)"),
    ("Asia/Tokyo", "Asia/Tokyo (JST, UTC+9)"),
    ("Europe/Paris", "Europe/Paris (CET/CEST)"),
    ("UTC", "UTC"),
]

LANGUAGE_CHOICES = [
    ("en", "English"),
    ("lo", "ພາສາລາວ"),
]


class ProfileUpdateForm(forms.ModelForm):
    """
    Allows an authenticated user to update their display name,
    preferred language, and timezone.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "language", "timezone"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": _("First name"),
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": _("Last name"),
                    "autocomplete": "family-name",
                }
            ),
            "language": forms.Select(
                choices=LANGUAGE_CHOICES,
                attrs={"class": "form-select"},
            ),
            "timezone": forms.Select(
                choices=TIMEZONE_CHOICES,
                attrs={"class": "form-select"},
            ),
        }
        labels = {
            "first_name": _("First Name"),
            "last_name": _("Last Name"),
            "language": _("Preferred Language"),
            "timezone": _("Timezone"),
        }

    def clean_first_name(self):
        v = self.cleaned_data.get("first_name", "").strip()
        if not v:
            raise forms.ValidationError(_("First name is required."))
        return v

    def clean_last_name(self):
        v = self.cleaned_data.get("last_name", "").strip()
        if not v:
            raise forms.ValidationError(_("Last name is required."))
        return v


class AdminUserCreateForm(forms.ModelForm):
    """
    Form for admins to create new user accounts directly (not via allauth signup).
    Password is set separately via password reset email.
    """

    role = forms.ChoiceField(
        choices=User.Role.choices,
        initial=User.Role.STUDENT,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Role"),
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role"]
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "user@example.com",
                    "autocomplete": "off",
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": _("First name"),
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": _("Last name"),
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("A user with this email already exists."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        # Set an unusable password — user must reset via email
        user.set_unusable_password()
        user.must_change_password = True
        if commit:
            user.save()
        return user


class AdminUserRoleForm(forms.ModelForm):
    """Allows admins to change a user's role."""

    class Meta:
        model = User
        fields = ["role", "require_mfa", "must_change_password"]
        widgets = {
            "role": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "role": _("Role"),
            "require_mfa": _("Force MFA Setup"),
            "must_change_password": _("Force Password Change on Next Login"),
        }
