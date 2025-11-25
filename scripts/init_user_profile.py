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
    """Extract text from PDF CV - using actual CV content."""
    # Real CV content extracted from Resume-Vanja-Petreski.pdf
    return """
VANJA PETRESKI
Principal Software Engineer | AI-Native Development · Backend Architecture | Java · Kotlin · Spring Boot · AWS · LLMs
vanja@petreski.co | LinkedIn

SUMMARY
================================================================================
With two decades of experience in software engineering and architecture, I specialize in building scalable backend
systems and integrating AI/LLM capabilities into production applications. My expertise spans traditional enterprise
development (Java, Kotlin, Spring Boot) and modern AI-native engineering practices (Python, FastAPI, Claude Code, Cursor).

I architect event-driven microservices, design RESTful and GraphQL APIs, and leverage AWS cloud infrastructure to
deliver high-performance solutions across fintech, healthcare, and other industries. Recently, I've focused on pioneering
AI-native development workflows, achieving 3-5x productivity improvements through tools like Claude Code, Cursor,
and direct LLM API integration.

As a principal engineer, I balance deep technical expertise with strategic thinking—designing systems that scale,
mentoring teams, and driving adoption of emerging technologies. I'm passionate about solving complex problems and
building products that make a meaningful impact.

EXPERIENCE
================================================================================

Principal Software Engineer | Petreski LLC | Apr '24 — Present | United States (Remote)
Building scalable backend systems and AI-integrated applications for fintech and property management sectors.
Tech: Java, Kotlin, Spring Boot, Python, FastAPI, Flutter, Dart, Firebase, Kafka, AWS, OpenAI, Anthropic Claude,
Claude Code, Cursor, GitHub Copilot.

• Designed and implemented payment processing backend and transaction management systems using Java and Spring Boot
  for Chicago-based fintech platform.
• Developed backend services and API integrations for property management software using Python and FastAPI.
• Built full-stack iOS budgeting application using Flutter, Dart, and Firebase with integrated Claude AI for automated
  financial insights and recommendations.
• Integrated AI-powered features using OpenAI and Anthropic Claude APIs for production applications.
• Established AI-native development practices leveraging Claude Code and Cursor for 3-5x productivity gains.
• Architected event-driven microservices on AWS with Kafka for scalability and reliability.

Principal Software Engineer | Nagarro | Feb '21 — Apr '24 | United States (Remote)
Architecting and developing AWS infrastructure, Internet of Things (IoT) solutions, backend services, and security for a
wellness company that provides experiential health therapy.
Tech: REST, gRPC, Java, Kotlin, Gradle, Maven, Spring Boot, Spring Security, Vue.js, TypeScript, Keycloak, CI/CD,
DevOps, Open AI, AWS IoT, CloudFormation, ECS, Fargate, RDS, S3.

• Architected and scaled an AI-driven health industry platform, integrating LED-lighting, sound, and heating systems,
  achieving a user base of 50,000 active participants.

Principal Software Engineer | Moody's Analytics | Dec '16 — Feb '21 | United States (Remote)
Creating a set of tools, libraries, frameworks, backends and standards to accelerate new application development and
maintain/align code consistency and way of doing things across applications and teams.
Tech: Java, Kotlin, Spring Boot, GraphQL, Docker, Kubernetes, AWS.

• Directed two teams of 10 engineers in the development of a risk management platform, resulting in a 40% reduction
  in project delivery time.

Software Architect | X-Team | Jul '13 — Dec '16 | United States (Remote)
Working on complex Microservices to integrate with Federal Reserve banking system and provide modern backend
services and APIs to fintechs and banks.
Tech: Java, Spring, AWS.

• Designed and implemented an event-driven Fintech architecture leveraging Kafka, enhancing data processing
  efficiency by 30%.

Staff Software Engineer | Riot Games | Jan '10 — Jul '13 | United States
Software architect and engineer developing awesome experiences and products optimized for Riot's players.
Tech: Java, Spring, AWS, Terraform.

• Developed a custom Jira plugin that enhanced QA workflow efficiency, resulting in a 15% increase in productivity.

Senior Software Engineer | Kindred Group | Dec '06 — Jan '10 | Estonia (Remote)
Software development of Java backend system to support online gambling business, integration with payment and gaming
providers and back-office development.
Tech: Spring, Hibernate, Maven, PostgreSQL, BigData, New Relic, reporting, SQL, DevOps.

• Orchestrated the overhaul of legacy gaming systems using advanced technologies, significantly reducing maintenance
  costs and improving user experience.

Software Engineer | Asseco Group | Oct '04 — Dec '06 | Serbia and Montenegro
Architecture, development and DevOps of anti-money laundry software for the Ministry of Finance of the Republic of
Serbia using Java, JEE, EJB3, MDB, JPA, Oracle AS, JSF and ADF.
Deployment of production system in a super computing environment.

• Led the development of an AML system using event-driven architecture, enhancing system responsiveness and scalability.

EDUCATION
================================================================================
Master in Computer Science | University of Belgrade, School of Electrical Engineering | 2001 — 2006 | Serbia and Montenegro
Electrical Engineering with focus on Computer Science

CERTIFICATIONS
================================================================================
• AWS Certified Solutions Architect – Associate, AWS
• AWS Certified Developer – Associate, AWS
• Kotlin for Java Developers, Coursera
• Entrepreneurship, Innovation & Digital Marketing, Harvard Business School Online

SKILLS
================================================================================
SWE: Java, Kotlin, Spring Boot, Python, FastAPI, AWS, Software Architecture, Technical Leadership, AI
Business: Entrepreneurship, Startups, Design Thinking, Innovation, Digital Marketing, Indie Hacking

WORK PREFERENCES
================================================================================
• Location: Colombia (Colombian and Serbian citizenship, NO US work authorization)
• Work Type: Full-time remote contractor via Petreski LLC
• Rate: $10,000 USD/month
• Industries: Fintech, Healthcare, SaaS, AI/ML, Enterprise Software
• Availability: Immediate
• Timezone: Flexible (Colombia UTC-5, can overlap with US/EU hours)
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
                # Core Backend (20 years experience)
                "Java",
                "Kotlin",
                "Spring Boot",
                "Spring Security",
                "Microservices",
                "Event-Driven Architecture",
                "REST APIs",
                "GraphQL",
                "gRPC",

                # Modern AI-Native Development
                "Python",
                "FastAPI",
                "Claude Code",
                "Cursor",
                "Claude API",
                "OpenAI API",
                "LLM Integration",
                "AI-Native Development",

                # Cloud & Infrastructure
                "AWS",
                "AWS IoT",
                "CloudFormation",
                "ECS",
                "Fargate",
                "RDS",
                "S3",
                "Docker",
                "Kubernetes",
                "Terraform",

                # Databases & Messaging
                "PostgreSQL",
                "MySQL",
                "MongoDB",
                "Redis",
                "Kafka",
                "BigData",

                # Frontend (when needed)
                "Vue.js",
                "TypeScript",
                "Flutter",
                "Dart",
                "Firebase",

                # DevOps & Tools
                "CI/CD",
                "DevOps",
                "Git",
                "GitHub Actions",
                "Maven",
                "Gradle",

                # Architecture & Leadership
                "Software Architecture",
                "Technical Leadership",
                "Team Leadership",
                "System Design",
                "Fintech",
                "Healthcare",
                "IoT",
            ],
            preferences={
                "rate_monthly": 10000,
                "min_rate": 8000,
                "max_rate": 15000,
                "remote_only": True,
                "contractor_only": True,
                "location_restrictions": "NO US work authorization - must accept international contractors or hire in Latam/Colombia",
                "preferred_industries": ["Fintech", "Healthcare", "SaaS", "AI/ML", "Enterprise Software"],
                "company_size": ["startup", "scale-up", "enterprise"],
                "willing_to_relocate": False,
                "citizenship": ["Colombia", "Serbia"],
                "timezone": "UTC-5 (Colombia)",
                "availability": "Immediate",
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
