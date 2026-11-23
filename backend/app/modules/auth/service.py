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

        # O Argon2 é lento de propósito e consome CPU. Roda em outra thread para não
        # travar o event loop (e as outras requisições) enquanto calcula.
        password_hash = await asyncio.to_thread(hash_password, password)

        # Registramos também o "não aceitei" (aceito=False): é o histórico de auditoria
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
            # Duas requisições com o mesmo e-mail ao mesmo tempo passam juntas pelo
            # email_exists; o índice único do banco barra a segunda.
            if _EMAIL_UNIQUE_INDEX in str(exc.orig):
                raise ConflictError(
                    detail="Já existe uma conta cadastrada com este e-mail.",
                    code="email_ja_cadastrado",
                ) from exc
            raise

        # Só o hash vai para o banco. O valor puro é usado apenas no e-mail.
        token = issue_opaque_token(email_verification_token_ttl())
        await self.repository.create_user_token(
            user_id=user.id,
            token_type=TipoTokenUsuario.VERIFICACAO_EMAIL,
            token_hash=token.hash,
            expires_at=token.expires_at,
        )
        try:
            await self.email_sender.send_email_verification(
                to=user.email,
                name=user.nome,
                token=token.value,
            )
        except Exception:
            logger.exception("Falha ao enviar e-mail de verificação (usuário %s).", user.id)

        return user