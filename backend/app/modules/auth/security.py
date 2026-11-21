import hashlib
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.config import settings
from app.core.exceptions import BadRequestError, UnauthorizedError

# ---------------------------------------------------------------------------
# Senha
# ---------------------------------------------------------------------------

_password_hash = PasswordHash.recommended()


def validate_password_strength(password: str) -> None:
    if len(password) < settings.password_min_length:
        raise BadRequestError(
            detail=f"A senha deve ter pelo menos {settings.password_min_length} caracteres.",
            code="senha_fraca",
        )
    if len(password) > settings.password_max_length:
        raise BadRequestError(
            detail=f"A senha deve ter no máximo {settings.password_max_length} caracteres.",
            code="senha_fraca",
        )
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise BadRequestError(
            detail="A senha deve conter pelo menos uma letra e um número.",
            code="senha_fraca",
        )


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


# ---------------------------------------------------------------------------
# Access token (JWT)
# ---------------------------------------------------------------------------

_TIPO_ACCESS = "access"


def create_access_token(user_id: uuid.UUID) -> str:
    agora = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": _TIPO_ACCESS,
        "iat": agora,
        "exp": agora + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID:

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(detail="Sessão expirada.", code="token_expirado") from None
    except jwt.InvalidTokenError:
        raise UnauthorizedError(detail="Token inválido.", code="token_invalido") from None

    if payload.get("type") != _TIPO_ACCESS:
        raise UnauthorizedError(detail="Token inválido.", code="token_invalido")

    try:
        return uuid.UUID(payload["sub"])
    except ValueError:
        raise UnauthorizedError(detail="Token inválido.", code="token_invalido") from None


# ---------------------------------------------------------------------------
# Tokens opacos (refresh, verificação de e-mail, recuperação de senha)
# ---------------------------------------------------------------------------

def refresh_token_ttl() -> timedelta:
    return timedelta(days=settings.refresh_token_expire_days)


def email_verification_token_ttl() -> timedelta:
    return timedelta(hours=settings.email_verification_token_expire_hours)


def password_reset_token_ttl() -> timedelta:
    return timedelta(minutes=settings.password_reset_token_expire_minutes)


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class OpaqueToken:
    value: str 
    hash: str
    expires_at: datetime


def issue_opaque_token(ttl: timedelta) -> OpaqueToken:
    value = generate_opaque_token()
    return OpaqueToken(
        value=value,
        hash=hash_token(value),
        expires_at=datetime.now(UTC) + ttl,
    )