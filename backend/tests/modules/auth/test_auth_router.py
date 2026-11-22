import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_auth_service, get_client_ip
from app.core.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    app_error_handler,
    validation_exception_handler,
)
from app.modules.auth.router import router
from app.modules.users.models import StatusUsuario


def _created_user(**overrides):
    now = datetime.now(UTC)
    data = {
        "id": uuid.uuid4(),
        "nome": "João Silva",
        "apelido": None,
        "email": "joao@example.com",
        "data_nascimento": None,
        "telefone": None,
        "biografia": None,
        "foto_url": None,
        "status_usuario": StatusUsuario.PENDENTE_EMAIL,
        "email_verificado": False,
        "ultimo_login": None,
        "criado_em": now,
        "atualizado_em": now,
        "aluno": SimpleNamespace(altura_cm=180, condicoes_saude=[]),
        "treinador": None,
        "nutricionista": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _body(**overrides):
    data = {
        "nome": "João Silva",
        "email": "joao@example.com",
        "senha": "senha1234",
        "aluno": {"altura_cm": 180},
        "aceite_termos_uso": True,
        "aceite_privacidade": True,
    }
    data.update(overrides)
    return data


@pytest.fixture
def mock_service():
    return AsyncMock()


@pytest.fixture
async def client(mock_service):
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(router)
    app.dependency_overrides[get_auth_service] = lambda: mock_service
    app.dependency_overrides[get_client_ip] = lambda: "203.0.113.7"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_register_returns_201_with_user_pending_email(client, mock_service):
    user = _created_user()
    mock_service.register.return_value = user

    response = await client.post("/auth/register", json=_body())

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["status_usuario"] == "PENDENTE_EMAIL"
    assert data["email_verificado"] is False
    assert data["aluno"]["altura_cm"] == 180


async def test_register_never_returns_password_or_hash(client, mock_service):
    mock_service.register.return_value = _created_user()

    response = await client.post("/auth/register", json=_body())

    response_text = response.text
    assert "senha" not in response_text
    assert "hash" not in response_text
    assert "senha1234" not in response_text


async def test_register_passes_request_ip_to_service(client, mock_service):
    mock_service.register.return_value = _created_user()

    await client.post("/auth/register", json=_body())

    mock_service.register.assert_awaited_once()
    assert mock_service.register.await_args.kwargs["ip"] == "203.0.113.7"


async def test_register_without_profile_returns_400_validation_error(client, mock_service):
    response = await client.post("/auth/register", json=_body(aluno=None))

    assert response.status_code == 400
    assert response.json()["code"] == "erro_validacao"
    mock_service.register.assert_not_awaited()


async def test_register_invalid_email_returns_400_validation_error(client, mock_service):
    response = await client.post("/auth/register", json=_body(email="nao-e-email"))

    assert response.status_code == 400
    assert response.json()["code"] == "erro_validacao"
    mock_service.register.assert_not_awaited()


async def test_register_duplicate_email_returns_409(client, mock_service):
    mock_service.register.side_effect = ConflictError(
        detail="Já existe uma conta cadastrada com este e-mail.",
        code="email_ja_cadastrado",
    )

    response = await client.post("/auth/register", json=_body())

    assert response.status_code == 409
    assert response.json()["code"] == "email_ja_cadastrado"


async def test_register_weak_password_returns_400(client, mock_service):
    mock_service.register.side_effect = BadRequestError(
        detail="A senha deve ter pelo menos 8 caracteres.", code="senha_fraca"
    )

    response = await client.post("/auth/register", json=_body(senha="abc1"))

    assert response.status_code == 400
    assert response.json()["code"] == "senha_fraca"


async def test_register_without_required_consent_returns_400(client, mock_service):
    mock_service.register.side_effect = BadRequestError(
        detail="O aceite dos Termos de Uso e da Política de Privacidade é obrigatório.",
        code="consentimentos_obrigatorios_ausentes",
    )

    response = await client.post("/auth/register", json=_body(aceite_termos_uso=False))

    assert response.status_code == 400
    assert response.json()["code"] == "consentimentos_obrigatorios_ausentes"
