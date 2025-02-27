import random
from typing import Dict, Type

from dst.generator.user import User


class EmailClient:
    """Base class for email clients"""

    def generate_content(
        self, subject: str, sender: User, text_content: str
    ) -> tuple[str, str]:
        """
        Generate the text and HTML content of an email

        Args:
            faker: Faker instance to generate content
            subject: Subject of the email
            sender: User sending the email
            previous_email: Tuple containing the text and HTML content of the previous email

        Returns:
            Tuple containing the text and HTML content
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        """Return a small but detailed representation of the email client"""
        return self.__class__.__name__


# Registry of available email clients
_email_client_registry: Dict[str, Type[EmailClient]] = {}


def register_email_client(cls: Type[EmailClient]):
    """Decorator to register an email client"""
    _email_client_registry[cls.__name__] = cls
    return cls


def get_random_email_client() -> EmailClient:
    """Get a random email client"""
    if not _email_client_registry:
        # Import clients to register them
        from . import default_client  # noqa
        from . import gmail  # noqa
        from . import outlook  # noqa

    client_class = random.choice(list(_email_client_registry.values()))

    return client_class()
