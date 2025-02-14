from datetime import datetime, timedelta
import requests
from python_on_whales import DockerClient
from pathlib import Path
import random

class DockerTimeController:
    def __init__(self):
        # Generate a random time between 2020 and 2030
        start = datetime(2020, 1, 1)
        end = datetime(2030, 12, 31)
        days_between = (end - start).days
        random_days = random.randint(0, days_between)
        random_seconds = random.randint(0, 24*60*60 - 1)

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
            wait=True,
            build=True,
            recreate=True,
        )

        # Convert list of containers to a map by service name
        containers = self.docker.compose.ps()
        if not containers:
            raise RuntimeError("No containers started")

        self.containers = {
            container.name.split('-')[1]: container
            for container in containers
        }

        print("Available services:", list(self.containers.keys()))

    def get_time(self):
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
