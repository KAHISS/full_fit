import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import settings
from app.core.exceptions import BadRequestError, UnauthorizedError
from app.modules.auth.security import (
    create_access_token,
    decode_access_token,
    email_verification_token_ttl,
    generate_opaque_token,
    hash_password,
    hash_token,
    issue_opaque_token,
    password_reset_token_ttl,
    refresh_token_ttl,
    validate_password_strength,
    verify_password,
)

# ---------------------------------------------------------------- password


def test_hash_password_does_not_store_plain_text():
    hashed = hash_password("senha123")

    assert hashed != "senha123"
    assert hashed.startswith("$argon2")


def test_hash_password_uses_a_different_salt_on_each_call():
    assert hash_password("senha123") != hash_password("senha123")


def test_verify_password_accepts_correct_password():
    hashed = hash_password("senha123")

    assert verify_password("senha123", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("senha123")

    assert verify_password("outra456", hashed) is False


@pytest.mark.parametrize("password", ["abc12345", "Senha1234", "a" * 127 + "1"])
def test_validate_password_strength_accepts_valid_passwords(password):
    validate_password_strength(password)


@pytest.mark.parametrize(
    "password",
    [
        "abc123",  # too short
        "somenteletras",  # no digit
        "1234567890",  # no letter
        "a1" * 65,  # 130 characters, too long
    ],
)
def test_validate_password_strength_rejects_weak_passwords(password):
    with pytest.raises(BadRequestError) as exc:
        validate_password_strength(password)

    assert exc.value.code == "senha_fraca"


# ---------------------------------------------------------- access token


def test_access_token_round_trip_returns_same_user():
    user_id = uuid.uuid4()

    token = create_access_token(user_id)

    assert decode_access_token(token) == user_id


def test_expired_access_token_raises_token_expirado(monkeypatch):
    monkeypatch.setattr(settings, "access_token_expire_minutes", -1)
    token = create_access_token(uuid.uuid4())

    with pytest.raises(UnauthorizedError) as exc:
        decode_access_token(token)

    assert exc.value.code == "token_expirado"


def test_access_token_signed_with_another_key_is_rejected():
    now = datetime.now(UTC)
    forged = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        "x" * 40,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError) as exc:
        decode_access_token(forged)

    assert exc.value.code == "token_invalido"


def test_token_of_another_type_is_not_an_access_token():
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError) as exc:
        decode_access_token(token)

    assert exc.value.code == "token_invalido"


def test_token_without_sub_is_rejected():
    now = datetime.now(UTC)
    token = jwt.encode(
        {"type": "access", "iat": now, "exp": now + timedelta(minutes=5)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(token)


def test_token_with_non_uuid_sub_is_rejected():
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "nao-e-uuid",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(token)


@pytest.mark.parametrize("garbage", ["", "abc", "a.b.c"])
def test_arbitrary_text_is_not_an_access_token(garbage):
    with pytest.raises(UnauthorizedError) as exc:
        decode_access_token(garbage)

    assert exc.value.code == "token_invalido"


# ----------------------------------------------------------- opaque tokens


def test_generate_opaque_token_is_unique():
    assert len({generate_opaque_token() for _ in range(100)}) == 100


def test_hash_token_is_deterministic_and_does_not_reveal_the_token():
    token = generate_opaque_token()

    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token
    assert len(hash_token(token)) == 64


def test_hash_token_differs_for_different_tokens():
    assert hash_token("a") != hash_token("b")


def test_issue_opaque_token_returns_value_hash_and_expiration():
    before = datetime.now(UTC)

    issued = issue_opaque_token(password_reset_token_ttl())

    assert issued.hash == hash_token(issued.value)
    assert issued.value != issued.hash
    assert before + password_reset_token_ttl() <= issued.expires_at
    assert issued.expires_at <= datetime.now(UTC) + password_reset_token_ttl()


def test_ttls_come_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "refresh_token_expire_days", 7)
    monkeypatch.setattr(settings, "email_verification_token_expire_hours", 2)
    monkeypatch.setattr(settings, "password_reset_token_expire_minutes", 10)

    assert refresh_token_ttl() == timedelta(days=7)
    assert email_verification_token_ttl() == timedelta(hours=2)
    assert password_reset_token_ttl() == timedelta(minutes=10)


def test_password_limits_come_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "password_min_length", 12)
    monkeypatch.setattr(settings, "password_max_length", 20)

    validate_password_strength("abcdefghij12")  # 12 characters: ok

    with pytest.raises(BadRequestError) as too_short:
        validate_password_strength("abcdefghi12")  # 11 characters
    with pytest.raises(BadRequestError) as too_long:
        validate_password_strength("a" * 20 + "1")  # 21 characters

    assert "12" in too_short.value.detail
    assert "20" in too_long.value.detail


def test_config_rejects_min_greater_than_max(monkeypatch):
    from app.config import Settings

    with pytest.raises(ValueError):
        Settings(password_min_length=30, password_max_length=10)
