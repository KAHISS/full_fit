import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.modules.auth.models import TipoTokenUsuario
from app.modules.auth.repository import AuthRepository


async def test_create_user_token_persists_verification_token_hash():
    session = MagicMock()
    session.flush = AsyncMock()
    repository = AuthRepository(session)
    user_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(hours=1)

    token = await repository.create_user_token(
        user_id=user_id,
        token_type=TipoTokenUsuario.VERIFICACAO_EMAIL,
        token_hash="a" * 64,
        expires_at=expires_at,
    )

    session.add.assert_called_once_with(token)
    session.flush.assert_awaited_once()
    assert token.id_usuario == user_id
    assert token.tipo == TipoTokenUsuario.VERIFICACAO_EMAIL
    assert token.token_hash == "a" * 64
    assert token.expira_em == expires_at
