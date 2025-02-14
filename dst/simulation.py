import random
from typing import List
from dst.controller import DockerTimeController
from dst.actions import SimulationAction

def run_simulation(actions: List[SimulationAction], steps: int = 100) -> bool:
    controller = DockerTimeController()
    try:
        for step in range(steps):
            print(f"\nStep {step + 1}/{steps}")
            action = random.choice(actions)
            print(f"Running action: {action.__class__.__name__}")
            if not action(controller):
                return False
        return True
    finally:
        controller.cleanup()
