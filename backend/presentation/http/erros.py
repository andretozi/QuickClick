"""
Apresentação · Erros

Cada erro de negócio vira uma resposta HTTP clara, sempre no mesmo formato:
    {"erro": {"codigo": "...", "mensagem": "...", "plano_sugerido": "..."}}
A mensagem já vem pronta para aparecer na tela do vendedor.
"""

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from backend.domain.erros import (
    ErroDeDominio,
    LimiteDoPlanoAtingido,
    MarketplaceEmBreve,
    MarketplaceNaoEncontrado,
    VendedorNaoEncontrado,
)

STATUS_POR_ERRO: tuple[tuple[type[ErroDeDominio], int], ...] = (
    (MarketplaceNaoEncontrado, 404),
    (VendedorNaoEncontrado, 404),
    (MarketplaceEmBreve, 409),
    (LimiteDoPlanoAtingido, 403),
)

ERROS_HTTP = {
    404: ("nao_encontrado", "Esse endereço não existe na API."),
    405: ("metodo_nao_permitido", "Esse endereço não aceita esse tipo de pedido."),
}


def _resposta(status: int, codigo: str, mensagem: str, **extras: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"erro": {"codigo": codigo, "mensagem": mensagem, **extras}})


def registrar_tratamento_de_erros(app: FastAPI) -> None:
    @app.exception_handler(ErroDeDominio)
    async def erro_de_negocio(request: Request, erro: ErroDeDominio) -> JSONResponse:
        status = next((codigo for tipo, codigo in STATUS_POR_ERRO if isinstance(erro, tipo)), 400)
        extras = {}
        if isinstance(erro, LimiteDoPlanoAtingido) and erro.plano_sugerido is not None:
            extras["plano_sugerido"] = erro.plano_sugerido.slug
        return _resposta(status, erro.codigo, erro.mensagem, **extras)

    @app.exception_handler(HTTPException)
    async def erro_http(request: Request, erro: HTTPException):
        # Dentro de /api, o mesmo formato dos erros de negócio; fora dela, o padrão do FastAPI
        if not request.url.path.startswith("/api"):
            return await http_exception_handler(request, erro)
        codigo, mensagem = ERROS_HTTP.get(erro.status_code, ("erro_http", "Não deu pra atender esse pedido."))
        return _resposta(erro.status_code, codigo, mensagem)
