import logging

from email_sim.actions import SimulationAction, register_action
from email_sim.controller import DockerTimeController
from email_sim.generator import DataGenerator

logger = logging.getLogger("dst")


@register_action
class AdvanceTime(SimulationAction):
    """Advances time by a random duration"""

    def __call__(
        self, controller: DockerTimeController, data_generator: DataGenerator
    ) -> bool:
        try:
            controller.advance_time()

            return True

        except Exception as e:
            logger.error(f"[red]Error advancing time: {e}[/]")
            return False
