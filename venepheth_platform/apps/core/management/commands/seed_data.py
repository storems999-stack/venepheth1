"""
Seed data management command for Venepheth Academic Platform.
Creates realistic sample data: Profile, Courses, Research, Publications, Blog Articles, Events.
Usage: python manage.py seed_data [--clear]
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify


class Command(BaseCommand):
    help = "Seed the database with realistic sample data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing seed data before creating new records.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            self._clear_data()

        self.stdout.write("🌱  Seeding database...")
        self._seed_profile()
        self._seed_courses()
        self._seed_research()
        self._seed_articles()
        self._seed_resources()
        self.stdout.write(self.style.SUCCESS("✅  Database seeded successfully!"))

    # ──────────────────────────────────────────────────────────
    def _clear_data(self):
        from apps.blog.models import Article, ArticleTag
        from apps.courses.models import Course, CourseCategory
        from apps.profiles.models import Profile
        from apps.research.models import Publication, ResearchProject, ResearchTopic
        from apps.resources.models import Resource, ResourceCategory

        Resource.objects.all().delete()
        ResourceCategory.objects.all().delete()
        Article.objects.all().delete()
        ArticleTag.objects.all().delete()
        Publication.objects.all().delete()
        ResearchProject.objects.all().delete()
        ResearchTopic.objects.all().delete()
        Course.objects.all().delete()
        CourseCategory.objects.all().delete()
        Profile.objects.all().delete()

    # ──────────────────────────────────────────────────────────
    def _seed_profile(self):
        from apps.profiles.models import (
            AcademicInterest,
            Education,
            Experience,
            Language,
            Profile,
        )

        profile, created = Profile.objects.get_or_create(
            full_name="Venepheth SAYAVONG",
            defaults={
                "title": "Lecturer & Researcher in Business Administration",
                "short_bio": (
                    "An academic dedicated to advancing business education and research "
                    "in Laos, bridging theory and practice for sustainable development."
                ),
                "bio": (
                    "Dr. Venepheth SAYAVONG is a Lecturer and Researcher at the Faculty of "
                    "Business Administration, specializing in strategic management, "
                    "entrepreneurship, and sustainable business development. With over a "
                    "decade of teaching and research experience, he is committed to fostering "
                    "the next generation of business leaders in Laos PDR and the ASEAN region.\n\n"
                    "His research interests span business strategy, SME development, "
                    "digital transformation, and economic sustainability. He has published "
                    "in peer-reviewed journals and presented at international conferences "
                    "across Southeast Asia."
                ),
                "email": "venepheth@university.edu.la",
                "office": "Faculty of Business Administration, Room 301",
                "is_active": True,
            },
        )
        if not created:
            self.stdout.write("  Profile already exists, skipping.")
            return

        Education.objects.bulk_create(
            [
                Education(
                    profile=profile,
                    degree="Doctor of Philosophy (PhD)",
                    field="Business Administration",
                    institution="National University of Laos",
                    country="Laos PDR",
                    year_start=2015,
                    year_end=2019,
                    order=0,
                ),
                Education(
                    profile=profile,
                    degree="Master of Business Administration (MBA)",
                    field="Strategic Management",
                    institution="Chiang Mai University",
                    country="Thailand",
                    year_start=2011,
                    year_end=2013,
                    order=1,
                ),
                Education(
                    profile=profile,
                    degree="Bachelor of Economics",
                    field="Economics",
                    institution="National University of Laos",
                    country="Laos PDR",
                    year_start=2006,
                    year_end=2010,
                    order=2,
                ),
            ]
        )

        Experience.objects.bulk_create(
            [
                Experience(
                    profile=profile,
                    position="Associate Lecturer",
                    organization="National University of Laos",
                    department="Faculty of Business Administration",
                    country="Laos PDR",
                    year_start=2019,
                    is_current=True,
                    order=0,
                ),
                Experience(
                    profile=profile,
                    position="Research Fellow",
                    organization="ASEAN Business Research Network",
                    country="Regional",
                    year_start=2021,
                    is_current=True,
                    order=1,
                ),
                Experience(
                    profile=profile,
                    position="Lecturer",
                    organization="National University of Laos",
                    department="Faculty of Economics",
                    country="Laos PDR",
                    year_start=2013,
                    year_end=2019,
                    order=2,
                ),
            ]
        )

        Language.objects.bulk_create(
            [
                Language(profile=profile, name="Lao", proficiency="native", order=0),
                Language(profile=profile, name="English", proficiency="fluent", order=1),
                Language(profile=profile, name="Thai", proficiency="advanced", order=2),
            ]
        )

        interests = [
            "Strategic Management",
            "SME Development",
            "Entrepreneurship",
            "Digital Transformation",
            "Sustainable Development",
            "Business Ethics",
        ]
        AcademicInterest.objects.bulk_create(
            [AcademicInterest(profile=profile, name=i, order=n) for n, i in enumerate(interests)]
        )
        self.stdout.write(f"  ✓ Profile created: {profile.full_name}")

    # ──────────────────────────────────────────────────────────
    def _seed_courses(self):
        from apps.courses.models import (
            Course,
            CourseCategory,
            CourseModule,
            LearningOutcome,
        )

        categories_data = [
            ("Business Administration", "business-administration"),
            ("Economics", "economics"),
            ("Research Methodology", "research-methodology"),
            ("Management", "management"),
        ]
        categories = {}
        for name, slug in categories_data:
            cat, _ = CourseCategory.objects.get_or_create(slug=slug, defaults={"name": name})
            categories[slug] = cat

        courses_data = [
            {
                "code": "BUS301",
                "name": "Strategic Management",
                "description": (
                    "This course explores the fundamentals of strategic management, including "
                    "environmental analysis, competitive strategy, and strategic implementation. "
                    "Students will develop skills in analyzing business environments and formulating "
                    "effective organizational strategies."
                ),
                "short_description": "Comprehensive study of business strategy formulation, implementation and evaluation.",
                "category": "business-administration",
                "credits": 3,
                "semester": "Semester 1",
                "academic_year": "2026–2027",
                "level": "Graduate",
                "language": "Lao / English",
                "featured": True,
                "outcomes": [
                    "Analyze external and internal business environments using established frameworks",
                    "Formulate competitive strategies appropriate to organizational context",
                    "Evaluate strategic options and develop implementation plans",
                    "Apply strategic management tools in real-world case studies",
                ],
                "modules": [
                    "Introduction to Strategic Management",
                    "External Environment Analysis (PESTEL, Porter's Five Forces)",
                    "Internal Environment Analysis (VRIO, Value Chain)",
                    "Competitive Strategy: Cost Leadership, Differentiation, Focus",
                    "Strategy Implementation and Change Management",
                    "Strategic Evaluation and Control",
                ],
            },
            {
                "code": "BUS205",
                "name": "Entrepreneurship and SME Development",
                "description": (
                    "Explores the theory and practice of entrepreneurship with a focus on "
                    "small and medium enterprise development in the Lao context. Topics include "
                    "opportunity identification, business planning, and growth strategies for SMEs."
                ),
                "short_description": "Building and growing successful businesses in the Lao and ASEAN context.",
                "category": "business-administration",
                "credits": 3,
                "semester": "Semester 2",
                "academic_year": "2026–2027",
                "level": "Undergraduate",
                "language": "Lao",
                "featured": True,
                "outcomes": [
                    "Identify and evaluate entrepreneurial opportunities in the local market",
                    "Develop comprehensive business plans for new ventures",
                    "Understand the challenges and opportunities facing SMEs in Laos",
                    "Apply entrepreneurial thinking to business problem-solving",
                ],
                "modules": [
                    "Introduction to Entrepreneurship",
                    "Opportunity Recognition and Business Idea Generation",
                    "Market Research and Feasibility Analysis",
                    "Writing a Business Plan",
                    "Financing a New Venture",
                    "Growth Strategies for SMEs",
                ],
            },
            {
                "code": "RES401",
                "name": "Research Methodology in Business",
                "description": (
                    "A graduate-level course covering quantitative and qualitative research methods "
                    "in business and social sciences. Students learn to design research projects, "
                    "collect and analyze data, and write research papers to international standards."
                ),
                "short_description": "Quantitative and qualitative research design for business studies.",
                "category": "research-methodology",
                "credits": 3,
                "semester": "Semester 1",
                "academic_year": "2026–2027",
                "level": "Graduate",
                "language": "English",
                "featured": True,
                "outcomes": [
                    "Design rigorous research projects using appropriate methodologies",
                    "Apply quantitative methods including survey design and statistical analysis",
                    "Conduct qualitative research through interviews and case studies",
                    "Write and present research findings according to academic standards",
                ],
                "modules": [
                    "Introduction to Research Methods",
                    "Literature Review and Theoretical Framework",
                    "Quantitative Research Design",
                    "Qualitative Research Methods",
                    "Data Collection and Survey Design",
                    "Data Analysis: Descriptive and Inferential Statistics",
                    "Writing a Research Thesis",
                ],
            },
            {
                "code": "ECO202",
                "name": "Microeconomics",
                "description": (
                    "Covers the fundamental principles of microeconomic theory including "
                    "consumer behavior, firm theory, market structures, and welfare economics. "
                    "Students will develop analytical skills to understand markets and economic decision-making."
                ),
                "short_description": "Core principles of microeconomic theory, markets, and resource allocation.",
                "category": "economics",
                "credits": 3,
                "semester": "Semester 2",
                "academic_year": "2026–2027",
                "level": "Undergraduate",
                "language": "Lao",
                "featured": False,
                "outcomes": [
                    "Understand consumer choice theory and demand analysis",
                    "Analyze firm behavior and production decisions",
                    "Evaluate different market structures and their outcomes",
                    "Apply economic models to real-world policy questions",
                ],
                "modules": [
                    "Introduction and Economic Thinking",
                    "Supply, Demand and Market Equilibrium",
                    "Consumer Choice Theory",
                    "Production and Cost Theory",
                    "Perfect Competition",
                    "Monopoly and Market Power",
                ],
            },
            {
                "code": "MGT310",
                "name": "Organizational Behavior",
                "description": (
                    "Studies human behavior in organizational settings, covering individual, "
                    "group, and organizational level phenomena. Topics include motivation, "
                    "leadership, team dynamics, organizational culture, and change management."
                ),
                "short_description": "Understanding human behavior and leadership in modern organizations.",
                "category": "management",
                "credits": 3,
                "semester": "Semester 1",
                "academic_year": "2026–2027",
                "level": "Undergraduate",
                "language": "Lao / English",
                "featured": True,
                "outcomes": [
                    "Analyze individual behavior and motivation in organizational contexts",
                    "Understand group dynamics and team effectiveness",
                    "Apply leadership theories to organizational challenges",
                    "Manage organizational culture and change processes",
                ],
                "modules": [
                    "Introduction to Organizational Behavior",
                    "Individual Differences and Personality",
                    "Motivation Theories and Application",
                    "Group Dynamics and Teamwork",
                    "Leadership and Influence",
                    "Organizational Culture and Change",
                ],
            },
        ]

        for data in courses_data:
            slug = slugify(data["name"])
            if Course.objects.filter(slug=slug).exists():
                continue
            course = Course.objects.create(
                code=data["code"],
                name=data["name"],
                slug=slug,
                description=data["description"],
                short_description=data["short_description"],
                category=categories[data["category"]],
                credits=data["credits"],
                semester=data["semester"],
                academic_year=data["academic_year"],
                level=data["level"],
                language=data["language"],
                featured=data["featured"],
                status="published",
                visibility="public",
                published_at=timezone.now(),
            )
            for i, outcome in enumerate(data["outcomes"]):
                LearningOutcome.objects.create(course=course, description=outcome, order=i)
            for i, module_title in enumerate(data["modules"]):
                CourseModule.objects.create(course=course, title=module_title, order=i, is_visible=True)
            self.stdout.write(f"  ✓ Course: {course.code} {course.name}")

    # ──────────────────────────────────────────────────────────
    def _seed_research(self):
        from apps.research.models import Publication, ResearchProject, ResearchTopic

        topics_data = [
            "Strategic Management",
            "SME Development",
            "Digital Transformation",
            "Sustainable Development",
            "Entrepreneurship",
            "Business Ethics",
            "ASEAN Economics",
            "Financial Inclusion",
            "Innovation Management",
        ]
        topics = {}
        for name in topics_data:
            slug = slugify(name)
            topic, _ = ResearchTopic.objects.get_or_create(slug=slug, defaults={"name": name})
            topics[name] = topic

        projects_data = [
            {
                "title": "Digital Transformation of SMEs in Laos PDR: Barriers and Enablers",
                "abstract": (
                    "This research investigates the barriers and enablers of digital transformation "
                    "among small and medium enterprises (SMEs) in Laos PDR. Using a mixed-methods "
                    "approach combining survey data from 200 SMEs and qualitative interviews with "
                    "business owners and policy makers, the study identifies key factors influencing "
                    "digital adoption. Findings reveal that limited digital infrastructure, access "
                    "to financing, and digital literacy are primary barriers, while government "
                    "support programs and industry partnerships serve as key enablers."
                ),
                "research_status": "ongoing",
                "start_date": "2024-01-01",
                "funding_source": "National Research Council of Laos PDR",
                "topics": ["Digital Transformation", "SME Development"],
                "featured": True,
            },
            {
                "title": "Sustainable Business Practices and Financial Performance of ASEAN Firms",
                "abstract": (
                    "An empirical investigation of the relationship between environmental and social "
                    "sustainability practices and financial performance across firms in ASEAN member "
                    "states. The study uses panel data from 350 publicly listed companies over a "
                    "10-year period (2013–2023), employing panel regression analysis and structural "
                    "equation modeling. Results indicate a positive long-term association between "
                    "sustainability orientation and firm financial performance, particularly in "
                    "manufacturing and services sectors."
                ),
                "research_status": "completed",
                "start_date": "2022-03-01",
                "end_date": "2024-06-30",
                "funding_source": "ASEAN Foundation Research Grant",
                "topics": ["Sustainable Development", "ASEAN Economics"],
                "featured": True,
            },
            {
                "title": "Entrepreneurial Ecosystem Development in Vientiane Capital",
                "abstract": (
                    "This study maps and evaluates the entrepreneurial ecosystem in Vientiane Capital, "
                    "Laos PDR, examining the role of universities, government agencies, financial "
                    "institutions, and cultural factors in supporting startup creation and growth. "
                    "Using stakeholder interviews and ecosystem framework analysis, the research "
                    "provides evidence-based recommendations for policy interventions to strengthen "
                    "the local entrepreneurial environment."
                ),
                "research_status": "published",
                "start_date": "2021-06-01",
                "end_date": "2023-01-31",
                "funding_source": "National University of Laos Research Fund",
                "topics": ["Entrepreneurship", "SME Development"],
                "featured": False,
            },
            {
                "title": "Financial Inclusion and Economic Development in Rural Laos",
                "abstract": (
                    "An examination of how access to formal financial services (banking, microfinance, "
                    "mobile money) affects household income, savings behavior, and economic development "
                    "in rural communities across three provinces in Laos PDR. The study employs "
                    "household survey data and econometric analysis to measure the causal impact of "
                    "financial inclusion on welfare outcomes."
                ),
                "research_status": "ongoing",
                "start_date": "2025-01-01",
                "funding_source": "ADB Technical Assistance Grant",
                "topics": ["Financial Inclusion", "Sustainable Development"],
                "featured": False,
            },
        ]

        for data in projects_data:
            slug = slugify(data["title"])[:240]
            if ResearchProject.objects.filter(slug=slug).exists():
                continue
            proj = ResearchProject.objects.create(
                title=data["title"],
                slug=slug,
                abstract=data["abstract"],
                research_status=data["research_status"],
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                funding_source=data.get("funding_source", ""),
                featured=data["featured"],
                status="published",
                published_at=timezone.now(),
            )
            for tname in data["topics"]:
                if tname in topics:
                    proj.topics.add(topics[tname])
            self.stdout.write(f"  ✓ Research: {proj.title[:60]}")

        # ── Publications ──────────────────────────────────────
        publications_data = [
            {
                "title": "Digital Transformation Readiness of SMEs: Evidence from Laos PDR",
                "pub_type": "journal",
                "abstract": "This paper examines the digital readiness of SMEs in Laos, identifying key barriers and policy recommendations for accelerating digital adoption.",
                "authors": "Sayavong, V., Phonethip, K., & Manorath, S.",
                "year": 2024,
                "journal": "Journal of Asian Business Studies",
                "volume": "18",
                "issue": "2",
                "pages": "145–167",
                "doi": "10.1108/JABS-2024-0123",
                "keywords": "digital transformation, SME, Laos, technology adoption",
                "topics": ["Digital Transformation", "SME Development"],
                "cited_by": 8,
                "featured": True,
            },
            {
                "title": "Sustainability and Firm Performance: A Meta-Analysis of ASEAN Evidence",
                "pub_type": "journal",
                "abstract": "A systematic review and meta-analysis of 45 studies examining the relationship between sustainability practices and firm financial performance in ASEAN member states.",
                "authors": "Sayavong, V., & Chanthavilay, P.",
                "year": 2023,
                "journal": "Sustainability",
                "volume": "15",
                "issue": "8",
                "pages": "6823",
                "doi": "10.3390/su15086823",
                "keywords": "ESG, sustainability, financial performance, ASEAN",
                "topics": ["Sustainable Development", "ASEAN Economics"],
                "cited_by": 24,
                "featured": True,
            },
            {
                "title": "Entrepreneurial Ecosystem in Vientiane: A Stakeholder Perspective",
                "pub_type": "conference",
                "abstract": "Using ecosystem theory and stakeholder interviews, this paper maps the entrepreneurial ecosystem in Vientiane Capital and identifies constraints on startup growth.",
                "authors": "Sayavong, V., Soukvilay, B., & Phetthong, L.",
                "year": 2023,
                "journal": "Proceedings of the 2023 ASEAN Entrepreneurship Conference",
                "pages": "88–99",
                "keywords": "entrepreneurial ecosystem, startups, Laos",
                "topics": ["Entrepreneurship"],
                "cited_by": 5,
                "featured": False,
            },
            {
                "title": "Strategic Management Practices of Lao Family Businesses: A Qualitative Study",
                "pub_type": "journal",
                "abstract": "An in-depth qualitative examination of strategic decision-making processes in family-owned businesses in Laos, with implications for business governance and succession planning.",
                "authors": "Sayavong, V.",
                "year": 2022,
                "journal": "Asian Journal of Business Research",
                "volume": "12",
                "issue": "1",
                "pages": "21–40",
                "doi": "10.14707/ajbr.220115",
                "keywords": "family business, strategic management, Laos, qualitative",
                "topics": ["Strategic Management"],
                "cited_by": 12,
                "featured": False,
            },
            {
                "title": "The Role of Microfinance in Rural Poverty Reduction: Evidence from Laos PDR",
                "pub_type": "journal",
                "abstract": "Using household panel data from three rural provinces, this study examines the impact of microfinance access on household income, consumption, and poverty rates.",
                "authors": "Sayavong, V., & Khamphanh, D.",
                "year": 2021,
                "journal": "Journal of Development Economics",
                "volume": "9",
                "issue": "3",
                "pages": "310–335",
                "doi": "10.1111/JADE-2021-0037",
                "keywords": "microfinance, poverty reduction, rural development, Laos",
                "topics": ["Financial Inclusion", "Sustainable Development"],
                "cited_by": 31,
                "featured": False,
            },
            {
                "title": "Business Education Reform in Laos: Challenges and Opportunities",
                "pub_type": "book_chapter",
                "abstract": "A policy-oriented analysis of higher business education in Laos PDR, examining curriculum design, faculty development, and the alignment of business education with economic development needs.",
                "authors": "Sayavong, V.",
                "year": 2022,
                "journal": "Business Education in Southeast Asia (Springer)",
                "isbn": "978-981-19-5432-1",
                "keywords": "business education, higher education, Laos, curriculum reform",
                "topics": ["Entrepreneurship"],
                "cited_by": 7,
                "featured": False,
            },
        ]

        for data in publications_data:
            slug = slugify(data["title"])[:240]
            if Publication.objects.filter(slug=slug).exists():
                continue
            pub = Publication.objects.create(
                title=data["title"],
                slug=slug,
                publication_type=data["pub_type"],
                abstract=data.get("abstract", ""),
                authors=data["authors"],
                year=data["year"],
                journal_name=data.get("journal", ""),
                volume=data.get("volume", ""),
                issue=data.get("issue", ""),
                pages=data.get("pages", ""),
                doi=data.get("doi", ""),
                isbn=data.get("isbn", ""),
                keywords=data.get("keywords", ""),
                cited_by=data.get("cited_by", 0),
                featured=data.get("featured", False),
                status="published",
                published_at=timezone.now(),
            )
            for tname in data.get("topics", []):
                if tname in topics:
                    pub.topics.add(topics[tname])
            self.stdout.write(f"  ✓ Publication: {pub.title[:60]}")

    # ──────────────────────────────────────────────────────────
    def _seed_articles(self):
        from apps.blog.models import Article, ArticleTag

        tags_data = ["Strategy", "Research", "Entrepreneurship", "Education", "Laos", "ASEAN", "SME", "Leadership"]
        tags = {}
        for name in tags_data:
            slug = slugify(name)
            tag, _ = ArticleTag.objects.get_or_create(slug=slug, defaults={"name": name})
            tags[name] = tag

        articles_data = [
            {
                "title": "Why Digital Transformation Matters for SMEs in Laos",
                "subtitle": "Lessons from the field and a path forward",
                "excerpt": (
                    "Small and medium enterprises form the backbone of Laos's economy, yet most "
                    "remain disconnected from the digital economy. Here's what we found and why it matters."
                ),
                "content_raw": """
<p>Small and medium enterprises (SMEs) account for over 90% of all businesses and employ the majority of the workforce in Laos PDR. Yet as the global economy undergoes rapid digital transformation, most Lao SMEs remain on the sidelines — constrained by infrastructure gaps, limited capital, and a shortage of digital skills.</p>

<h2>What the Data Shows</h2>
<p>Our recent survey of 200 SMEs across Vientiane, Savannakhet, and Luang Prabang found that only 34% use any form of digital tool beyond basic mobile communication for business operations. Of those, most rely solely on Facebook for marketing — a single platform that represents their entire digital footprint.</p>

<p>The findings reveal a stark divide. Larger SMEs — those with 20+ employees — are three times more likely to have adopted digital tools compared to micro-enterprises. This suggests that economies of scale play a significant role in digital adoption capacity.</p>

<h2>The Key Barriers</h2>
<p>When asked what prevents them from adopting digital tools, SME owners consistently cited three barriers:</p>
<ul>
    <li><strong>Cost:</strong> Software subscriptions and device costs are prohibitive for many small businesses</li>
    <li><strong>Skills gap:</strong> Owners and staff lack the digital literacy needed to use new tools effectively</li>
    <li><strong>Trust:</strong> Many are concerned about data security and the reliability of digital platforms</li>
</ul>

<h2>A Path Forward</h2>
<p>The solution cannot come from SMEs alone. Government agencies, financial institutions, universities, and technology providers must collaborate to build an enabling environment. Specifically, we recommend subsidized digital tools for micro-enterprises, digital literacy training programs integrated into business support services, and a national SME digital readiness index to track progress over time.</p>

<p>The window of opportunity is now. ASEAN's digital economy is projected to reach $1 trillion by 2030. If Lao SMEs are to participate, the time to act is today.</p>
""",
                "category": "academic",
                "tags": ["SME", "Laos", "Strategy"],
                "is_featured": True,
            },
            {
                "title": "Five Things I Wish I Had Known Before Starting My Research Career",
                "subtitle": "Reflections from ten years in academia",
                "excerpt": (
                    "Academic careers are rewarding but often opaque to outsiders. Here are the five most "
                    "important lessons I've learned in a decade of research and teaching."
                ),
                "content_raw": """
<p>I started my academic journey over a decade ago, full of enthusiasm for ideas but largely unprepared for the realities of life in academia. Looking back, there are several things I wish someone had told me at the beginning.</p>

<h2>1. Your Network Is Your Research Infrastructure</h2>
<p>Ideas don't exist in isolation. The quality of your research improves dramatically when you engage actively with other researchers, participate in conferences, and build genuine collaborative relationships. Some of my best papers came from conversations at workshops, not from sitting alone in my office.</p>

<h2>2. Writing Is a Daily Practice</h2>
<p>Most academics I admire write something every day — even if it's just 200 words. Research doesn't get published if it stays in your head. Treat writing like exercise: small, consistent efforts compound into something substantial over time.</p>

<h2>3. Rejection Is the Default</h2>
<p>Getting a paper rejected from a top journal isn't a sign of failure — it's normal. What matters is how you respond to reviewers' feedback. The papers that eventually get published are almost always better for having been rejected and revised multiple times.</p>

<h2>4. Teaching and Research Feed Each Other</h2>
<p>Early in my career I saw teaching as a distraction from research. I was wrong. Explaining concepts to students forces you to deepen your own understanding, and students' questions often point toward gaps in knowledge that become the seed of a new research project.</p>

<h2>5. Define Your Own Measure of Success</h2>
<p>Academic culture can be obsessed with impact factors, citation counts, and h-indices. While these metrics matter to some extent, I've found more lasting satisfaction from the quality of my relationships with students, the real-world impact of my research, and the joy of learning itself.</p>
""",
                "category": "article",
                "tags": ["Research", "Education", "Leadership"],
                "is_featured": False,
            },
            {
                "title": "Building an Entrepreneurial Ecosystem: Lessons from Vientiane",
                "subtitle": "What our research revealed about startup support in the capital",
                "excerpt": (
                    "Vientiane is seeing growing interest in entrepreneurship, but critical gaps remain. "
                    "Our latest research examines the ecosystem and what needs to change."
                ),
                "content_raw": """
<p>In the past five years, Vientiane Capital has seen a notable uptick in entrepreneurial activity. New cafes, tech startups, and social enterprises have appeared across the city. The government has established an SME promotion agency, and universities are introducing entrepreneurship courses. Yet for many aspiring entrepreneurs, the path from idea to sustainable business remains treacherous.</p>

<h2>What We Found</h2>
<p>Our stakeholder research — involving interviews with 48 entrepreneurs, investors, university administrators, government officials, and business support organizations — reveals a picture of a nascent ecosystem with significant structural gaps.</p>

<p>On the positive side, entrepreneurial intent is high, especially among university graduates. There is genuine optimism about Laos's economic potential, and a growing cohort of successful entrepreneurs who are willing to mentor and invest in the next generation.</p>

<h2>Critical Gaps</h2>
<p>However, three critical gaps consistently emerged:</p>
<ul>
    <li><strong>Access to early-stage capital:</strong> Angel investors and seed funds are extremely scarce. Most entrepreneurs rely on family savings or informal loans.</li>
    <li><strong>Market access:</strong> The domestic market is small, and most entrepreneurs lack the networks and knowledge to access regional markets.</li>
    <li><strong>Legal and regulatory environment:</strong> Business registration, intellectual property protection, and contract enforcement remain challenging for new ventures.</li>
</ul>

<h2>Recommendations</h2>
<p>Based on our findings, we recommend establishing a dedicated startup fund with government and private co-investment, creating accelerator programs with regional market access components, and simplifying business registration processes for innovative ventures.</p>

<p>The potential is there. The Vientiane entrepreneurial ecosystem is at a critical inflection point. The decisions made in the next few years will shape the trajectory of Lao innovation for decades.</p>
""",
                "category": "academic",
                "tags": ["Entrepreneurship", "ASEAN", "Laos"],
                "is_featured": True,
            },
            {
                "title": "Teaching Strategic Management in the Lao Context",
                "subtitle": "Adapting Western frameworks for Southeast Asian realities",
                "excerpt": (
                    "Most strategic management textbooks are written for Western business contexts. "
                    "Here's how I adapt the content to make it relevant for Lao students."
                ),
                "content_raw": """
<p>When I first started teaching strategic management, I relied heavily on canonical Western textbooks — Porter's competitive framework, the BCG matrix, McKinsey's 7S model. These are powerful analytical tools, but they were developed in and for a very different business context.</p>

<h2>The Challenge of Context</h2>
<p>Lao businesses operate in an environment shaped by strong social networks, family ownership structures, rapidly changing government policy, and a regional economy increasingly influenced by China, Thailand, and Vietnam. Western frameworks often fail to capture these dynamics, or worse, lead students to misread situations by applying inappropriate assumptions.</p>

<h2>What I Do Instead</h2>
<p>I now structure my Strategic Management course around a mix of global frameworks and regional case studies. For every Western concept we introduce, we analyze at least one Lao or ASEAN company through that lens. This comparative approach helps students see both the value and the limitations of formal strategic tools.</p>

<p>Case studies from Thai family conglomerates, Vietnamese manufacturing companies, and Lao enterprises in tourism and agribusiness have proven particularly effective. Students see immediately how strategy plays out differently when family relationships, government connections, and cultural context are factored in.</p>

<h2>The Results</h2>
<p>Student engagement has improved noticeably since I adopted this approach. More importantly, graduates tell me they find themselves using these analytical skills in their work — which is, ultimately, what education is for.</p>
""",
                "category": "tutorial",
                "tags": ["Education", "Strategy", "ASEAN"],
                "is_featured": False,
            },
        ]

        for data in articles_data:
            slug = slugify(data["title"])[:240]
            if Article.objects.filter(slug=slug).exists():
                continue
            article = Article.objects.create(
                title=data["title"],
                subtitle=data.get("subtitle", ""),
                slug=slug,
                excerpt=data["excerpt"],
                content_raw=data["content_raw"],
                category=data["category"],
                is_featured=data.get("is_featured", False),
                status=Article.Status.PUBLISHED,
                published_at=timezone.now(),
            )
            for tname in data.get("tags", []):
                if tname in tags:
                    article.tags.add(tags[tname])
            self.stdout.write(f"  ✓ Article: {article.title[:60]}")

    # ──────────────────────────────────────────────────────────
    def _seed_resources(self):
        from apps.resources.models import Resource, ResourceCategory

        cats = [
            ("Lecture Notes", "lecture-notes"),
            ("Datasets", "datasets"),
            ("Templates", "templates"),
        ]

        categories = {}
        for name, slug in cats:
            c, _ = ResourceCategory.objects.get_or_create(slug=slug, defaults={"name": name})
            categories[slug] = c

        resources_data = [
            {
                "title": "Strategic Management Syllabus 2026",
                "category": "lecture-notes",
                "resource_type": "pdf",
                "description": "The complete course syllabus and reading list for BUS301 Strategic Management.",
                "author": "Dr. Venepheth Sayavong",
                "visibility": "public",
                "tags": "syllabus, strategy, 2026",
                "external_url": "https://example.com/syllabus.pdf",
            },
            {
                "title": "Lao SME Survey Dataset 2025",
                "category": "datasets",
                "resource_type": "dataset",
                "description": "Anonymized dataset from the 2025 survey of 200 SMEs in Vientiane Capital. Use for research purposes only.",
                "author": "Research Team",
                "visibility": "public",
                "tags": "data, sme, survey",
                "external_url": "https://example.com/dataset.csv",
            },
            {
                "title": "Business Plan Template v2",
                "category": "templates",
                "resource_type": "template",
                "description": "A comprehensive business plan template for startups and SMEs in Laos. Includes financial projection sheets.",
                "author": "Faculty of Business",
                "visibility": "public",
                "tags": "template, business plan, startup",
                "external_url": "https://example.com/template.docx",
            },
        ]

        for data in resources_data:
            slug = slugify(data["title"])[:240]
            if Resource.objects.filter(slug=slug).exists():
                continue
            res = Resource.objects.create(
                title=data["title"],
                slug=slug,
                category=categories[data["category"]],
                resource_type=data["resource_type"],
                description=data["description"],
                author=data["author"],
                visibility=data["visibility"],
                tags=data["tags"],
                external_url=data["external_url"],
            )
            self.stdout.write(f"  ✓ Resource: {res.title}")
