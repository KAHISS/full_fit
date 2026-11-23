import logging
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    async def send_email_verification(self, *, to: str, name: str, token: str) -> None: ...


class ConsoleEmailSender:
    """Não envia e-mail de verdade: só escreve no log, para desenvolvimento.

    O token só aparece no log fora de produção. Em produção, um token no log seria um
    vazamento, então registramos apenas um aviso de que não há provedor real configurado.
    """

    async def send_email_verification(self, *, to: str, name: str, token: str) -> None:
        if settings.environment == "production":
            logger.warning("No email provider configured: verification email was not sent.")
            return
        logger.info("[DEV] Verification email for %s (%s). Token: %s", to, name, token)


def build_email_sender() -> EmailSender:
    """Escolhe a implementação de EmailSender a partir de settings.email_backend.

    Para adicionar um provedor: escreva a classe dele acima, inclua o nome no Literal de
    Settings.email_backend e adicione um ramo aqui.
    """
    if settings.email_backend == "console":
        return ConsoleEmailSender()
    raise ValueError(f"Unknown EMAIL_BACKEND: {settings.email_backend!r}")