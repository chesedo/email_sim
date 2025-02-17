from email.message import EmailMessage
from email import message_from_bytes
from pathlib import Path
import asyncio
import aiosmtplib
import time
import shutil
import subprocess
from datetime import datetime
from rich.console import Console
from dst.actions import SimulationAction, register_action
from dst.controller import DockerTimeController

console = Console()

@register_action
class SendBasicEmail(SimulationAction):
    """Sends a basic test email from the sending MTA to the receiving MTA"""

    def ensure_mail_directory(self) -> bool:
        """Ensures mail directory exists with correct permissions"""
        self.mail_dir = Path("./tmp/mail")
        if self.mail_dir.exists():
            try:
                shutil.rmtree(self.mail_dir)
            except PermissionError:
                console.print("[yellow]Need sudo permissions to delete mail directory.[/]")
                try:
                    subprocess.run(
                        ["sudo", "rm", "-R", str(self.mail_dir)],
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

        self.mail_dir.mkdir(parents=True, exist_ok=True)

        # Try to set ownership without sudo first
        try:
            shutil.chown(self.mail_dir, user=101)  # Only change user, keep group
            return True
        except PermissionError:
            console.print("[yellow]Need sudo permissions to set mail directory ownership.[/]")
            try:
                subprocess.run(
                    ["sudo", "chown", "101", str(self.mail_dir)],  # Only change user
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

    def __init__(self):
        if not self.ensure_mail_directory():
            raise RuntimeError("Could not set up mail directory with correct permissions")

    async def send_test_email(self, host: str, port: int, current_time: datetime) -> tuple[bool, str]:
        message = EmailMessage()
        message["From"] = "test@sender.local"
        message["To"] = "test@receiver.local"
        message["Subject"] = "Test Email from DST"
        message["Date"] = current_time.strftime("%a, %d %b %Y %H:%M:%S %z")
        message.set_content("This is a test email from the DST system.")

        try:
            await aiosmtplib.send(
                message,
                hostname=host,
                port=port,
                timeout=5,
                start_tls=False,
                validate_certs=False,
            )
            return True, "Test Email from DST.eml"
        except Exception as e:
            console.print(f"[red]Failed to send email: {e}[/]")
            return False, ""

    def verify_received_email(self, expected_filename: str, max_wait: int = 5) -> bool:
        """
        Verify that the email was received by checking the mail directory.
        Will wait up to max_wait seconds for the email to appear.
        """
        recipient_dir = self.mail_dir / "test@receiver.local"
        expected_file = recipient_dir / expected_filename

        # Wait for file to appear
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if expected_file.exists():
                try:
                    email_content = expected_file.read_bytes()
                    email_msg = message_from_bytes(email_content)

                    console.print("[green]Found email:[/]")
                    console.print(f"From: {email_msg['From']}")
                    console.print(f"To: {email_msg['To']}")
                    console.print(f"Subject: {email_msg['Subject']}")
                    console.print(f"Date: {email_msg['Date']}")
                    return True
                except Exception as e:
                    console.print(f"[red]Error reading email: {e}[/]")
                    return False

            # Wait a bit before checking again
            time.sleep(0.5)

        console.print(f"[red]Timeout waiting for email file: {expected_file}[/]")
        return False

    def __call__(self, controller: DockerTimeController) -> bool:
        try:
            # Get current simulated time
            current_time = controller.get_time()
            console.print(f"[cyan]Sending email at simulated time: {current_time}[/]")

            # Get the sending exim container and its port
            exim_send = controller.containers['exim_send']
            port_mappings = exim_send.network_settings.ports["25/tcp"]
            if not port_mappings:
                raise RuntimeError("Could not find mapped port for sending MTA")

            send_port = int(port_mappings[0]["HostPort"])

            # Use localhost and mapped port to send email
            success, expected_filename = asyncio.run(
                self.send_test_email("localhost", send_port, current_time)
            )

            if not success:
                return False

            # Verify the email was received
            if not self.verify_received_email(expected_filename):
                console.print("[red]Failed to verify received email[/]")
                return False

            return True

        except Exception as e:
            console.print(f"[red]Error in SendBasicEmail action: {e}[/]")
            return False
