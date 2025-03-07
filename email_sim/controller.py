import asyncio
import logging
import random
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from python_on_whales import DockerClient
from rich.progress import Progress, TaskID

from email_sim.timecontrol import TimeControl

logger = logging.getLogger("dst")


class DockerTimeController:
    def __init__(self, progress: Progress, action_id: TaskID):
        if not ensure_mail_directory():
            raise RuntimeError(
                "Could not set up mail directory with correct permissions"
            )

        if not ensure_root_owns_exim_config("exim/send.conf"):
            raise RuntimeError("Could not set sending exim config to root ownership")

        if not ensure_root_owns_exim_config("exim/receive.conf"):
            raise RuntimeError("Could not set receiving exim config to root ownership")

        # Generate a random time between 2020 and 2030
        start = datetime(2020, 1, 1)
        end = datetime(2030, 12, 31)
        days_between = (end - start).days
        random_days = random.randint(0, days_between)
        random_seconds = random.randint(0, 24 * 60 * 60 - 1)

        self.initial_time = start + timedelta(days=random_days, seconds=random_seconds)
        logger.info(f"Initial simulation time: {self.initial_time}")

        # Initialize time control
        self.time_control = TimeControl(self.initial_time)

        self.docker = DockerClient()

        self.progress = progress
        self.action_id = action_id

        # Start the services using compose
        self.progress.update(
            self.action_id, advance=0, description="Starting Docker services"
        )
        self.docker.compose.up(
            wait=True,
            build=True,
            recreate=True,
            quiet=True,
        )

        # Convert list of containers to a map by service name
        containers = self.docker.compose.ps()
        if not containers:
            raise RuntimeError("No containers started")

        self.containers = {
            container.name.split("-")[1]: container for container in containers
        }

        # Log available services
        logger.info("Available services:")
        for service in self.containers.keys():
            logger.info(f"• {service}")

        # Get the sending exim container and its port
        exim_send = self.containers["exim_send"]
        port_mappings = exim_send.network_settings.ports["25/tcp"]
        if not port_mappings:
            raise RuntimeError("Could not find mapped port for sending MTA")

        self.send_port = int(port_mappings[0]["HostPort"])

    def get_send_queue_size(self) -> int:
        """Get the current size of the send queue"""
        response = self.docker.compose.execute(
            service="exim_send", command=["exim", "-bpc"], tty=False
        )

        if response is None:
            return 0

        try:
            return int(response)
        except ValueError:
            return 0

    async def wait_to_reach_send_queue(self) -> None:
        """Wait until the send queue has one email"""
        while True:
            queue_size = self.get_send_queue_size()

            logger.debug(f"Send queue size: {queue_size}")

            if queue_size == 1:
                return

            # Need a small async sleep to allow the send thread to continue
            await asyncio.sleep(0.001)

    def get_receive_queue_size(self) -> int:
        """Get the current size of the send queue"""
        response = self.docker.compose.execute(
            service="exim_receive", command=["exim", "-bpc"], tty=False
        )

        if response is None:
            return 0

        try:
            return int(response)
        except ValueError:
            return 0

    def wait_to_reach_receive_queue(self) -> None:
        """Wait until the receive queue has one email"""
        while True:
            queue_size = self.get_receive_queue_size()

            logger.debug(f"Receive queue size: {queue_size}")

            if queue_size == 1:
                return

    def get_time(self) -> datetime:
        """Get the current simulation time"""
        return self.time_control.get_time()

    def advance_time(self, lower_bound: int = 1, upper_bound: int = 100) -> None:
        """Advance the simulation time by a random amount of milliseconds within the bounds"""
        milliseconds = random.randint(lower_bound, upper_bound)
        new_time = self.get_time() + timedelta(milliseconds=milliseconds)

        logger.debug(f"Advancing time by {milliseconds} milliseconds")

        self.time_control.set_time(new_time)

    def cleanup(self):
        if self.docker:
            self.progress.update(
                self.action_id, advance=0, description="Stopping Docker services"
            )
            self.docker.compose.down(volumes=True, quiet=True)

        if hasattr(self, "time_control"):
            self.time_control.cleanup()

        logger.info("Environment cleanup completed")


def ensure_mail_directory() -> bool:
    """Ensures mail directory exists with correct permissions"""
    mail_dir = Path("./tmp/mail")
    if mail_dir.exists():
        try:
            shutil.rmtree(mail_dir)
        except PermissionError:
            logger.warning("Need sudo permissions to delete mail directory.")
            try:
                subprocess.run(
                    ["sudo", "rm", "-R", str(mail_dir)],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to delete directory: {e.stderr}")
                return False
            except Exception as e:
                logger.error(f"Unexpected error deleting directory: {e}")
                return False

    mail_dir.mkdir(parents=True, exist_ok=True)

    try:
        shutil.chown(mail_dir, user=101)
        return True
    except PermissionError:
        logger.warning("Need sudo permissions to set mail directory ownership.")
        try:
            subprocess.run(
                ["sudo", "chown", "101", str(mail_dir)],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set directory permissions: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting permissions: {e}")
            return False

# Exim has a security thing where the running user cannot own the config files
# It has to be owned by root. So this function makes sure that is the case.
def ensure_root_owns_exim_config(path: str) -> bool:
    """Ensure the exim config file at `path` is owned by root"""
    try:
        shutil.chown(path, user=0, group=0)

        return True
    except PermissionError:
        logger.warning(f"Need sudo permissions to set ownership of {path}")
        try:
            subprocess.run(
                ["sudo", "chown", "root:root", path],
                capture_output=True,
                text=True,
                check=True,
            )

            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set ownership of {path}: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting ownership of {path}: {e}")
            return False
