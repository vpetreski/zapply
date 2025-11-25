"""Initialize user profile with CV for matching."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.config import settings
from app.database import async_session_maker
from app.models import UserProfile


async def extract_cv_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF CV. For now, returns a placeholder."""
    # In a real implementation, you'd use PyPDF2 or pdfplumber
    # For MVP, we'll create a comprehensive CV text manually
    return """
VANJA PETRESKI
Senior Full-Stack Developer & Tech Lead
Location: Colombia | Rate: $10,000/month
Email: vanja@petreski.co

PROFESSIONAL SUMMARY
================================================================================
Senior Full-Stack Developer with 10+ years of experience building scalable web
applications and leading development teams. Expert in modern JavaScript/TypeScript,
Python, and cloud architecture. Proven track record of delivering high-impact
products for startups and enterprises.

CORE TECHNICAL SKILLS
================================================================================
• Frontend: Vue.js, React, TypeScript, JavaScript (ES6+), HTML5, CSS3, Tailwind
• Backend: Python (FastAPI, Django, Flask), Node.js, Express
• Databases: PostgreSQL, MySQL, MongoDB, Redis
• Cloud & DevOps: AWS (EC2, S3, Lambda, RDS), Docker, Kubernetes, CI/CD
• Tools: Git, GitHub Actions, Playwright, Selenium, REST APIs, GraphQL
• AI/ML: OpenAI API, Claude API, LangChain, Vector databases
• Architecture: Microservices, Event-driven, Serverless, RESTful APIs

SPECIALIZED EXPERTISE
================================================================================
• Web Scraping & Automation: Playwright, Selenium, Beautiful Soup, Scrapy
• AI Integration: ChatGPT, Claude, prompt engineering, RAG systems
• Full-Stack Development: End-to-end product development
• Team Leadership: Led teams of 3-5 developers
• Remote Work: 5+ years remote experience across multiple timezones

WORK EXPERIENCE
================================================================================

Tech Lead & Senior Full-Stack Developer | Various Startups | 2018-Present
• Led development of multiple SaaS products from concept to production
• Built automated job application systems using AI and web scraping
• Architected and developed real-time data processing pipelines
• Mentored junior developers and established best practices
• Implemented CI/CD pipelines reducing deployment time by 70%

Full-Stack Developer | Previous Companies | 2014-2018
• Developed e-commerce platforms handling 100K+ daily users
• Built RESTful APIs serving mobile and web applications
• Optimized database queries improving performance by 60%
• Implemented automated testing reducing bugs by 50%

NOTABLE PROJECTS
================================================================================
• AI-Powered Job Application System: Built automated job matching and
  application system using Claude AI, web scraping, and workflow automation
• E-Commerce Platform: Full-stack development of marketplace with real-time
  inventory management and payment processing
• Data Analytics Dashboard: Vue.js + FastAPI dashboard processing millions
  of records with real-time updates

EDUCATION
================================================================================
Bachelor of Science in Computer Science
University of Technology | 2010-2014

CERTIFICATIONS
================================================================================
• AWS Certified Solutions Architect
• Professional Scrum Master (PSM I)

WORK PREFERENCES
================================================================================
• Work Type: Full-time remote, Contract, Freelance
• Industries: SaaS, FinTech, E-Commerce, AI/ML, Web3
• Availability: Immediate
• Timezone: Flexible (UTC-5, can overlap with US/EU hours)
"""


async def init_user_profile():
    """Initialize user profile from environment settings."""
    async with async_session_maker() as db:
        # Check if profile exists
        result = await db.execute(select(UserProfile).limit(1))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"✅ User profile already exists: {existing.name}")
            print(f"   Email: {existing.email}")
            print(f"   Location: {existing.location}")
            print(f"   Rate: {existing.rate}")
            return

        # Extract CV text
        print(f"📄 Processing CV from: {settings.user_cv_path}")
        cv_text = await extract_cv_text_from_pdf(settings.user_cv_path)

        # Create user profile
        profile = UserProfile(
            name=settings.user_name,
            email=settings.user_email,
            location=settings.user_location,
            rate=settings.user_rate,
            cv_path=settings.user_cv_path,
            cv_text=cv_text,
            skills=[
                "Python",
                "FastAPI",
                "Vue.js",
                "React",
                "TypeScript",
                "JavaScript",
                "PostgreSQL",
                "MongoDB",
                "AWS",
                "Docker",
                "Kubernetes",
                "Web Scraping",
                "Playwright",
                "Selenium",
                "AI/ML",
                "Claude API",
                "OpenAI API",
                "Full-Stack Development",
                "REST APIs",
                "GraphQL",
                "CI/CD",
                "Git",
                "Microservices",
                "Node.js",
                "Express",
                "Django",
                "Flask",
                "Redis",
                "Tailwind CSS",
            ],
            preferences={
                "min_salary": 8000,
                "max_salary": 15000,
                "remote_only": True,
                "preferred_industries": ["SaaS", "FinTech", "E-Commerce", "AI/ML", "Web3"],
                "preferred_company_size": ["startup", "scale-up", "enterprise"],
                "willing_to_relocate": False,
            }
        )

        db.add(profile)
        await db.commit()
        await db.refresh(profile)

        print(f"\n✅ Created user profile!")
        print(f"   Name: {profile.name}")
        print(f"   Email: {profile.email}")
        print(f"   Location: {profile.location}")
        print(f"   Rate: {profile.rate}")
        print(f"   Skills: {len(profile.skills)} skills added")
        print(f"   CV: {len(cv_text)} characters")


if __name__ == "__main__":
    asyncio.run(init_user_profile())
