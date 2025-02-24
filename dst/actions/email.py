from datetime import timedelta
from email.message import EmailMessage
from email import message_from_bytes
from pathlib import Path
import asyncio
import aiosmtplib
import time
from datetime import datetime
from rich.console import Console
from dst.actions import SimulationAction, ValidationAction, register_action
from dst.controller import DockerTimeController
from dst.generator import GeneratedEmail
from typing import Optional

from dst.generator import DataGenerator

console = Console()

class EmailValidator(ValidationAction):
    """Validates that an email was received correctly"""

    def __init__(self, start_time: datetime, generated_email: GeneratedEmail):
        super().__init__(start_time)
        self.generated_email = generated_email
        self.mail_dir = Path("./tmp/mail")

    @property
    def timeout(self) -> float:
        return 5.0  # 5 second timeout for email delivery

    def validate(self, controller: DockerTimeController) -> bool:
        """Verify that the email was received by checking the mail directory."""
        recipient_dir = self.mail_dir / self.generated_email.recipient.email
        expected_file = recipient_dir / f"{self.generated_email.subject}.eml"

        if expected_file.exists():
            try:
                email_content = expected_file.read_bytes()
                email_msg = message_from_bytes(email_content)

                if email_msg["Subject"] != self.generated_email.subject:
                    console.print(f"[red]Subject mismatch:[/]\nExpected: {email_msg['Subject']}\nReceived: {self.generated_email.subject}")
                    return False

                if email_msg["Date"] != self.generated_email.date.strftime("%a, %d %b %Y %H:%M:%S +0000"):
                    console.print(f"[red]Date mismatch:[/]\nExpected: {email_msg['Date']}\nReceived: {self.generated_email.date.strftime('%a, %d %b %Y %H:%M:%S +0000')}")
                    return False

                payload = email_msg.get_payload()

                for part in payload:
                    if part.get_content_type() == "text/plain":
                        if part.get_payload() != self.generated_email.text_content:
                            console.print(f"[red]Text content mismatch:[/]\nExpected: {part.get_payload()}\nReceived: {self.generated_email.text_content}")
                            return False
                    elif part.get_content_type() == "text/html":
                        if part.get_payload() != self.generated_email.html_content:
                            console.print(f"[red]HTML content mismatch:[/]\nExpected: {part.get_payload()}\nReceived: {self.generated_email.html_content}")
                            return False

                return True
            except Exception as e:
                console.print(f"[red]Error reading email: {e}[/]")
                return False

        console.print(f"[red]Email file not found: {expected_file}[/]")
        return False

@register_action
class SendBasicEmail(SimulationAction):
    """Sends a basic test email from the sending MTA to the receiving MTA"""

    async def send_test_email(self, host: str, port: int, email: EmailMessage, controller: DockerTimeController) -> bool:
        try:
            # Create SMTP connection
            smtp = aiosmtplib.SMTP(
                hostname=host,
                port=port,
                timeout=5,
                use_tls=False,
                validate_certs=False,
            )

            # Start connection process
            connect_task = asyncio.create_task(smtp.connect())
            console.print(f"[cyan]Connecting to SMTP server at {host}:{port}...[/]")

            # Check connection result
            await connect_task

            # Start send process
            send_task = asyncio.create_task(smtp.send_message(email))
            console.print(f"[cyan]Sending email...[/]")

            await controller.wait_to_reach_send_queue()
            controller.set_time(controller.get_time() + timedelta(milliseconds=100))

            # Check send result
            await send_task

            # Close connection
            await smtp.quit()

            return True

        except Exception as e:
            console.print(f"[red]Failed to send email: {e}[/]")
            return False

    def __call__(self, controller: DockerTimeController, data_generator: DataGenerator) -> tuple[bool, Optional[ValidationAction]]:
        try:
            # Get current simulated time
            current_time = controller.get_time()
            console.print(f"[cyan]Sending email at simulated time: {current_time}[/]")

            generated_email = data_generator.generate_email(date = current_time)

            # Get the sending exim container and its port
            exim_send = controller.containers['exim_send']
            port_mappings = exim_send.network_settings.ports["25/tcp"]
            if not port_mappings:
                raise RuntimeError("Could not find mapped port for sending MTA")

            send_port = int(port_mappings[0]["HostPort"])

            # Use localhost and mapped port to send email
            success = asyncio.run(
                self.send_test_email("localhost", send_port, generated_email.build_email(), controller)
            )

            if not success:
                return False, None

            # Wait for receiver to get the email
            controller.wait_to_reach_receive_queue()
            controller.set_time(controller.get_time() + timedelta(milliseconds=100))

            # Create validator
            validator = EmailValidator(
                start_time=current_time,
                generated_email=generated_email
            )

            # Try validation with retry/timeout
            start_validate_time = datetime.now()
            timeout_seconds = validator.timeout

            while True:
                # Check if we need to timeout
                elapsed = (datetime.now() - start_validate_time).total_seconds()
                if elapsed > timeout_seconds:
                    console.print(f"[red]Validation timed out after {elapsed:.2f} seconds[/]")
                    return False, None

                # Try to validate
                if validator.validate(controller):
                    console.print(f"[green]Email validated successfully after {elapsed:.2f} seconds[/]")
                    return True, None

                # Brief pause before trying again
                time.sleep(0.01)

        except Exception as e:
            console.print(f"[red]Error in SendBasicEmail action: {e}[/]")
            return False, None
