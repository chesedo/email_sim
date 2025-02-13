#!/usr/bin/env python3

import pytest
import docker
from datetime import datetime, timedelta
import requests
import time

class DockerTimeController:
    def __init__(self):
        self.client = docker.from_client()
        self.container = None

    def start_container(self):
        # Using a simple Python HTTP server as our test service
        self.container = self.client.containers.run(
            "python:3.9-slim",
            command="python -m http.server 8080",
            detach=True,
            ports={'8080/tcp': None},  # Random host port
            environment={"TZ": "UTC"},  # Ensure UTC timezone
            cap_add=["SYS_TIME"]  # Required for time manipulation
        )

        # Wait for container to be ready
        time.sleep(2)  # Simple wait, could be replaced with proper health check

        # Get the mapped port
        container_info = self.client.api.inspect_container(self.container.id)
        self.host_port = container_info['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']

    def set_container_time(self, target_time: datetime):
        # Format time for date command
        time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")

        # Use date command to set time in container
        exec_result = self.container.exec_run(
            f"date -s '{time_str}'",
            privileged=True
        )
        if exec_result.exit_code != 0:
            raise Exception(f"Failed to set time: {exec_result.output}")

    def cleanup(self):
        if self.container:
            self.container.stop()
            self.container.remove()

@pytest.fixture
def time_controlled_container():
    controller = DockerTimeController()
    try:
        controller.start_container()
        yield controller
    finally:
        controller.cleanup()

def test_time_control(time_controlled_container):
    # Set container time to a specific datetime
    target_time = datetime(2024, 1, 1, 12, 0, 0)
    time_controlled_container.set_container_time(target_time)

    # You can now make requests to your service and verify time-dependent behavior
    response = requests.get(f"http://localhost:{time_controlled_container.host_port}")
    assert response.status_code == 200
