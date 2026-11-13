from collections.abc import AsyncGenerator

import httpx
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


class _TestPayload(BaseModel):
    nome: str
    idade: int


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.post("/test/validation")
    async def validation_route(payload: _TestPayload) -> dict[str, str]:
        return {"nome": payload.nome}

    @app.get("/test/400")
    async def route_400() -> None:
        raise BadRequestError(
            detail="Dados inconsistentes.", code="dados_inconsistentes"
        )

    @app.get("/test/401")
    async def route_401() -> None:
        raise UnauthorizedError(detail="Token expirado.", code="token_expirado")

    @app.get("/test/403")
    async def route_403() -> None:
        raise ForbiddenError()

    @app.get("/test/404")
    async def route_404() -> None:
        raise NotFoundError()

    @app.get("/test/409")
    async def route_409() -> None:
        raise ConflictError()

    @app.get("/test/500")
    async def route_500() -> None:
        raise RuntimeError("falha no banco")

    return app


@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient]:
    app = _create_test_app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_pydantic_validation_returns_400_with_extra(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/test/validation", json={"idade": "invalido"})
    assert response.status_code == 400

    body = response.json()
    assert set(body.keys()) == {"detail", "code", "extra"}
    assert body["code"] == "erro_validacao"
    assert isinstance(body["extra"], list)

    error_fields = {item["key"] for item in body["extra"]}
    assert error_fields == {"nome", "idade"}
    for item in body["extra"]:
        assert set(item.keys()) == {"key", "message"}
        assert isinstance(item["message"], str)
        assert item["message"]


@pytest.mark.parametrize(
    ("route", "expected_status", "expected_code"),
    [
        ("/test/400", 400, "dados_inconsistentes"),
        ("/test/401", 401, "token_expirado"),
        ("/test/403", 403, "acesso_negado"),
        ("/test/404", 404, "nao_encontrado"),
        ("/test/409", 409, "conflito"),
    ],
)
async def test_app_error_subclasses(
    client: httpx.AsyncClient,
    route: str,
    expected_status: int,
    expected_code: str,
) -> None:
    response = await client.get(route)
    assert response.status_code == expected_status

    body = response.json()
    assert set(body.keys()) == {"detail", "code", "extra"}
    assert isinstance(body["detail"], str)
    assert body["code"] == expected_code
    assert body["extra"] == []


async def test_unhandled_exception_returns_generic_500(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/test/500")
    assert response.status_code == 500

    body = response.json()
    assert set(body.keys()) == {"detail", "code", "extra"}
    assert body["code"] == "erro_interno"
    assert body["extra"] == []
    assert "falha no banco" not in response.text


async def test_nonexistent_route_follows_contract(client: httpx.AsyncClient) -> None:
    response = await client.get("/nonexistent-route")
    assert response.status_code == 404

    body = response.json()
    assert set(body.keys()) == {"detail", "code", "extra"}
    assert body["code"] == "nao_encontrado"
    assert body["extra"] == []


async def test_method_not_allowed(client: httpx.AsyncClient) -> None:
    response = await client.get("/test/validation")
    assert response.status_code == 405
    assert response.json()["code"] == "metodo_nao_permitido"


async def test_key_for_invalid_json(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/test/validation",
        content="{isso nao e json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["extra"][0]["key"] == "geral"
