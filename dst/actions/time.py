import time
import random
from dst.actions import SimulationAction, register_action
from dst.controller import DockerTimeController

@register_action
class CheckTime(SimulationAction):
    def __call__(self, controller: DockerTimeController) -> bool:
        try:
            before_time = controller.get_time()
            time.sleep(5)
            after_time = controller.get_time()

            time_difference = abs((after_time - before_time).total_seconds())
            if abs(time_difference - 5) > 0.1:
                print(f"ERROR: Time progression incorrect. Expected 5 seconds, got {time_difference}")
                return False
            return True
        except Exception as e:
            print(f"Error checking time: {e}")
            return False

@register_action
class WaitRandomDuration(SimulationAction):
    def __call__(self, controller: DockerTimeController) -> bool:
        try:
            duration = random.randint(1, 10)
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
