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


class _PayloadTeste(BaseModel):
    nome: str
    idade: int


def _criar_app_teste() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.post("/teste/validacao")
    async def rota_validacao(payload: _PayloadTeste) -> dict[str, str]:
        return {"nome": payload.nome}

    @app.get("/teste/400")
    async def rota_400() -> None:
        raise BadRequestError(
            detail="Dados inconsistentes.", code="dados_inconsistentes"
        )

    @app.get("/teste/401")
    async def rota_401() -> None:
        raise UnauthorizedError(detail="Token expirado.", code="token_expirado")

    @app.get("/teste/403")
    async def rota_403() -> None:
        raise ForbiddenError()

    @app.get("/teste/404")
    async def rota_404() -> None:
        raise NotFoundError()

    @app.get("/teste/409")
    async def rota_409() -> None:
        raise ConflictError()

    @app.get("/teste/500")
    async def rota_500() -> None:
        raise RuntimeError("falha no banco")

    return app


@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient]:
    app = _criar_app_teste()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_validacao_pydantic_retorna_400_com_extra(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/teste/validacao", json={"idade": "invalido"})
    assert response.status_code == 400

    body = response.json()
    assert set(body.keys()) == {"detail", "code", "extra"}
    assert body["code"] == "erro_validacao"
    assert isinstance(body["extra"], list)

    campos_com_erro = {item["key"] for item in body["extra"]}
    assert campos_com_erro == {"nome", "idade"}
    for item in body["extra"]:
        assert set(item.keys()) == {"key", "message"}
        assert isinstance(item["message"], str)
        assert item["message"]


@pytest.mark.parametrize(
    ("rota", "status_esperado", "code_esperado"),
    [
        ("/teste/400", 400, "dados_inconsistentes"),
        ("/teste/401", 401, "token_expirado"),
        ("/teste/403", 403, "acesso_negado"),
        ("/teste/404", 404, "nao_encontrado"),
        ("/teste/409", 409, "conflito"),
    ],
)
async def test_subclasses_app_error(
    client: httpx.AsyncClient,
    rota: str,
    status_esperado: int,
    code_esperado: str,
) -> None:
    response = await client.get(rota)
    assert response.status_code == status_esperado

    body = response.json()
    assert set(body.keys()) == {"detail", "code", "extra"}
    assert isinstance(body["detail"], str)
    assert body["code"] == code_esperado
    assert body["extra"] == []


async def test_excecao_nao_tratada_retorna_500_generico(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/teste/500")
    assert response.status_code == 500

    body = response.json()
    assert set(body.keys()) == {"detail", "code", "extra"}
    assert body["code"] == "erro_interno"
    assert body["extra"] == []
    assert "falha no banco" not in response.text


async def test_rota_inexistente_segue_o_contrato(client: httpx.AsyncClient) -> None:
    response = await client.get("/rota-que-nao-existe")
    assert response.status_code == 404

    body = response.json()
    assert set(body.keys()) == {"detail", "code", "extra"}
    assert body["code"] == "nao_encontrado"
    assert body["extra"] == []


async def test_metodo_nao_permitido(client: httpx.AsyncClient) -> None:
    response = await client.get("/teste/validacao")
    assert response.status_code == 405
    assert response.json()["code"] == "metodo_nao_permitido"


async def test_chave_para_json_invalido(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/teste/validacao",
        content="{isso nao e json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["extra"][0]["key"] == "geral"
