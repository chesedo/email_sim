import logging
import random
from dataclasses import dataclass
from typing import Optional

from faker import Faker

logger = logging.getLogger("dst")


@dataclass
class User:
    first_name: str
    last_name: str
    email: str
    company: Optional[str] = None


class UserManager:
    """Manages a pool of user for email simulation"""

    def __init__(self, faker: Faker):
        self._faker = faker
        self._users = []

        for _ in range(random.randint(1, 10)):
            self.add_random_user()

    def generate_user(self) -> User:
        """Generate a random user"""
        user = User(
            first_name=self._faker.first_name(),
            last_name=self._faker.last_name(),
            email=self._faker.email(),
            company=self._faker.company() if random.random() > 0.5 else None,
        )

        logger.debug(f"Generated user: {user}")

        return user

    def get_random_user(self) -> User:
        """Get a random user from the pool"""
        user = random.choice(self._users)

        logger.debug(f"Selected user: {user}")

        return user

    def add_random_user(self) -> None:
        """Add a random user to the pool"""
        self._users.append(self.generate_user())

    def remove_random_user(self) -> None:
        """Remove a random user from the pool"""
        index = random.randint(0, len(self._users) - 1)
        logger.debug(f"Removing user {self._users[index]}")

        self._users.pop(index)

        if not self._users:
            logger.debug("No more users left so adding a new one")
            self.add_random_user()
