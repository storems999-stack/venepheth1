"""Contact forms with honeypot anti-spam protection."""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    """Contact message form with hidden honeypot field for anti-spam."""

    # Honeypot field - bots autofill this, real users never see or fill it
    website_url_hp = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "tabindex": "-1",
                "autocomplete": "off",
                "style": "display:none !important; position:absolute !important; left:-9999px !important;",
                "aria-hidden": "true",
            }
        ),
    )

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "organization", "subject", "message"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full bg-navy-900 border border-white/10 focus:border-gold-500 text-white placeholder-gray-600 rounded-xl px-4 py-3 text-sm outline-none transition-all",
                    "placeholder": _("Your full name"),
                    "required": True,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full bg-navy-900 border border-white/10 focus:border-gold-500 text-white placeholder-gray-600 rounded-xl px-4 py-3 text-sm outline-none transition-all",
                    "placeholder": _("your@email.com"),
                    "required": True,
                }
            ),
            "organization": forms.TextInput(
                attrs={
                    "class": "w-full bg-navy-900 border border-white/10 focus:border-gold-500 text-white placeholder-gray-600 rounded-xl px-4 py-3 text-sm outline-none transition-all",
                    "placeholder": _("Your institution or company"),
                }
            ),
            "subject": forms.TextInput(
                attrs={
                    "class": "w-full bg-navy-900 border border-white/10 focus:border-gold-500 text-white placeholder-gray-600 rounded-xl px-4 py-3 text-sm outline-none transition-all",
                    "placeholder": _("What is this about?"),
                    "required": True,
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "w-full bg-navy-900 border border-white/10 focus:border-gold-500 text-white placeholder-gray-600 rounded-xl px-4 py-3 text-sm outline-none transition-all resize-none",
                    "rows": 6,
                    "placeholder": _("Tell me about your inquiry, project or collaboration idea..."),
                    "required": True,
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        hp = cleaned_data.get("website_url_hp")
        if hp:
            self.is_spam = True
        else:
            self.is_spam = False
        return cleaned_data
