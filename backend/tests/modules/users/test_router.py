import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user_mock, get_user_service
from app.core.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    app_error_handler,
)
from app.modules.users.models import StatusUsuario
from app.modules.users.router import router


def _make_user_payload(**kwargs):
    now = datetime.now(UTC)
    defaults = {
        "id": uuid.uuid4(),
        "nome": "João Silva",
        "apelido": "joao",
        "email": "joao@example.com",
        "data_nascimento": None,
        "telefone": None,
        "biografia": None,
        "foto_url": None,
        "status_usuario": StatusUsuario.ATIVO,
        "email_verificado": True,
        "ultimo_login": now,
        "criado_em": now,
        "atualizado_em": now,
        "aluno": None,
        "treinador": None,
        "nutricionista": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.fixture
def mock_user():
    return _make_user_payload()


@pytest.fixture
def mock_service():
    return AsyncMock()


@pytest.fixture
async def client(mock_user, mock_service):
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(router)
    app.dependency_overrides[get_current_user_mock] = lambda: mock_user
    app.dependency_overrides[get_user_service] = lambda: mock_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_get_me_success(client, mock_user, mock_service):
    mock_service.get_user_by_id.return_value = mock_user

    response = await client.get("/users/me")

    assert response.status_code == 200
    assert response.json()["id"] == str(mock_user.id)


async def test_get_me_not_found_error(client, mock_service):
    mock_service.get_user_by_id.side_effect = NotFoundError()

    response = await client.get("/users/me")

    assert response.status_code == 404


async def test_update_me_success(client, mock_user, mock_service):
    mock_user.nome = "Nome Atualizado"
    mock_service.update_profile.return_value = mock_user

    response = await client.patch("/users/me", json={"nome": "Nome Atualizado"})

    assert response.status_code == 200
    assert response.json()["nome"] == "Nome Atualizado"


async def test_update_me_bad_request_error(client, mock_service):
    mock_service.update_profile.side_effect = BadRequestError()

    response = await client.patch("/users/me", json={"altura_cm": 180})

    assert response.status_code == 400


async def test_activate_student_profile_success(client, mock_user, mock_service):
    mock_user.aluno = SimpleNamespace(altura_cm=175, condicoes_saude=[])
    mock_service.activate_student_profile.return_value = mock_user

    response = await client.post("/users/me/profiles/student", json={"altura_cm": 175})

    assert response.status_code == 201
    assert response.json()["aluno"]["altura_cm"] == 175


async def test_activate_student_profile_conflict_error(client, mock_service):
    mock_service.activate_student_profile.side_effect = ConflictError()

    response = await client.post("/users/me/profiles/student", json={"altura_cm": 175})

    assert response.status_code == 409


async def test_activate_trainer_profile_success(client, mock_user, mock_service):
    mock_user.treinador = SimpleNamespace(
        cref="123456-G/SP", status_verificacao="NAO_ENVIADO"
    )
    mock_service.activate_trainer_profile.return_value = mock_user

    response = await client.post(
        "/users/me/profiles/trainer", json={"cref": "123456-G/SP"}
    )

    assert response.status_code == 201
    assert response.json()["treinador"]["cref"] == "123456-G/SP"


async def test_activate_trainer_profile_conflict_error(client, mock_service):
    mock_service.activate_trainer_profile.side_effect = ConflictError()

    response = await client.post(
        "/users/me/profiles/trainer", json={"cref": "123456-G/SP"}
    )

    assert response.status_code == 409


async def test_activate_nutritionist_profile_success(client, mock_user, mock_service):
    mock_user.nutricionista = SimpleNamespace(
        crn="12345", status_verificacao="NAO_ENVIADO"
    )
    mock_service.activate_nutritionist_profile.return_value = mock_user

    response = await client.post(
        "/users/me/profiles/nutritionist", json={"crn": "12345"}
    )

    assert response.status_code == 201
    assert response.json()["nutricionista"]["crn"] == "12345"


async def test_activate_nutritionist_profile_conflict_error(client, mock_service):
    mock_service.activate_nutritionist_profile.side_effect = ConflictError()

    response = await client.post(
        "/users/me/profiles/nutritionist", json={"crn": "12345"}
    )

    assert response.status_code == 409


async def test_delete_me_success(client, mock_service):
    response = await client.delete("/users/me")

    assert response.status_code == 204
    mock_service.delete_account.assert_awaited_once()


async def test_delete_me_not_found_error(client, mock_service):
    mock_service.delete_account.side_effect = NotFoundError()

    response = await client.delete("/users/me")

    assert response.status_code == 404


async def test_get_public_user_success(client, mock_user, mock_service):
    target_id = uuid.uuid4()
    public_user = _make_user_payload(id=target_id, nome="Maria Souza")
    mock_service.get_user_by_id.return_value = public_user

    response = await client.get(f"/users/{target_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(target_id)
    assert "email" not in response.json()


async def test_get_public_user_not_found_error(client, mock_service):
    mock_service.get_user_by_id.side_effect = NotFoundError()

    response = await client.get(f"/users/{uuid.uuid4()}")

    assert response.status_code == 404
