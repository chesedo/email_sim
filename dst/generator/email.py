from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dst.generator.user import User


@dataclass
class GeneratedEmail:
    sender: User
    recipient: User
    subject: str
    text_content: str
    html_content: str
    date: datetime

    def build_email(self) -> EmailMessage:
        """Build an EmailMessage object from the generated email"""
        msg = EmailMessage()

        # Set the standard headers
        msg["From"] = (
            f"{self.sender.first_name} {self.sender.last_name} <{self.sender.email}>"
        )
        msg["To"] = (
            f"{self.recipient.first_name} {self.recipient.last_name} <{self.recipient.email}>"
        )
        msg["Subject"] = self.subject
        msg["Date"] = self.date.strftime("%a, %d %b %Y %H:%M:%S +0000")

        # Create multipart message
        msg_alternative = MIMEMultipart("alternative")
        msg_alternative.attach(MIMEText(self.text_content, "plain"))
        msg_alternative.attach(MIMEText(self.html_content, "html"))

        # Attach the multipart content to the message
        msg.set_content(msg_alternative)

        return msg
