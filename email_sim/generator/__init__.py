import random

from faker import Faker

from email_sim.generator.user_manager import UserManager


class DataGenerator:
    def __init__(self, seed: int):
        """Initialize the data generator with an optional seed for reproducibility"""
        self.faker = Faker()
        Faker.seed(seed)

        self.user_manager = UserManager(self.faker)

        # Set up email subject prefix weights
        self.prefix_options = ["", "Re: ", "Fwd: "]
        self.prefix_weights = [0.7, 0.2, 0.1]  # 70% normal, 20% reply, 10% forward

    def generate_subject(self) -> str:
        """Generate an email subject with properly weighted prefixes"""
        # Use the weighted choice for the prefix
        prefix = random.choices(self.prefix_options, weights=self.prefix_weights, k=1)[0]

        subject_content = self.faker.sentence(nb_words=random.randint(3, 8)).rstrip('.')

        return f"{prefix}{subject_content}"

    def generate_paragraph(self) -> str:
        """Generate a simple paragraph of text"""
        # Simply use faker's built-in text generator
        return self.faker.text(max_nb_chars=random.randint(150, 300))

    def generate_text_content(self, paragraphs: int = 3) -> str:
        """Generate text content with multiple paragraphs"""
        return "\n\n".join(self.generate_paragraph() for _ in range(paragraphs))
