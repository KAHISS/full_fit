import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.core.exceptions import BadRequestError, ConflictError
from app.modules.auth.models import TipoTokenUsuario
from app.modules.auth.schemas import RegisterRequest
from app.modules.auth.security import hash_token, verify_password
from app.modules.auth.service import AuthService
from app.modules.users.models import TipoConsentimento


def _request(**overrides) -> RegisterRequest:
    data = {
        "nome": "João Silva",
        "email": "Joao@Example.com",
        "senha": "senha1234",
        "aluno": {"altura_cm": 180},
        "aceite_termos_uso": True,
        "aceite_privacidade": True,
    }
    data.update(overrides)
    return RegisterRequest(**data)


@pytest.fixture
def created_user():
    return SimpleNamespace(id=uuid.uuid4(), nome="João Silva", email="joao@example.com")


@pytest.fixture
def user_service(created_user):
    service = AsyncMock()
    service.create_account.return_value = created_user
    return service


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def email_sender():
    return AsyncMock()


@pytest.fixture
def service(user_service, repo, email_sender):
    return AuthService(user_service, repo, email_sender)


async def test_register_creates_account_and_returns_user(service, user_service, created_user):
    user = await service.register(_request(), ip="203.0.113.7")

    assert user is created_user
    user_service.create_account.assert_awaited_once()
    kwargs = user_service.create_account.await_args.kwargs
    assert kwargs["nome"] == "João Silva"
    # EmailStr already normalizes the domain; UserService lowercases the rest.
    assert kwargs["email"] == "Joao@example.com"
    assert kwargs["ip"] == "203.0.113.7"


async def test_register_never_passes_plain_text_password(service, user_service):
    await service.register(_request(senha="senha1234"), ip="203.0.113.7")

    password_hash = user_service.create_account.await_args.kwargs["senha_hash"]
    assert password_hash != "senha1234"
    assert verify_password("senha1234", password_hash) is True


async def test_register_rejects_weak_password_before_touching_database(service, user_service, repo):
    with pytest.raises(BadRequestError) as exc:
        await service.register(_request(senha="curta1"), ip="203.0.113.7")

    assert exc.value.code == "senha_fraca"
    user_service.create_account.assert_not_awaited()
    repo.create_user_token.assert_not_awaited()


async def test_register_sends_three_consents_with_configured_version(service, user_service):
    await service.register(_request(aceite_publicidade=False), ip="203.0.113.7")

    consents = user_service.create_account.await_args.kwargs["consents"]
    assert consents == [
        (TipoConsentimento.TERMOS_USO, True, settings.consent_terms_version),
        (TipoConsentimento.PRIVACIDADE, True, settings.consent_privacy_version),
        (TipoConsentimento.PUBLICIDADE, False, settings.consent_advertising_version),
    ]


async def test_register_uses_document_versions_from_settings(service, user_service, monkeypatch):
    monkeypatch.setattr(settings, "consent_terms_version", "2.1")

    await service.register(_request(), ip="203.0.113.7")

    consents = user_service.create_account.await_args.kwargs["consents"]
    assert consents[0] == (TipoConsentimento.TERMOS_USO, True, "2.1")


async def test_register_student_creates_only_student_profile(service, user_service):
    await service.register(_request(aluno={"altura_cm": 180}), ip="203.0.113.7")

    kwargs = user_service.create_account.await_args.kwargs
    assert kwargs["create_student"] is True
    assert kwargs["altura_cm"] == 180
    assert kwargs["create_trainer"] is False
    assert kwargs["create_nutritionist"] is False


async def test_register_professional_carries_council_registration(service, user_service):
    request = _request(
        aluno=None,
        treinador={"cref": "012345-G/BA"},
        nutricionista={"crn": "CRN-9 1234"},
    )

    await service.register(request, ip="203.0.113.7")

    kwargs = user_service.create_account.await_args.kwargs
    assert kwargs["create_student"] is False
    assert kwargs["create_trainer"] is True
    assert kwargs["cref"] == "012345-G/BA"
    assert kwargs["create_nutritionist"] is True
    assert kwargs["crn"] == "CRN-9 1234"


async def test_register_stores_only_the_verification_token_hash(
    service, repo, email_sender, created_user
):
    await service.register(_request(), ip="203.0.113.7")

    repo.create_user_token.assert_awaited_once()
    saved = repo.create_user_token.await_args.kwargs
    sent = email_sender.send_email_verification.await_args.kwargs

    assert saved["user_id"] == created_user.id
    assert saved["token_type"] == TipoTokenUsuario.VERIFICACAO_EMAIL
    assert saved["token_hash"] == hash_token(sent["token"])
    assert saved["token_hash"] != sent["token"]
    assert sent["to"] == created_user.email
    assert sent["name"] == created_user.nome


async def test_register_does_not_fail_if_email_sending_fails(
    service, repo, email_sender, created_user
):
    email_sender.send_email_verification.side_effect = RuntimeError("smtp is down")

    user = await service.register(_request(), ip="203.0.113.7")

    assert user is created_user
    repo.create_user_token.assert_awaited_once()


async def test_register_propagates_email_conflict_from_user_service(service, user_service, repo):
    user_service.create_account.side_effect = ConflictError(
        detail="Já existe uma conta cadastrada com este e-mail.",
        code="email_ja_cadastrado",
    )

    with pytest.raises(ConflictError) as exc:
        await service.register(_request(), ip="203.0.113.7")

    assert exc.value.code == "email_ja_cadastrado"
    repo.create_user_token.assert_not_awaited()


async def test_register_converts_email_race_into_conflict(service, user_service, repo):
    driver_error = Exception(
        'duplicate key value violates unique constraint "uq_usuario_email_lower"'
    )
    user_service.create_account.side_effect = IntegrityError("INSERT", {}, driver_error)

    with pytest.raises(ConflictError) as exc:
        await service.register(_request(), ip="203.0.113.7")

    assert exc.value.code == "email_ja_cadastrado"
    repo.create_user_token.assert_not_awaited()


async def test_register_does_not_hide_other_integrity_errors(service, user_service):
    driver_error = Exception('violates check constraint "status_usuario_valido"')
    user_service.create_account.side_effect = IntegrityError("INSERT", {}, driver_error)

    with pytest.raises(IntegrityError):
        await service.register(_request(), ip="203.0.113.7")
