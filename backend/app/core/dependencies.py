import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.users.models import Usuario
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService

MOCK_CURRENT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserService:
    repository = UserRepository(session)
    return UserService(repository)

# Mudar quando o módulo de users ficar pronto
async def get_current_user_mock(
    service: Annotated[UserService, Depends(get_user_service)],
) -> Usuario:
    return await service.get_user_by_id(MOCK_CURRENT_USER_ID, load_profiles=True)


CurrentUser = Annotated[Usuario, Depends(get_current_user_mock)]