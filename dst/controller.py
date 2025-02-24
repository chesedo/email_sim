from datetime import datetime, timedelta
import requests
from python_on_whales import DockerClient
from pathlib import Path
import random
import shutil
import subprocess
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn
from dst.timecontrol import TimeControl

console = Console()

class DockerTimeController:
    def __init__(self):
        if not ensure_mail_directory():
            raise RuntimeError("Could not set up mail directory with correct permissions")

        # Generate a random time between 2020 and 2030
        start = datetime(2020, 1, 1)
        end = datetime(2030, 12, 31)
        days_between = (end - start).days
        random_days = random.randint(0, days_between)
        random_seconds = random.randint(0, 24*60*60 - 1)

        self.initial_time = start + timedelta(days=random_days, seconds=random_seconds)
        console.print(Panel.fit(
            f"[cyan]Initial simulation time:[/] [yellow]{self.initial_time}[/]",
            title="DST Environment Setup"
        ))

        # Initialize time control
        self.time_control = TimeControl(self.initial_time)

        self.docker = DockerClient()

        # TODO change the ownership of the exim config files to `root`
        # Start the services using compose
        with Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            console=console
        ) as progress:
            progress.add_task("[cyan]Starting Docker services...", total=None)
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

        # Display available services in a table
        table = Table(show_header=False, title="Available Services", border_style="cyan")
        for service in self.containers.keys():
            table.add_row(f"[green]•[/] {service}")
        console.print(table)
        console.print()

    def get_time(self) -> datetime:
        """Get the current simulation time"""
        return self.time_control.get_time()

    def set_time(self, new_time: datetime) -> None:
        """Set a new simulation time"""
        self.time_control.set_time(new_time)

    def cleanup(self):
        if self.docker:
            with Progress(
                SpinnerColumn(),
                "[progress.description]{task.description}",
                console=console
            ) as progress:
                progress.add_task("[yellow]Stopping Docker services...", total=None)
                self.docker.compose.down(volumes=True)

        if hasattr(self, 'time_control'):
            self.time_control.cleanup()

        console.print(Panel.fit(
            "[green]Environment cleanup completed[/]",
            title="DST Cleanup",
            border_style="yellow"
        ))

def ensure_mail_directory() -> bool:
    """Ensures mail directory exists with correct permissions"""
    mail_dir = Path("./tmp/mail")
    if mail_dir.exists():
        try:
            shutil.rmtree(mail_dir)
        except PermissionError:
            console.print("[yellow]Need sudo permissions to delete mail directory.[/]")
            try:
                subprocess.run(
                    ["sudo", "rm", "-R", str(mail_dir)],
                    capture_output=True,
                    text=True,
                    check=True
                )
            except subprocess.CalledProcessError as e:
                console.print(f"[red]Failed to delete directory: {e.stderr}[/]")
                return False
            except Exception as e:
                console.print(f"[red]Unexpected error deleting directory: {e}[/]")
                return False

    mail_dir.mkdir(parents=True, exist_ok=True)

    try:
        shutil.chown(mail_dir, user=101)
        return True
    except PermissionError:
        console.print("[yellow]Need sudo permissions to set mail directory ownership.[/]")
        try:
            subprocess.run(
                ["sudo", "chown", "101", str(mail_dir)],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to set directory permissions: {e.stderr}[/]")
            return False
        except Exception as e:
            console.print(f"[red]Unexpected error setting permissions: {e}[/]")
            return False
