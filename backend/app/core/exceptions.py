import logging
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_HTTP_PADRAO: dict[int, tuple[str, str]] = {
    400: ("requisicao_invalida", "Requisição inválida."),
    401: ("nao_autenticado", "Não autenticado."),
    403: ("acesso_negado", "Acesso negado."),
    404: ("nao_encontrado", "Recurso não encontrado."),
    405: ("metodo_nao_permitido", "Método não permitido."),
    429: ("muitas_requisicoes", "Muitas requisições. Tente novamente em instantes."),
}

_ORIGENS = {"body", "query", "path", "header", "cookie"}


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str,
        extra: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.extra = extra if extra is not None else []


class BadRequestError(AppError):
    def __init__(
        self,
        detail: str = "Requisição inválida.",
        code: str = "requisicao_invalida",
        extra: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            code=code,
            extra=extra,
        )


class UnauthorizedError(AppError):
    def __init__(
        self,
        detail: str = "Não autenticado.",
        code: str = "nao_autenticado",
        extra: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code=code,
            extra=extra,
        )


class ForbiddenError(AppError):
    def __init__(
        self,
        detail: str = "Acesso negado.",
        code: str = "acesso_negado",
        extra: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            code=code,
            extra=extra,
        )


class NotFoundError(AppError):
    def __init__(
        self,
        detail: str = "Recurso não encontrado.",
        code: str = "nao_encontrado",
        extra: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            code=code,
            extra=extra,
        )


class ConflictError(AppError):
    def __init__(
        self,
        detail: str = "Conflito de dados.",
        code: str = "conflito",
        extra: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            code=code,
            extra=extra,
        )


def _format_error_payload(
    detail: str,
    code: str,
    extra: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "detail": detail,
        "code": code,
        "extra": extra if extra is not None else [],
    }


def _chave_do_campo(loc: tuple[Any, ...]) -> str:
    partes = [p for p in loc if isinstance(p, str) and p not in _ORIGENS]
    return partes[-1] if partes else "geral"


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code,
        content=_format_error_payload(
            detail=exc.detail,
            code=exc.code,
            extra=exc.extra,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    extra: list[dict[str, str]] = [
        {
            "key": _chave_do_campo(tuple(err.get("loc", ()))),
            "message": str(err.get("msg", "Invalid value.")),
        }
        for err in exc.errors()
    ]

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_format_error_payload(
            detail="Erro de validação nos dados enviados.",
            code="erro_validacao",
            extra=extra,
        ),
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code, detail = _HTTP_PADRAO.get(
        exc.status_code,
        (
            "erro_http",
            exc.detail if isinstance(exc.detail, str) else "Erro na requisição.",
        ),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_format_error_payload(detail=detail, code=code),
        headers=exc.headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Erro interno não tratado na requisição %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_format_error_payload(
            detail="Erro interno inesperado no servidor.",
            code="erro_interno",
            extra=[],
        ),
    )
