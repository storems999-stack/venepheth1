"""
Seed starter FAQs for the AI Knowledge Box.

Idempotent: uses get_or_create by slug, so re-running never overwrites
admin edits. Reverse migration removes only these seed slugs.
"""

from django.db import migrations

SEED_FAQS = [
    {
        "slug": "ai-assistant-help-en",
        "title": "What can the AI Assistant help with?",
        "summary": "Capabilities of the AI Academic Assistant.",
        "content": (
            "The AI Academic Assistant can answer questions about courses offered, "
            "teaching schedule and office hours, research projects, publications, "
            "library resources, and latest blog articles. "
            "Answers are grounded in this site's academic records and always include "
            "source links. For complex inquiries, use the Contact page."
        ),
        "tags": "help, ai, assistant, faq",
        "language": "en",
        "source_url": "/assistant/",
    },
    {
        "slug": "ai-assistant-help-lo",
        "title": "AI Assistant ຊ່ວຍຫຍັງໄດ້ແດ່?",
        "summary": "ຄວາມສາມາດຂອງ AI Academic Assistant.",
        "content": (
            "AI Academic Assistant ຕອບຄຳຖາມກ່ຽວກັບວິຊາຮຽນ, ຕາຕະລາງສອນ ແລະ ເວລາຮັບນັກສຶກສາ, "
            "ໂຄງການຄົ້ນຄ້ວາ, ສິ່ງຕີພິມ, ເອກະສານໃນຫ້ອງສະໝຸດ ແລະ ບົດຄວາມລ່າສຸດ. "
            "ຄຳຕອບອ້າງອີງຈາກຂໍ້ມູນວິຊາການໃນລະບົບພ້ອມລິ້ງແຫຼ່ງຂໍ້ມູນ. "
            "ສຳລັບເລື່ອງຊັບຊ້ອນ ກະລຸນາໃຊ້ໜ້າຕິດຕໍ່."
        ),
        "tags": "help, ai, assistant, faq, ຊ່ວຍເຫຼືອ",
        "language": "lo",
        "source_url": "/assistant/",
    },
    {
        "slug": "office-hours-faq",
        "title": "Where can I find office hours?",
        "summary": "How to check the professor's office hours.",
        "content": (
            "Current office hours are published on the Teaching page, including day, "
            "time, location, and online meeting links where available. "
            "Ask the assistant e.g. 'When are office hours?' for the latest schedule."
        ),
        "tags": "office hours, teaching, schedule, faq",
        "language": "en",
        "source_url": "/teaching/",
    },
    {
        "slug": "courses-faq",
        "title": "What courses are offered?",
        "summary": "How to browse current courses.",
        "content": (
            "All current and past courses are listed on the Courses page with syllabus, "
            "learning outcomes, modules, and downloadable resources. "
            "Ask the assistant e.g. 'What courses are offered?' and it will cite "
            "the matching course pages."
        ),
        "tags": "courses, syllabus, faq",
        "language": "en",
        "source_url": "/courses/",
    },
    {
        "slug": "contact-faq",
        "title": "How do I contact the professor?",
        "summary": "How to send collaboration or supervision inquiries.",
        "content": (
            "Use the Contact page for supervision, collaboration, or speaking requests. "
            "Include your full name, institution, subject, and a clear message. "
            "Spam-like messages are filtered automatically."
        ),
        "tags": "contact, collaboration, faq",
        "language": "en",
        "source_url": "/contact/",
    },
]


def seed_faqs(apps, schema_editor):
    KnowledgeDocument = apps.get_model("assistant", "KnowledgeDocument")
    for faq in SEED_FAQS:
        KnowledgeDocument.objects.get_or_create(
            slug=faq["slug"],
            defaults={**faq, "is_active": True},
        )


def unseed_faqs(apps, schema_editor):
    KnowledgeDocument = apps.get_model("assistant", "KnowledgeDocument")
    KnowledgeDocument.objects.filter(slug__in=[f["slug"] for f in SEED_FAQS]).delete()


class Migration(migrations.Migration):
    dependencies = [("assistant", "0001_initial")]

    operations = [migrations.RunPython(seed_faqs, unseed_faqs)]
