import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

# To avoid circular references for type hinting
if TYPE_CHECKING:
    from email_sim.email_clients import EmailClient

logger = logging.getLogger("dst")


@dataclass
class User:
    first_name: str
    last_name: str
    email: str
    email_client: "EmailClient"
    company: Optional[str] = None

    def generate_signature(self) -> str:
        """Generate an email signature for a user"""
        signature_parts = [
            f"{self.first_name} {self.last_name}",
        ]
        if self.company:
            signature_parts.append(self.company)
        signature_parts.append(self.email)

        return "\n".join(signature_parts)
