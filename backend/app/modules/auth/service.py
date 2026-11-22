import asyncio
import logging

from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.core.email import EmailSender
from app.core.exceptions import ConflictError
from app.modules.auth.models import TipoTokenUsuario
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import RegisterRequest
from app.modules.auth.security import (
    email_verification_token_ttl,
    hash_password,
    issue_opaque_token,
    validate_password_strength,
)
from app.modules.users.models import TipoConsentimento, Usuario
from app.modules.users.service import UserService

logger = logging.getLogger(__name__)

_EMAIL_UNIQUE_INDEX = "uq_usuario_email_lower"

class AuthService:
    def __init__(
        self,
        user_service: UserService,
        repository: AuthRepository,
        email_sender: EmailSender,
    ) -> None:
        self.user_service = user_service
        self.repository = repository
        self.email_sender = email_sender

    async def register(self, payload: RegisterRequest, *, ip: str) -> Usuario:
        password = payload.senha.get_secret_value()
        validate_password_strength(password)

        # Argon2 is slow on purpose and CPU-bound. Run it in a separate thread so it
        # does not block the event loop (and other requests) while it computes.
        password_hash = await asyncio.to_thread(hash_password, password)

        # We also record "did not accept" (accepted=False): it is the audit history.
        consents = [
            (
                TipoConsentimento.TERMOS_USO,
                payload.aceite_termos_uso,
                settings.consent_terms_version,
            ),
            (
                TipoConsentimento.PRIVACIDADE,
                payload.aceite_privacidade,
                settings.consent_privacy_version,
            ),
            (
                TipoConsentimento.PUBLICIDADE,
                payload.aceite_publicidade,
                settings.consent_advertising_version,
            ),
        ]

        try:
            user = await self.user_service.create_account(
                nome=payload.nome,
                email=payload.email,
                senha_hash=password_hash,
                consents=consents,
                ip=ip,
                apelido=payload.apelido,
                data_nascimento=payload.data_nascimento,
                telefone=payload.telefone,
                create_student=payload.aluno is not None,
                altura_cm=payload.aluno.altura_cm if payload.aluno else None,
                create_trainer=payload.treinador is not None,
                cref=payload.treinador.cref if payload.treinador else None,
                create_nutritionist=payload.nutricionista is not None,
                crn=payload.nutricionista.crn if payload.nutricionista else None,
            )
        except IntegrityError as exc:
            if _EMAIL_UNIQUE_INDEX in str(exc.orig):
                raise ConflictError(
                    detail="Já existe uma conta cadastrada com este e-mail.",
                    code="email_ja_cadastrado",
                ) from exc
            raise

        await self._send_verification_email(user)
        return user

    async def _send_verification_email(self, user: Usuario) -> None:
        # Only the hash goes to the database. The raw value goes only in the email.
        token = issue_opaque_token(email_verification_token_ttl())
        await self.repository.create_user_token(
            user_id=user.id,
            token_type=TipoTokenUsuario.VERIFICACAO_EMAIL,
            token_hash=token.hash,
            expires_at=token.expires_at,
        )

        try:
            await self.email_sender.send_email_verification(
                to=user.email, name=user.nome, token=token.value
            )
        except Exception:
            logger.exception("Falha ao enviar e-mail de verificação (usuário %s).", user.id)