import asyncio
import logging
import time
from datetime import datetime, timedelta
from email import message_from_bytes
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib

from dst.actions import SimulationAction, register_action
from dst.controller import DockerTimeController
from dst.generator import DataGenerator, GeneratedEmail

logger = logging.getLogger("dst")


class EmailValidator:
    """Validates that an email was received correctly"""

    def __init__(self, generated_email: GeneratedEmail):
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
                    logger.error(
                        f"Subject mismatch: Expected: {self.generated_email.subject}, Received: {email_msg['Subject']}"
                    )
                    return False

                if email_msg["Date"] != self.generated_email.date.strftime(
                    "%a, %d %b %Y %H:%M:%S +0000"
                ):
                    logger.error(
                        f"Date mismatch: Expected: {self.generated_email.date.strftime('%a, %d %b %Y %H:%M:%S +0000')}, Received: {email_msg['Date']}"
                    )
                    return False

                payload = email_msg.get_payload()

                for part in payload:
                    if part.get_content_type() == "text/plain":
                        if part.get_payload() != self.generated_email.text_content:
                            logger.error("Text content mismatch")
                            return False
                    elif part.get_content_type() == "text/html":
                        if part.get_payload() != self.generated_email.html_content:
                            logger.error("HTML content mismatch")
                            return False

                return True
            except Exception as e:
                logger.error(f"Error reading email: {e}")
                return False

        # Email file not found yet
        return False


@register_action
class SendBasicEmail(SimulationAction):
    """Sends a basic test email from the sending MTA to the receiving MTA"""

    async def send_test_email(
        self,
        host: str,
        port: int,
        email: EmailMessage,
        controller: DockerTimeController,
    ) -> bool:
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
            logger.info(f"Connecting to SMTP server at {host}:{port}...")

            # Check connection result
            await connect_task

            # Start send process
            send_task = asyncio.create_task(smtp.send_message(email))
            logger.info("Sending email...")

            await controller.wait_to_reach_send_queue()
            controller.set_time(controller.get_time() + timedelta(milliseconds=100))

            # Check send result
            await send_task

            # Close connection
            await smtp.quit()

            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def __call__(
        self, controller: DockerTimeController, data_generator: DataGenerator
    ) -> bool:
        try:
            # Get current simulated time
            current_time = controller.get_time()
            logger.info(f"Sending email at simulated time: {current_time}")

            generated_email = data_generator.generate_email(date=current_time)

            # Use localhost and mapped port to send email
            success = asyncio.run(
                self.send_test_email(
                    "localhost",
                    controller.send_port,
                    generated_email.build_email(),
                    controller,
                )
            )

            if not success:
                return False

            # Wait for receiver to get the email
            controller.wait_to_reach_receive_queue()
            controller.set_time(controller.get_time() + timedelta(milliseconds=100))

            # Create validator
            validator = EmailValidator(generated_email)

            # Try validation with retry/timeout
            start_validate_time = datetime.now()
            timeout_seconds = validator.timeout

            while True:
                # Check if we need to timeout
                elapsed = (datetime.now() - start_validate_time).total_seconds()
                if elapsed > timeout_seconds:
                    logger.error(f"Validation timed out after {elapsed:.2f} seconds")
                    return False

                # Try to validate
                if validator.validate(controller):
                    logger.info(
                        f"Email validated successfully after {elapsed:.2f} seconds"
                    )
                    return True

                # Brief pause before trying again
                time.sleep(0.01)

        except Exception as e:
            logger.error(f"Error in SendBasicEmail action: {e}")
            return False
