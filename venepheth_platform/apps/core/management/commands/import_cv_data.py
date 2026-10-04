"""Import verified profile and publication data from the supplied CV."""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify

PROFILE_NAME = "VENEPHETH SAYAVONG"

COURSES = (
    "Total Quality Management",
    "Logistics and Supply Chain Management",
    "Project Management",
    "Management of Information System",
)

EDUCATION = [
    {
        "degree": "Ph.D. Student",
        "field": "Resources Management and Development",
        "institution": "Maejo University, Faculty of Agricultural Production",
        "country": "Thailand",
        "year_start": 2026,
        "is_current": True,
        "description": "",
        "order": 0,
    },
    {
        "degree": "Master of Business Administration (MBA)",
        "field": "Industrial Administration and Development",
        "institution": "Kasetsart University, Faculty of Management Sciences",
        "country": "Thailand",
        "year_end": 2018,
        "is_current": False,
        "description": "",
        "order": 1,
    },
    {
        "degree": "Bachelor of Business Management",
        "field": "Business Management",
        "institution": "National University of Laos, Faculty of Economics and Business Management",
        "country": "Laos PDR",
        "year_end": 2010,
        "is_current": False,
        "description": "",
        "order": 2,
    },
]

PUBLICATIONS = [
    {
        "title": "Service Quality and Customer Loyalty of Mie Tha Heen Restaurant (Pakse City, Champasak Province)",
        "authors": ("Lekthabandith, S., Chanyhilath, A., Syaphay, N., Sayavong, V., Xayavong, P., & Lianepaseuth, K."),
        "year": 2025,
        "journal_name": "Social Science Journal",
        "volume": "25",
        "issue": "1",
        "pages": "50-61",
        "doi": "10.71026/ss.2025.01007",
    },
    {
        "title": "The Effects of Corporate Social Responsibility on Customers' Loyalty in Lao PDR",
        "authors": (
            "Phongsavath, Saykham; Sompaseuth, Somchith; Xaisongkham, Sorphasith; "
            "Xayavong, Phoneaphay; Sayavong, Venepheth; Somphon, Vadsana"
        ),
        "year": 2021,
        "journal_name": "European Journal of Business and Management",
        "volume": "13",
        "issue": "12",
        "doi": "10.7176/EJBM/13-12-01",
        "external_url": "https://www.iiste.org/Journals/index.php/EJBM/article/view/56516",
    },
    {
        "title": "Organizational Culture and Organizational Commitment of State-owned Commercial Bank Employees in Vientiane Capital, Lao PDR",
        "authors": "Sayavong, V., & Chaiyakul, T.",
        "year": 2020,
        "journal_name": "KKU Research Journal (Graduate Studies) Humanities and Social Sciences",
        "volume": "8",
        "issue": "1",
        "pages": "127-139",
        "external_url": ("https://so04.tci-thaijo.org/index.php/gskkuhs/article/download/241443/164210"),
    },
]

DEMO_COURSE_CODES = ("BUS301", "BUS205", "RES401", "ECO202", "MGT310")
DEMO_PROJECT_TITLES = (
    "Digital Transformation of SMEs in Laos PDR: Barriers and Enablers",
    "Sustainable Business Practices and Financial Performance of ASEAN Firms",
    "Entrepreneurial Ecosystem Development in Vientiane Capital",
    "Financial Inclusion and Economic Development in Rural Laos",
)
DEMO_PUBLICATION_TITLES = (
    "Digital Transformation Readiness of SMEs: Evidence from Laos PDR",
    "Sustainability and Firm Performance: A Meta-Analysis of ASEAN Evidence",
    "Entrepreneurial Ecosystem in Vientiane: A Stakeholder Perspective",
    "Strategic Management Practices of Lao Family Businesses: A Qualitative Study",
    "The Role of Microfinance in Rural Poverty Reduction: Evidence from Laos PDR",
    "Business Education Reform in Laos: Challenges and Opportunities",
)
DEMO_ARTICLE_TITLES = (
    "Why Digital Transformation Matters for SMEs in Laos",
    "Five Things I Wish I Had Known Before Starting My Research Career",
    "Building an Entrepreneurial Ecosystem: Lessons from Vientiane",
    "Teaching Strategic Management in the Lao Context",
)
DEMO_RESOURCE_TITLES = (
    "Strategic Management Syllabus 2026",
    "Lao SME Survey Dataset 2025",
    "Business Plan Template v2",
)


class Command(BaseCommand):
    help = "Import profile, education, experience, courses and publications verified by the supplied CV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--remove-demo-data",
            action="store_true",
            help="Remove exact sample records created by the retired seed_data command.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.courses.models import Course, CourseCategory
        from apps.profiles.models import Education, Experience, Profile
        from apps.research.models import Publication

        profile = Profile.objects.filter(full_name__iexact=PROFILE_NAME).order_by("pk").first()
        if profile is None:
            profile = Profile(full_name="Venepheth SAYAVONG")

        profile.title = "Lecturer & Academic Researcher"
        profile.short_bio = (
            "Lecturer and Academic Researcher at the Faculty of Economics and Business "
            "Management, National University of Laos. Has taught BBA courses since 2013."
        )
        profile.bio = (
            "Lecturer and Academic Researcher at the Faculty of Economics and Business "
            "Management, National University of Laos. A Ph.D. student in Resources Management "
            "and Development at Maejo University, Thailand, since 2026. Holds an MBA in "
            "Industrial Administration and Development from Kasetsart University (2018) and "
            "a Bachelor's degree in Business Management from the National University of "
            "Laos (2010)."
        )
        profile.email = "v.sayavong@nuol.edu.la"
        profile.phone = "(+856-20) 99613433"
        profile.office = "Faculty of Economics and Business Management, National University of Laos; P.O. Box 7322"
        profile.website = "https://venepheth.online"
        profile.is_active = True
        profile.save()

        if options["remove_demo_data"]:
            removed = self._remove_demo_data(profile)
            self.stdout.write(f"Removed exact demo records: {removed}")

        for education in EDUCATION:
            defaults = {**education, "year_start": education.get("year_start"), "year_end": education.get("year_end")}
            record = (
                Education.objects.filter(
                    profile=profile,
                    degree=education["degree"],
                    institution=education["institution"],
                )
                .order_by("pk")
                .first()
            )
            if record is None:
                Education.objects.create(profile=profile, **defaults)
            else:
                for field, value in defaults.items():
                    setattr(record, field, value)
                record.save()

        experience_values = {
            "position": "Lecturer & Academic Researcher",
            "organization": "National University of Laos",
            "department": "Faculty of Economics and Business Management",
            "country": "Laos PDR",
            "year_start": 2013,
            "year_end": None,
            "is_current": True,
            "description": (
                "Lectures for the BBA programme since 2013: Total Quality Management; "
                "Logistics and Supply Chain Management; Project Management; and Management "
                "of Information System."
            ),
            "order": 0,
        }
        experience = (
            Experience.objects.filter(
                profile=profile,
                position=experience_values["position"],
                organization=experience_values["organization"],
                department=experience_values["department"],
            )
            .order_by("pk")
            .first()
        )
        if experience is None:
            Experience.objects.create(profile=profile, **experience_values)
        else:
            for field, value in experience_values.items():
                setattr(experience, field, value)
            experience.save()

        category, _ = CourseCategory.objects.get_or_create(
            slug="management",
            defaults={"name": "Management"},
        )
        for course_name in COURSES:
            slug = slugify(course_name)
            Course.objects.get_or_create(
                slug=slug,
                defaults={
                    "code": "",
                    "name": course_name,
                    "description": "Listed in the supplied CV as taught for the BBA programme since 2013.",
                    "short_description": "BBA course taught since 2013.",
                    "category": category,
                    "credits": 0,
                    "semester": "",
                    "academic_year": "",
                    "level": "BBA",
                    "language": "",
                    "featured": True,
                    "visibility": Course.Visibility.PUBLIC,
                    "status": Course.Status.PUBLISHED,
                },
            )

        for publication in PUBLICATIONS:
            defaults = {
                **publication,
                "slug": slugify(publication["title"])[:240],
                "publication_type": Publication.PublicationType.JOURNAL,
                "abstract": "",
                "keywords": "",
                "cited_by": 0,
                "featured": False,
                "status": Publication.Status.PUBLISHED,
            }
            publication_records = (
                Publication.objects.filter(doi=publication["doi"])
                if publication.get("doi")
                else (Publication.objects.filter(slug=defaults["slug"]))
            )
            record = publication_records.order_by("pk").first()
            if record is None:
                Publication.objects.create(**defaults)
            else:
                for field, value in defaults.items():
                    setattr(record, field, value)
                record.save()

        self.stdout.write(self.style.SUCCESS("Imported CV-verified profile, courses and 3 publications."))

    def _remove_demo_data(self, profile):
        from apps.blog.models import Article, ArticleTag
        from apps.courses.models import Course, CourseCategory
        from apps.profiles.models import AcademicInterest, Education, Experience, Language
        from apps.research.models import Publication, ResearchProject, ResearchTopic
        from apps.resources.models import Resource, ResourceCategory

        removed = {}
        demo_courses = Course.objects.filter(code__in=DEMO_COURSE_CODES)
        removed["courses"] = demo_courses.count()
        demo_courses.delete()
        demo_projects = ResearchProject.objects.filter(title__in=DEMO_PROJECT_TITLES)
        removed["projects"] = demo_projects.count()
        demo_projects.delete()
        demo_publications = Publication.objects.filter(title__in=DEMO_PUBLICATION_TITLES)
        removed["publications"] = demo_publications.count()
        demo_publications.delete()
        demo_articles = Article.objects.filter(title__in=DEMO_ARTICLE_TITLES)
        removed["articles"] = demo_articles.count()
        demo_articles.delete()
        demo_resources = Resource.objects.filter(title__in=DEMO_RESOURCE_TITLES)
        removed["resources"] = demo_resources.count()
        demo_resources.delete()

        if profile:
            education_demo = (
                Q(degree="Doctor of Philosophy (PhD)", institution="National University of Laos")
                | Q(degree="Master of Business Administration (MBA)", institution="Chiang Mai University")
                | Q(degree="Bachelor of Economics", institution="National University of Laos")
            )
            Education.objects.filter(profile=profile).filter(education_demo).delete()
            experience_demo = (
                Q(
                    position="Associate Lecturer",
                    organization="National University of Laos",
                    department="Faculty of Business Administration",
                )
                | Q(position="Research Fellow", organization="ASEAN Business Research Network")
                | Q(
                    position="Lecturer",
                    organization="National University of Laos",
                    department="Faculty of Economics",
                )
            )
            Experience.objects.filter(profile=profile).filter(experience_demo).delete()
            AcademicInterest.objects.filter(
                profile=profile,
                name__in=(
                    "Strategic Management",
                    "SME Development",
                    "Entrepreneurship",
                    "Digital Transformation",
                    "Sustainable Development",
                    "Business Ethics",
                ),
            ).delete()
            Language.objects.filter(
                profile=profile,
                name__in=("Lao", "English", "Thai"),
            ).delete()

        for category in CourseCategory.objects.filter(
            slug__in=("business-administration", "economics", "research-methodology", "management")
        ):
            if not category.courses.exists():
                category.delete()

        for category in ResourceCategory.objects.filter(slug__in=("lecture-notes", "datasets", "templates")):
            if not category.resources.exists():
                category.delete()

        demo_topic_names = (
            "Strategic Management",
            "SME Development",
            "Digital Transformation",
            "Sustainable Development",
            "Entrepreneurship",
            "Business Ethics",
            "ASEAN Economics",
            "Financial Inclusion",
            "Innovation Management",
        )
        for topic in ResearchTopic.objects.filter(name__in=demo_topic_names):
            if not topic.projects.exists() and not topic.publications.exists():
                topic.delete()

        demo_tag_names = ("Strategy", "Research", "Entrepreneurship", "Education", "Laos", "ASEAN", "SME", "Leadership")
        for tag in ArticleTag.objects.filter(name__in=demo_tag_names):
            if not tag.articles.exists():
                tag.delete()

        return removed
