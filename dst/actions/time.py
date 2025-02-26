import logging

from dst.actions import SimulationAction, register_action
from dst.controller import DockerTimeController
from dst.generator import DataGenerator

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
