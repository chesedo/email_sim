import random

from faker import Faker

from dst.generator.user_manager import UserManager


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
        self.faker = Faker()
        Faker.seed(seed)

        self.user_manager = UserManager(self.faker)

    def generate_subject(self) -> str:
        """Generate a realistic email subject"""
        templates = ["Re: {}", "Fwd: {}", "{}", "{}", "{}"]  # Weight towards non-Re/Fwd

        subjects = [
            f"Updates on {random.choice(self.BUSINESS_WORDS)} {random.choice(self.BUSINESS_WORDS)}",
            f"Meeting: {random.choice(self.BUSINESS_WORDS)} Discussion",
            f"Proposal: {self.faker.bs()}",
            f"Question about {random.choice(self.BUSINESS_WORDS)}",
            f"{random.choice(self.BUSINESS_VERBS).title()} {random.choice(self.BUSINESS_WORDS)}",
            "Team Update",
            "Quick Question",
            f"Review: {self.faker.catch_phrase()}",
            f"{self.faker.month_name()} Newsletter",
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
