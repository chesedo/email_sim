import asyncio
import logging
import re
import time
from datetime import datetime
from email import message_from_bytes
from email.message import EmailMessage
from pathlib import Path

import aiosmtplib

from email_sim.actions import SimulationAction, register_action
from email_sim.controller import DockerTimeController
from email_sim.generator import DataGenerator
from email_sim.generator.email import GeneratedEmail

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

        # Sanitize the subject to match how Exim would process it
        sanitized_subject = re.sub(r'[/:*?"<>|\\]', "_", self.generated_email.subject)
        expected_file = recipient_dir / f"{sanitized_subject}.eml"

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

        logger.debug(f"Email not found at: {expected_file}")
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
            logger.debug("Opening connection to SMTP server...")
            connect_task = asyncio.create_task(smtp.connect())
            logger.debug(f"Connecting to SMTP server at {host}:{port}...")

            # Check connection result
            await connect_task
            logger.debug("Connection established")

            # Start send process
            logger.debug("Ready to send email...")
            send_task = asyncio.create_task(smtp.send_message(email))
            logger.info("Sending email...")

            await asyncio.sleep(0.1)
            await controller.wait_to_reach_send_queue()
            logger.debug("Email in queue")
            controller.advance_time(lower_bound=50)

            # Check send result
            await send_task
            logger.info("Email sent")

            # Close connection
            await smtp.quit()
            logger.debug("Connection closed")

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

            generated_email = GeneratedEmail(data_generator, current_time)

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
            logger.debug("Email in receive queue")
            controller.advance_time(lower_bound=50)

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
