#!/usr/bin/env python3

import pytest
from datetime import datetime
import requests
import time
from python_on_whales import DockerClient
import tempfile
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
        self.container = None

    def start_container(self):

        # Start the service using compose
        self.docker.compose.up(
            wait=True
        )

        # Get container instance
        containers = self.docker.compose.ps()
        if not containers:
            raise RuntimeError("No containers started")
        self.container = containers[0]

        # Get the mapped port
        port_mappings = self.container.network_settings.ports["8080/tcp"]
        if not port_mappings:
            raise RuntimeError("Could not find mapped port")

        self.host_port = port_mappings[0]["HostPort"]

    def get_container_time(self):
        response = requests.get(f"http://localhost:{self.host_port}/time")
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
    container_time = time_controlled_container.get_container_time()
    expected_time = datetime(2024, 8, 1, 12, 0, 0)

    # Assert that the time was set correctly (allowing for a small difference due to execution time)
    time_difference = abs((container_time - expected_time).total_seconds())
    assert time_difference < 5, f"Time difference too large: {time_difference} seconds"

    # Wait for 5 seconds
    time.sleep(5)
    new_time = time_controlled_container.get_container_time()
    time_difference = abs((new_time - container_time).total_seconds())
    assert time_difference == 5, f"Time difference should be 5 seconds, but was {time_difference}"
