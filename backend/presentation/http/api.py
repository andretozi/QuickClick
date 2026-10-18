"""
Apresentação · API HTTP

Cria o FastAPI com todas as rotas debaixo de /api.
A documentação automática fica em /docs (Swagger) e /redoc.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI

from backend.application.casos_de_uso import CasosDeUso
from backend.application.portas import ServicoToken
from backend.presentation.http.autenticacao import dependencia_do_vendedor
from backend.presentation.http.erros import registrar_tratamento_de_erros
from backend.presentation.http.rotas import criar_rotas
from backend.presentation.http.rotas_anuncios import criar_rotas_anuncios
from backend.presentation.http.rotas_ia import criar_rotas_ia

PREFIXO = "/api"


def criar_api(
    casos: CasosDeUso,
    identificar_vendedor: Callable[..., int] | None = None,
    servico_token: ServicoToken | None = None,
) -> FastAPI:
    """`identificar_vendedor` é um fallback opcional para testes ou modo sem token."""
    app = FastAPI(
        title="Quick Click API",
        description="Clicou, vendeu. Automação de vendas multicanal com IA.",
        version="0.1.0",
    )
    registrar_tratamento_de_erros(app)
    app.include_router(criar_rotas(casos, identificar_vendedor, servico_token=servico_token), prefix=PREFIXO)
    vendedor_atual = Annotated[int, Depends(dependencia_do_vendedor(servico_token, identificar_vendedor))]
    app.include_router(criar_rotas_ia(casos, vendedor_atual), prefix=PREFIXO)
    app.include_router(criar_rotas_anuncios(casos, vendedor_atual), prefix=PREFIXO)
    return app
