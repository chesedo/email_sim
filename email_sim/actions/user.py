import logging
import random

from email_sim.actions import SimulationAction, register_action
from email_sim.controller import DockerTimeController
from email_sim.generator import DataGenerator

logger = logging.getLogger("dst")


@register_action
class AddUser(SimulationAction):
    """Adds a new user to the user pool"""

    @property
    def weight(self) -> float:
        """Define the weight for this action"""
        return 0.2  # Lower weight as we don't want to add users too frequently

    def __call__(
        self, controller: DockerTimeController, data_generator: DataGenerator
    ) -> bool:
        try:
            data_generator.user_manager.add_random_user()

            return True

        except Exception as e:
            logger.error(f"Error adding user: {e}[/]")
            return False


@register_action
class RemoveUser(SimulationAction):
    """Removes a user from the user pool"""

    @property
    def weight(self) -> float:
        """Define the weight for this action"""
        return 0.1  # Even lower weight as we want to maintain some users2

    def __call__(
        self, controller: DockerTimeController, data_generator: DataGenerator
    ) -> bool:
        try:
            data_generator.user_manager.remove_random_user()

            return True

        except Exception as e:
            logger.error(f"Error removing user: {e}[/]")
            return False


@register_action
class ModifyUser(SimulationAction):
    """Modifies a user in the user pool"""

    @property
    def weight(self) -> float:
        """Define the weight for this action"""
        return 0.15  # Medium weight compared to the above

    def __call__(
        self, controller: DockerTimeController, data_generator: DataGenerator
    ) -> bool:
        try:
            user = data_generator.user_manager.get_random_user()

            logger.debug(f"Modifying user: {user}")

            # Determine what to modify
            modification_type = random.choice(["email", "name", "company", "all"])

            logger.debug(f"Modifying {modification_type}")

            if modification_type == "email" or modification_type == "all":
                user.email = data_generator.faker.email()

            if modification_type == "name" or modification_type == "all":
                user.first_name = data_generator.faker.first_name()
                user.last_name = data_generator.faker.last_name()

            if modification_type == "company" or modification_type == "all":
                user.company = (
                    data_generator.faker.company() if random.random() > 0.5 else None
                )

            logger.debug(f"Modified user: {user}")

            return True

        except Exception as e:
            logger.error(f"Error modifying user: {e}[/]")
            return False
