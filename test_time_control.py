#!/usr/bin/env python3

import pytest
from datetime import datetime
import requests
import time
from python_on_whales import DockerClient
from pathlib import Path

class DockerTimeController:
    def __init__(self):
        static_time = datetime(2024, 8, 1, 12, 0, 0)
        # Set up environment with our static time
        faketime_timestamp = static_time.strftime("@%Y-%m-%d %H:%M:%S")

        # Create env file next to compose.yaml
        project_dir = Path.cwd()
        self.env_path = project_dir / "tmp.env"
        self.env_path.write_text(f"FAKETIME={faketime_timestamp}\n")

        self.docker = DockerClient()
        self.containers = {}

    def start_container(self):

        # Start the service using compose
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

@pytest.fixture
def time_controlled_container():
    controller = DockerTimeController()
    try:
        controller.start_container()
        yield controller
    finally:
        controller.cleanup()

def test_time_control(time_controlled_container):
    # Get the container's current time
    container_time = time_controlled_container.get_time()
    expected_time = datetime(2024, 8, 1, 12, 0, 0)

    # Assert that the time was set correctly (allowing for a small difference due to execution time)
    time_difference = abs((container_time - expected_time).total_seconds())
    assert time_difference < 5, f"Time difference too large: {time_difference} seconds"

    # Wait for 5 seconds
    time.sleep(5)
    new_time = time_controlled_container.get_time()
    time_difference = abs((new_time - container_time).total_seconds())
    assert time_difference == 5, f"Time difference should be 5 seconds, but was {time_difference}"
