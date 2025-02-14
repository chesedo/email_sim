#!/usr/bin/env python3

# test_time_control.py
import pytest
import docker
import io
from datetime import datetime, timedelta
import requests
import time

class DockerTimeController:
    def __init__(self):
        self.client = docker.from_env()
        self.container = None
        self.static_time = datetime(2024, 8, 1, 12, 0, 0)


    def start_container(self):
        # Set initial timestamp for libfaketime
        faketime_timestamp = self.static_time.strftime("@%Y-%m-%d %H:%M:%S")

        # Run the container with libfaketime configured
        self.container = self.client.containers.run(
            "timeserver:latest",
            detach=True,
            ports={'8080/tcp': None},
            environment={
                "LD_PRELOAD": "/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1",
                "FAKETIME": faketime_timestamp,
                "FAKETIME_NO_CACHE": "1",
                "TZ": "UTC"
            }
        )

        # Wait for container to be ready
        time.sleep(2)

        # Get the mapped port
        container_info = self.client.api.inspect_container(self.container.id)
        self.host_port = container_info['NetworkSettings']['Ports']['8080/tcp'][0]['HostPort']

    def get_container_time(self):
        response = requests.get(f"http://localhost:{self.host_port}/time")
        return datetime.strptime(response.json()['current_time'], '%Y-%m-%d %H:%M:%S')

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
