"""Primitivas de segurança do módulo de autenticação.

Tudo aqui é função pura (sem banco, sem FastAPI): recebe dados e devolve dados. Isso deixa
o código fácil de testar e de reaproveitar nos fluxos de login, verificação de e-mail e
recuperação de senha.
"""

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

# recommended() usa Argon2id com parâmetros seguros por padrão.
_password_hasher = PasswordHash.recommended()

# Os limites de tamanho vêm do .env (PASSWORD_MIN_LENGTH / PASSWORD_MAX_LENGTH).
# O máximo evita que alguém envie uma senha gigante só para gastar CPU da API
# durante o hash (ataque de negação de serviço).


def _weak_password_error(message: str) -> BadRequestError:
    return BadRequestError(
        detail=message,
        code="senha_fraca",
        extra=[{"key": "senha", "message": message}],
    )


def validate_password_strength(password: str) -> None:
    """Regras de senha. Lança BadRequestError se a senha não servir."""
    if len(password) < settings.password_min_length:
        raise _weak_password_error(
            f"A senha deve ter pelo menos {settings.password_min_length} caracteres."
        )
    if len(password) > settings.password_max_length:
        raise _weak_password_error(
            f"A senha deve ter no máximo {settings.password_max_length} caracteres."
        )
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise _weak_password_error("A senha deve conter pelo menos uma letra e um número.")


def hash_password(password: str) -> str:
    """Devolve o hash Argon2id (com salt aleatório embutido) para guardar em senha_hash."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Confere a senha digitada contra o hash salvo. Senha errada nunca lança erro."""
    return _password_hasher.verify(password, password_hash)


# ---------------------------------------------------------------------------
# Access token (JWT)
# ---------------------------------------------------------------------------

_ACCESS_TOKEN_TYPE = "access"


def create_access_token(user_id: uuid.UUID) -> str:
    """JWT de curta duração (padrão 15 min) que prova quem é o usuário."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": _ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID:
    """Valida assinatura, expiração e tipo; devolve o id do usuário.

    Qualquer problema vira UnauthorizedError (HTTP 401) com um code estável, para o app
    Flutter decidir o que fazer (por exemplo, tentar o refresh).
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        # Precisa vir antes de InvalidTokenError: é subclasse dela.
        raise UnauthorizedError(detail="Sessão expirada.", code="token_expirado") from None
    except jwt.InvalidTokenError:
        raise UnauthorizedError(detail="Token inválido.", code="token_invalido") from None

    # Impede usar como access token um JWT emitido para outra finalidade.
    if payload.get("type") != _ACCESS_TOKEN_TYPE:
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
    """Token aleatório de 256 bits, seguro para ir em URL ou JSON."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 em hexadecimal (64 caracteres): é o que vai para token_hash no banco.

    SHA-256 (e não Argon2) porque o token já tem entropia altíssima, então um hash lento
    não acrescenta nada. Além disso, o hash precisa ser determinístico para podermos
    buscar a linha com WHERE token_hash = ...
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class OpaqueToken:
    value: str
    hash: str
    expires_at: datetime


def issue_opaque_token(ttl: timedelta) -> OpaqueToken:
    """Gera o token, o hash e a data de expiração de uma vez só."""
    value = generate_opaque_token()
    return OpaqueToken(
        value=value,
        hash=hash_token(value),
        expires_at=datetime.now(UTC) + ttl,
    )
