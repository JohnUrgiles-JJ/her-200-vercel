"""Seed demo data: 12 mentors and 2 mentees, all fictional, all with password "demo1234".

    python manage.py seed           # create or update the demo users (safe to run repeatedly)
    python manage.py seed --reset   # also delete every Question, QuestionMatch and Answer first

Users are keyed on their demo address, which is stored as `username` (the login key). Running the
command again updates the same rows, so there are never duplicates, and each user keeps its token.

Optional env var SEED_REAL_EMAILS (read from the environment or backend/.env):
    SEED_REAL_EMAILS="maya@demo.com=teammate@gmail.com,priya@demo.com=other@gmail.com"
For each pair, that seeded mentor's `User.email` (where notification emails go) is set to the real
address. `username` stays the demo address, so login still uses maya@demo.com / demo1234.
Mentors not listed get their demo address back as `User.email`.
"""

import os

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from rest_framework.authtoken.models import Token

from core.models import Answer, MentorProfile, Profile, Question, QuestionMatch

PASSWORD = "demo1234"

MENTORS = [
    {
        "email": "maya@demo.com",
        "full_name": "Maya Chen",
        "headline": "UX Designer",
        "company": "Figma",
        "fields": "UX, product design, Figma, user research, accessibility",
        "open_to": "career switching, portfolios, breaking in without a degree",
        "experience_years": 6,
        "bio": (
            "I taught middle-school art for four years before switching careers into UX, with no design "
            "degree, just online courses and a portfolio of redesigns for local nonprofits. My first role "
            "came from a case study about making a school sign-up form accessible. Now I design "
            "collaboration features at Figma and love helping career switchers tell their story."
        ),
    },
    {
        "email": "priya@demo.com",
        "full_name": "Priya Nair",
        "headline": "Data Scientist",
        "company": "Spotify",
        "fields": "data science, Python, machine learning, statistics, SQL",
        "open_to": "grad school, internships, research",
        "experience_years": 5,
        "bio": (
            "I moved to the U.S. from Kerala for a master's in statistics and landed my first internship "
            "after cold-emailing a professor whose research lab needed help cleaning data. Today I build "
            "recommendation models at Spotify. I'm happy to talk through grad school applications, "
            "funding, and turning a research project into an industry internship."
        ),
    },
    {
        "email": "sofia@demo.com",
        "full_name": "Sofia Martinez",
        "headline": "Software Engineer",
        "company": "Microsoft",
        "fields": "backend, Python, Django, APIs, cloud",
        "open_to": "first job, technical interviews, imposter syndrome",
        "experience_years": 4,
        "bio": (
            "I was the first in my family to go to college and the only Latina in most of my CS classes. "
            "I failed my first six technical interviews before something clicked, and I learned more from "
            "those rejections than from any course. Now I build backend APIs at Microsoft and still deal "
            "with imposter syndrome, so let's talk about it honestly."
        ),
    },
    {
        "email": "amara@demo.com",
        "full_name": "Amara Okafor",
        "headline": "Cybersecurity Analyst",
        "company": "JPMorgan Chase",
        "fields": "cybersecurity, networking, security certifications",
        "open_to": "certifications, getting started, first-gen experience",
        "experience_years": 7,
        "bio": (
            "My parents immigrated from Nigeria, and I was the first in my family to graduate college. I "
            "started on a help desk, earned Security+ and then CySA+ while working full time, and moved "
            "into the security operations center at JPMorgan Chase. I can help you pick the right "
            "certification and study for it on a budget."
        ),
    },
    {
        "email": "elena@demo.com",
        "full_name": "Elena Rossi",
        "headline": "Product Manager",
        "company": "Etsy",
        "fields": "product management, strategy, startups, roadmaps",
        "open_to": "PM interviews, switching from engineering to product",
        "experience_years": 8,
        "bio": (
            "I spent four years as a backend engineer at two early-stage startups before switching from "
            "engineering to product. The move happened because I kept volunteering to talk to customers "
            "and write specs. Now I'm a PM at Etsy working on seller tools, and I enjoy prepping people "
            "for product-sense and execution interviews."
        ),
    },
    {
        "email": "jasmine@demo.com",
        "full_name": "Jasmine Lee",
        "headline": "Front-End Engineer",
        "company": "Squarespace",
        "fields": "React, JavaScript, web development, accessibility",
        "open_to": "bootcamps, portfolios, first job",
        "experience_years": 3,
        "bio": (
            "I worked as a restaurant manager until I was 27, then did a 16-week coding bootcamp at night "
            "while still working shifts. I sent over 100 applications before landing my first front-end "
            "job, and the portfolio project that got me hired was a screen-reader-friendly menu app. I "
            "now build React components at Squarespace."
        ),
    },
    {
        "email": "fatima@demo.com",
        "full_name": "Fatima Hassan",
        "headline": "AI/ML Engineer",
        "company": "IBM",
        "fields": "artificial intelligence, LLMs, deep learning, research",
        "open_to": "AI careers, research, grad school",
        "experience_years": 6,
        "bio": (
            "I grew up in Cairo and came to the U.S. for a PhD in computer science, where I researched "
            "neural networks for Arabic speech recognition. After defending, I chose industry over "
            "academia and now work on large language model evaluation at IBM. I can help you decide "
            "between a master's, a PhD, or going straight into AI work."
        ),
    },
    {
        "email": "grace@demo.com",
        "full_name": "Grace Kim",
        "headline": "Health Tech Analyst",
        "company": "Mount Sinai",
        "fields": "health tech, informatics, data analysis, healthcare",
        "open_to": "non-traditional paths, career switching",
        "experience_years": 5,
        "bio": (
            "I was an ICU nurse for six years before I started teaching myself SQL to fix the clunky "
            "reports on my unit. That side project turned into a health informatics certificate and a "
            "switch into analytics at Mount Sinai. If you're coming from healthcare or another "
            "non-traditional path, your domain knowledge is a superpower."
        ),
    },
    {
        "email": "valeria@demo.com",
        "full_name": "Valeria Cruz",
        "headline": "Cloud Engineer",
        "company": "Amazon Web Services",
        "fields": "cloud, AWS, DevOps, infrastructure",
        "open_to": "certifications, first-gen students, community college",
        "experience_years": 4,
        "bio": (
            "I started at community college while working at my family's laundromat, then transferred to "
            "a state university as a first-gen student. Earning my AWS Solutions Architect certification "
            "before graduating is what got me noticed by recruiters. Now I'm a cloud engineer at AWS "
            "helping teams automate their infrastructure."
        ),
    },
    {
        "email": "nadia@demo.com",
        "full_name": "Nadia Brooks",
        "headline": "Quality Engineer",
        "company": "Bloomberg",
        "fields": "software testing, QA, automation",
        "open_to": "entry-level roles, interviews",
        "experience_years": 3,
        "bio": (
            "I majored in psychology and started out doing manual QA testing through a contract agency "
            "after graduation. I taught myself Python and Selenium on my lunch breaks, automated half of "
            "my team's regression suite, and got hired full time at Bloomberg. QA is a great "
            "entry-level door into tech, and I'm happy to show you how to walk through it."
        ),
    },
    {
        "email": "rosa@demo.com",
        "full_name": "Rosa Delgado",
        "headline": "IT Support Specialist",
        "company": "NYC Health + Hospitals",
        "fields": "IT support, help desk, networking, hardware",
        "open_to": "breaking into tech without a degree, certifications",
        "experience_years": 5,
        "bio": (
            "I left work for eight years to raise my kids and care for my mother, then returned to work "
            "by earning the CompTIA A+ through a free library program. I don't have a college degree, "
            "and I've been in hospital IT support for five years now, keeping clinicians' devices and "
            "networks running. You can absolutely break into tech without a degree."
        ),
    },
    {
        "email": "hannah@demo.com",
        "full_name": "Hannah Wright",
        "headline": "Technology Strategy Associate",
        "company": "BNY",
        "fields": "business strategy, consulting, fintech",
        "open_to": "consulting, finance careers in tech, résumés",
        "experience_years": 2,
        "bio": (
            "I studied economics at a small liberal arts college with no recruiting pipeline to Wall "
            "Street, so I built my own network through alumni coffee chats. I spent a year at a boutique "
            "consulting firm before joining BNY's technology strategy team. I review a lot of résumés and "
            "can help you translate your experience for consulting and fintech roles."
        ),
    },
]

MENTEES = [
    {"email": "student1@demo.com", "full_name": "Maria Lopez"},
    {"email": "student2@demo.com", "full_name": "Aisha Rahman"},
]


def parse_real_emails(raw, mentor_emails):
    """Parse "demo@x=real@y,..." into {demo: real}. Raises CommandError on malformed input."""
    mapping = {}
    for chunk in (raw or "").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.count("=") != 1:
            raise CommandError(f'SEED_REAL_EMAILS: "{chunk}" must look like demo@demo.com=real@example.com')
        demo, real = (part.strip().lower() for part in chunk.split("="))
        if demo not in mentor_emails:
            raise CommandError(f'SEED_REAL_EMAILS: "{demo}" is not one of the seeded mentor addresses.')
        try:
            validate_email(real)
        except ValidationError:
            raise CommandError(f'SEED_REAL_EMAILS: "{real}" is not a valid email address.')
        mapping[demo] = real
    return mapping


class Command(BaseCommand):
    help = "Create or update the ConnectHER demo users (12 mentors, 2 mentees). Safe to run repeatedly."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all Questions, QuestionMatches and Answers before seeding. Users are kept and updated.",
        )

    def handle(self, *args, **options):
        real_emails = parse_real_emails(
            os.environ.get("SEED_REAL_EMAILS", ""), {m["email"] for m in MENTORS}
        )

        rows = []
        with transaction.atomic():
            if options["reset"]:
                answers = Answer.objects.count()
                matches = QuestionMatch.objects.count()
                questions = Question.objects.count()
                Answer.objects.all().delete()
                QuestionMatch.objects.all().delete()
                Question.objects.all().delete()
                self.stdout.write(
                    f"--reset: deleted {questions} questions, {matches} matches, {answers} answers."
                )

            for m in MENTORS:
                user, token, created = self._upsert_user(m["email"], m["full_name"], "mentor", real_emails)
                MentorProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "headline": m["headline"],
                        "company": m["company"],
                        "fields": m["fields"],
                        "open_to": m["open_to"],
                        "bio": m["bio"],
                        "experience_years": m["experience_years"],
                        "is_active": True,
                    },
                )
                rows.append((m["email"], "mentor", token.key, created, user.email))

            for m in MENTEES:
                user, token, created = self._upsert_user(m["email"], m["full_name"], "mentee", real_emails)
                # A mentee should never carry a mentor profile (e.g. if the row was edited in admin).
                MentorProfile.objects.filter(user=user).delete()
                rows.append((m["email"], "mentee", token.key, created, user.email))

        self._print_summary(rows)

    def _upsert_user(self, demo_email, full_name, role, real_emails):
        first, _, last = full_name.partition(" ")
        user, created = User.objects.update_or_create(
            username=demo_email,
            defaults={
                "email": real_emails.get(demo_email, demo_email),
                "first_name": first,
                "last_name": last,
                "is_active": True,
            },
        )
        user.set_password(PASSWORD)
        user.save(update_fields=["password"])
        Profile.objects.update_or_create(user=user, defaults={"role": role, "full_name": full_name})
        token, _ = Token.objects.get_or_create(user=user)  # keep the same token across runs
        return user, token, created

    def _print_summary(self, rows):
        created = sum(1 for r in rows if r[3])
        mentors = Profile.objects.filter(role="mentor", user__username__in=[r[0] for r in rows]).count()
        mentees = Profile.objects.filter(role="mentee", user__username__in=[r[0] for r in rows]).count()

        login_w = max(len("login email"), *(len(r[0]) for r in rows))
        header = f"{'login email':<{login_w}}  {'role':<6}  {'password':<8}  {'token':<40}  notifications go to"
        self.stdout.write("")
        self.stdout.write(header)
        self.stdout.write("-" * len(header))
        for login, role, key, _, notify in rows:
            note = notify if notify != login else "(same)"
            self.stdout.write(f"{login:<{login_w}}  {role:<6}  {PASSWORD:<8}  {key:<40}  {note}")
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {mentors} mentors and {mentees} mentees "
                f"({created} created, {len(rows) - created} updated)."
            )
        )
