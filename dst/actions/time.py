import time
import random
from dst.actions import SimulationAction, ValidationAction, register_action
from dst.controller import DockerTimeController
from typing import Optional

@register_action
class WaitRandomDuration(SimulationAction):
    def __call__(self, controller: DockerTimeController) -> tuple[bool, Optional[ValidationAction]]:
        try:
            duration = random.randint(1, 2)
            print(f"Waiting for {duration} seconds...")

            before_time = controller.get_time()
            time.sleep(duration)
            after_time = controller.get_time()

            time_difference = abs((after_time - before_time).total_seconds())
            if abs(time_difference - duration) > 0.1:
                print(f"ERROR: Time progression incorrect. Expected {duration} seconds, got {time_difference}")
                return False, None
            return True, None
        except Exception as e:
            print(f"Error during random wait: {e}")
            return False, None
