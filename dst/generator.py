import html
import random
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from faker import Faker
from jinja2 import BaseLoader, Environment


@dataclass
class User:
    first_name: str
    last_name: str
    email: str
    company: Optional[str] = None


@dataclass
class GeneratedEmail:
    sender: User
    recipient: User
    subject: str
    text_content: str
    html_content: str
    date: datetime

    def build_email(self) -> EmailMessage:
        """Build an EmailMessage object from the generated email"""
        msg = EmailMessage()

        # Set the standard headers
        msg["From"] = (
            f"{self.sender.first_name} {self.sender.last_name} <{self.sender.email}>"
        )
        msg["To"] = (
            f"{self.recipient.first_name} {self.recipient.last_name} <{self.recipient.email}>"
        )
        msg["Subject"] = self.subject
        msg["Date"] = self.date.strftime("%a, %d %b %Y %H:%M:%S +0000")

        # Create multipart message
        msg_alternative = MIMEMultipart("alternative")
        msg_alternative.attach(MIMEText(self.text_content, "plain"))
        msg_alternative.attach(MIMEText(self.html_content, "html"))

        # Attach the multipart content to the message
        msg.set_content(msg_alternative)

        return msg


class DataGenerator:
    # Sample business words for content generation
    BUSINESS_WORDS = [
        "synergy",
        "strategy",
        "innovation",
        "optimization",
        "solution",
        "implementation",
        "analytics",
        "framework",
        "methodology",
        "initiative",
        "deployment",
        "infrastructure",
        "integration",
        "scalability",
        "productivity",
        "collaboration",
        "efficiency",
        "sustainability",
        "development",
        "management",
    ]

    BUSINESS_VERBS = [
        "implement",
        "optimize",
        "strategize",
        "develop",
        "analyze",
        "coordinate",
        "facilitate",
        "integrate",
        "leverage",
        "streamline",
        "enhance",
        "maximize",
        "innovate",
        "transform",
        "utilize",
        "deploy",
        "scale",
        "generate",
        "evaluate",
        "restructure",
    ]

    # Sample email templates
    EMAIL_TEMPLATES = {
        "basic": """
            <html>
            <body>
                <div style="font-family: Arial, sans-serif;">
                    <p>{{ text_content }}</p>
                    {% if signature %}
                    <br/>
                    <div style="color: #666;">
                        {{ signature }}
                    </div>
                    {% endif %}
                </div>
            </body>
            </html>
        """,
        "newsletter": """
            <html>
            <body>
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h1 style="color: #333;">{{ subject }}</h1>
                    <div style="padding: 20px;">
                        {{ text_content }}
                    </div>
                    {% if signature %}
                    <div style="border-top: 1px solid #eee; padding-top: 20px; color: #666;">
                        {{ signature }}
                    </div>
                    {% endif %}
                </div>
            </body>
            </html>
        """,
    }

    def __init__(self, seed: int):
        """Initialize the data generator with an optional seed for reproducibility"""
        self.fake = Faker()
        Faker.seed(seed)

    def generate_user(self) -> User:
        """Generate a random user with realistic data"""
        profile = self.fake.profile()
        return User(
            first_name=self.fake.first_name(),
            last_name=self.fake.last_name(),
            email=profile["mail"],
            company=self.fake.company() if random.random() > 0.5 else None,
        )

    def generate_signature(self, user: User) -> str:
        """Generate an email signature for a user"""
        signature_parts = [
            f"{user.first_name} {user.last_name}",
        ]
        if user.company:
            signature_parts.append(user.company)
        signature_parts.append(user.email)

        return "\n".join(signature_parts)

    def generate_subject(self) -> str:
        """Generate a realistic email subject"""
        templates = ["Re: {}", "Fwd: {}", "{}", "{}", "{}"]  # Weight towards non-Re/Fwd

        subjects = [
            f"Updates on {random.choice(self.BUSINESS_WORDS)} {random.choice(self.BUSINESS_WORDS)}",
            f"Meeting: {random.choice(self.BUSINESS_WORDS)} Discussion",
            f"Proposal: {self.fake.bs()}",
            f"Question about {random.choice(self.BUSINESS_WORDS)}",
            f"{random.choice(self.BUSINESS_VERBS).title()} {random.choice(self.BUSINESS_WORDS)}",
            "Team Update",
            "Quick Question",
            f"Review: {self.fake.catch_phrase()}",
            f"{self.fake.month_name()} Newsletter",
        ]

        template = random.choice(templates)
        subject = random.choice(subjects)

        return template.format(subject)

    def generate_paragraph(self) -> str:
        """Generate a random business-like paragraph"""
        num_sentences = random.randint(2, 4)
        sentences = []

        for _ in range(num_sentences):
            template = random.choice(
                [
                    "We need to {} the {} {}.",
                    "The {} {} requires immediate {}.",
                    "Please review the {} {} proposal.",
                    "Let's schedule a meeting to discuss {} {}.",
                    "I'd like to get your thoughts on the {} {}.",
                    "We've made progress on {} the {} {}.",
                    "The team has been working on {} {}.",
                    "Could you provide feedback on the {} {}?",
                ]
            )

            words = [
                random.choice(self.BUSINESS_VERBS),
                random.choice(self.BUSINESS_WORDS),
                random.choice(self.BUSINESS_WORDS),
            ]

            sentences.append(template.format(*words))

        return " ".join(sentences)

    def generate_text_content(self, paragraphs: int = 3) -> str:
        """Generate somewhat realistic text content"""
        return "\n\n".join(self.generate_paragraph() for _ in range(paragraphs))

    def generate_email(
        self, date: datetime, sender: User = None, recipient: User = None
    ) -> GeneratedEmail:
        """Generate a complete email message"""
        if sender is None:
            sender = self.generate_user()
        if recipient is None:
            recipient = self.generate_user()

        subject = self.generate_subject()

        # Generate content
        text_content = self.generate_text_content()
        signature = self.generate_signature(sender)
        text_content_with_signature = f"{text_content}\n\n--\n{signature}"

        # Create HTML version using a random template
        template_key = random.choice(list(self.EMAIL_TEMPLATES.keys()))
        template = Environment(loader=BaseLoader()).from_string(
            self.EMAIL_TEMPLATES[template_key]
        )
        html_content = template.render(
            subject=html.escape(subject),
            text_content=html.escape(text_content).replace("\n", "<br/>"),
            signature=html.escape(signature).replace("\n", "<br/>"),
        )

        return GeneratedEmail(
            sender=sender,
            recipient=recipient,
            subject=subject,
            text_content=text_content_with_signature,
            html_content=html_content,
            date=date,
        )
