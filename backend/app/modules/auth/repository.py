import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import TipoTokenUsuario, TokenUsuario


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user_token(
        self,
        *,
        user_id: uuid.UUID,
        token_type: TipoTokenUsuario,
        token_hash: str,
        expires_at: datetime,
    ) -> TokenUsuario:
        token = TokenUsuario(
            id_usuario=user_id,
            tipo=token_type,
            token_hash=token_hash,
            expira_em=expires_at,
        )
        self.session.add(token)
        await self.session.flush()
        return token