import time
import random
from datetime import timedelta
from dst.actions import SimulationAction, register_action
from dst.controller import DockerTimeController
from rich.console import Console
from dst.generator import DataGenerator

console = Console()

@register_action
class WaitRandomDuration(SimulationAction):
    @property
    def weight(self) -> float:
        """Give this action a 1/100 chance of being selected"""
        return 0.01

    def __call__(self, controller: DockerTimeController, data_generator: DataGenerator) -> bool:
        try:
            duration = random.randint(1, 2)
            print(f"Waiting for {duration} seconds...")

            before_time = controller.get_time()
            time.sleep(duration)
            after_time = controller.get_time()

            time_difference = abs((after_time - before_time).total_seconds())
            if abs(time_difference - duration) > 0.1:
                print(f"ERROR: Time progression incorrect. Expected {duration} seconds, got {time_difference}")
                return False
            return True
        except Exception as e:
            print(f"Error during random wait: {e}")
            return False

@register_action
class AdvanceTime(SimulationAction):
    """Advances time by a random duration"""

    @property
    def weight(self) -> float:
        """Give this action a high weight since time needs to advance frequently"""
        return 10.0  # Much higher weight than other actions

    def __call__(self, controller: DockerTimeController, data_generator: DataGenerator) -> bool:
        try:
            # Get current time
            current_time = controller.get_time()

            # Advance by random amount of milliseconds (between 1ms and 100ms)
            advance_ms = random.randint(10, 100)
            new_time = current_time + timedelta(milliseconds=advance_ms)

            console.print(f"[cyan]Advancing time by {advance_ms} milliseconds...[/]")
            controller.set_time(new_time)

            return True

        except Exception as e:
            console.print(f"[red]Error advancing time: {e}[/]")
            return False
