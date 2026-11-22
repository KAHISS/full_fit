import logging
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)

class EmailSender(Protocol):
    async def send_email_verification(self, *, to: str, name: str, token: str) -> None: ...


class ConsoleEmailSender:
    async def send_email_verification(self, *, to: str, name: str, token: str) -> None:
        if settings.environment == "production":
            logger.warning("No email provider configured: verification email was not sent.")
            return
        logger.info("[DEV] Verification email for %s (%s). Token: %s", to, name, token)