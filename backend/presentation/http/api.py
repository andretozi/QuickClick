"""
Apresentação · API HTTP

Cria o FastAPI com todas as rotas debaixo de /api.
A documentação automática fica em /docs (Swagger) e /redoc.
"""

from collections.abc import Callable

from fastapi import FastAPI

from backend.application.casos_de_uso import CasosDeUso
from backend.presentation.http.erros import registrar_tratamento_de_erros
from backend.presentation.http.rotas import criar_rotas

PREFIXO = "/api"


def criar_api(casos: CasosDeUso, identificar_vendedor: Callable[[], int]) -> FastAPI:
    """`identificar_vendedor` diz de quem é cada pedido (hoje, sempre o vendedor de demonstração)."""
    app = FastAPI(
        title="Quick Click API",
        description="Clicou, vendeu. Automação de vendas multicanal com IA.",
        version="0.1.0",
    )
    registrar_tratamento_de_erros(app)
    app.include_router(criar_rotas(casos, identificar_vendedor), prefix=PREFIXO)
    return app
