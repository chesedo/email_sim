import random
from datetime import timedelta

from rich.console import Console

from dst.actions import SimulationAction, register_action
from dst.controller import DockerTimeController
from dst.generator import DataGenerator

console = Console()


@register_action
class AdvanceTime(SimulationAction):
    """Advances time by a random duration"""

    def __call__(
        self, controller: DockerTimeController, data_generator: DataGenerator
    ) -> bool:
        try:
            # Get current time
            current_time = controller.get_time()

            # Advance by random amount of milliseconds (between 1ms and 100ms)
            advance_ms = random.randint(1, 100)
            new_time = current_time + timedelta(milliseconds=advance_ms)

            console.print(f"[cyan]Advancing time by {advance_ms} milliseconds...[/]")
            controller.set_time(new_time)

            return True

        except Exception as e:
            console.print(f"[red]Error advancing time: {e}[/]")
            return False
