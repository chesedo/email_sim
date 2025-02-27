import html

from jinja2 import BaseLoader, Environment

from dst.email_clients import EmailClient, register_email_client
from dst.generator.user import User


@register_email_client
class DefaultEmailClient(EmailClient):
    """Default email client with basic formatting"""

    EMAIL_TEMPLATE = """
        <html>
        <body>
            <div style="font-family: Arial, sans-serif;">
                <p>{{ text_content }}</p>
                {% if signature %}
                <br/>
                <div style="color: #666;">
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
        """Generate the text and HTML content of an email"""
        # Generate content
        signature = sender.generate_signature()
        text_content_with_signature = f"{text_content}\n\n--\n{signature}"

        template = Environment(loader=BaseLoader()).from_string(self.EMAIL_TEMPLATE)
        html_content = template.render(
            subject=html.escape(subject),
            text_content=html.escape(text_content).replace("\n", "<br/>"),
            signature=html.escape(signature).replace("\n", "<br/>"),
        )

        return text_content_with_signature, html_content
