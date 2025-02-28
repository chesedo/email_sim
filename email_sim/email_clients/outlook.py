import html

from jinja2 import BaseLoader, Environment

from email_sim.email_clients import EmailClient, register_email_client
from email_sim.generator.user import User


@register_email_client
class OutlookClient(EmailClient):
    """Outlook email client with typical Outlook formatting"""

    EMAIL_TEMPLATE = """
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 11pt; color: #000000;">
            <div>
                <p>{{ text_content }}</p>
                {% if signature %}
                <div style="border-top: solid 1.0pt #E1E1E1; padding-top: 8px; margin-top: 15px;">
                    {{ signature }}
                </div>
                {% endif %}
            </div>
        </body>
        </html>
    """

    def generate_content(
        self, subject: str, sender: User, text_content: str
    ) -> tuple[str, str]:
        """Generate the text and HTML content of an email in Outlook style"""
        # Generate content
        signature = sender.generate_signature()
        text_content_with_signature = f"{text_content}\n\n{signature}"

        template = Environment(loader=BaseLoader()).from_string(self.EMAIL_TEMPLATE)
        html_content = template.render(
            subject=html.escape(subject),
            text_content=html.escape(text_content).replace("\n", "<br/>"),
            signature=html.escape(signature).replace("\n", "<br/>"),
        )

        return text_content_with_signature, html_content
