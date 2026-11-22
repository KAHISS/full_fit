import uuid
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email import ConsoleEmailSender, EmailSender
from app.core.exceptions import BadRequestError
from app.db.session import get_db_session
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService
from app.modules.users.models import Usuario
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService

MOCK_CURRENT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserService:
    repository = UserRepository(session)
    return UserService(repository)


def get_email_sender() -> EmailSender:
    return ConsoleEmailSender()


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> AuthService:
    return AuthService(user_service, AuthRepository(session), email_sender)


def get_client_ip(request: Request) -> str:
    if request.client is None:
        raise BadRequestError(
            detail="Não foi possível identificar o IP da requisição.",
            code="ip_indisponivel",
        )
    return request.client.host


ClientIp = Annotated[str, Depends(get_client_ip)]


# Mudar quando o módulo de users ficar pronto
async def get_current_user_mock(
    service: Annotated[UserService, Depends(get_user_service)],
) -> Usuario:
    return await service.get_user_by_id(MOCK_CURRENT_USER_ID, load_profiles=True)


CurrentUser = Annotated[Usuario, Depends(get_current_user_mock)]