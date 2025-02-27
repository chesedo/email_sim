import logging
import random

from faker import Faker

from dst.email_clients import get_random_email_client
from dst.generator.user import User

logger = logging.getLogger("dst")


class UserManager:
    """Manages a pool of user for email simulation"""

    def __init__(self, faker: Faker):
        self._faker = faker
        self._users = []

        for _ in range(random.randint(1, 10)):
            self.add_random_user()

    def generate_user(self) -> User:
        """Generate a random user"""
        email = self._faker.email()

        while any(user.email == email for user in self._users):
            email = self._faker.email()

        user = User(
            first_name=self._faker.first_name(),
            last_name=self._faker.last_name(),
            email=email,
            company=self._faker.company() if random.random() > 0.5 else None,
            email_client=get_random_email_client(),
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
        logger.debug(f"Added user. Pool now has {len(self._users)} users")

    def remove_random_user(self) -> None:
        """Remove a random user from the pool"""
        index = random.randint(0, len(self._users) - 1)
        logger.debug(f"Removing user {self._users[index]}")

        self._users.pop(index)

        logger.debug(f"User removed. Pool now has {len(self._users)} users")

        if not self._users:
            logger.debug("No more users left so adding a new one")
            self.add_random_user()
