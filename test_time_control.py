#!/usr/bin/env python3

from datetime import datetime, timedelta
import requests
import time
from python_on_whales import DockerClient
from pathlib import Path
import random
import argparse
import sys
from typing import Callable, List

class SimulationAction:
    """Base class for simulation actions"""
    def __call__(self, controller: 'DockerTimeController') -> bool:
        raise NotImplementedError

class CheckTime(SimulationAction):
    def __call__(self, controller: 'DockerTimeController') -> bool:
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

class WaitRandomDuration(SimulationAction):
    def __call__(self, controller: 'DockerTimeController') -> bool:
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

class DockerTimeController:
    def __init__(self):
        # Generate a random time between 2020 and 2030
        start = datetime(2020, 1, 1)
        end = datetime(2030, 12, 31)
        days_between = (end - start).days
        random_days = random.randint(0, days_between)
        random_seconds = random.randint(0, 24*60*60 - 1)  # Random time within the day

        self.initial_time = start + timedelta(days=random_days, seconds=random_seconds)
        print(f"Simulation starting with time: {self.initial_time}")

        # Set up environment with our static time
        faketime_timestamp = self.initial_time.strftime("@%Y-%m-%d %H:%M:%S")

        # Create env file next to compose.yaml
        project_dir = Path.cwd()
        self.env_path = project_dir / "tmp.env"
        self.env_path.write_text(f"FAKETIME={faketime_timestamp}\n")

        self.docker = DockerClient()

        # Start the services using compose
        self.docker.compose.up(
            wait=True, # Wait for the service to be healthy
            build=True, # Always rebuild the images
            recreate=True, # Recreate the containers
        )

        # Convert list of containers to a map by service name
        containers = self.docker.compose.ps()
        if not containers:
            raise RuntimeError("No containers started")

        # Map of service_name -> container
        self.containers = {
            container.name.split('-')[1]: container
            for container in containers
        }

        print("Available services:", list(self.containers.keys()))

    def get_time(self):
        # Get the mapped port
        timeserver = self.containers['timeserver']
        port_mappings = timeserver.network_settings.ports["8080/tcp"]
        if not port_mappings:
            raise RuntimeError("Could not find mapped port")

        host_port = port_mappings[0]["HostPort"]

        response = requests.get(f"http://localhost:{host_port}/time")
        return datetime.strptime(response.json()['current_time'], '%Y-%m-%d %H:%M:%S')

    def cleanup(self):
        if self.docker:
            self.docker.compose.down(volumes=True)

        self.env_path.unlink(missing_ok=True)


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

def main():
    parser = argparse.ArgumentParser(description='Run time simulation')
    parser.add_argument('--seed', type=int, help='Seed for random time generation')
    parser.add_argument('--steps', type=int, default=2, help='Number of simulation steps')
    args = parser.parse_args()

    if args.seed is None:
        args.seed = random.randint(1, 1_000_000)

    print(f"Using seed {args.seed}")

    random.seed(args.seed)

    # List of available actions
    actions = [
        CheckTime(),
        WaitRandomDuration(),
        # Add more actions here
    ]

    success = run_simulation(actions, args.steps)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
