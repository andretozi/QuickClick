"""
Apresentação · API HTTP

Cria o FastAPI com todas as rotas debaixo de /api e aplica os cabeçalhos HTTP de segurança.
Por segurança (redução de superfície de ataque), a documentação interativa (/docs, /redoc e
/openapi.json) fica desligada por padrão.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, Request

from backend.application.casos_de_uso import CasosDeUso
from backend.application.portas import ServicoToken
from backend.presentation.http.autenticacao import dependencia_do_vendedor
from backend.presentation.http.erros import registrar_tratamento_de_erros
from backend.presentation.http.rotas import criar_rotas
from backend.presentation.http.rotas_anuncios import criar_rotas_anuncios
from backend.presentation.http.rotas_ia import criar_rotas_ia

PREFIXO = "/api"

CABECALHOS_DE_SEGURANCA: tuple[tuple[str, str], ...] = (
    ("Strict-Transport-Security", "max-age=31536000; includeSubDomains"),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"),
    (
        "Content-Security-Policy",
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'",
    ),
)


def registrar_cabecalhos_de_seguranca(app: FastAPI) -> None:
    @app.middleware("http")
    async def adicionar_cabecalhos(request: Request, call_next):
        resposta = await call_next(request)
        for nome, valor in CABECALHOS_DE_SEGURANCA:
            if nome not in resposta.headers:
                resposta.headers[nome] = valor
        return resposta


def criar_api(
    casos: CasosDeUso,
    identificar_vendedor: Callable[..., int] | None = None,
    servico_token: ServicoToken | None = None,
    documentacao_ativa: bool = False,
) -> FastAPI:
    """`identificar_vendedor` é um fallback opcional para testes ou modo sem token."""
    app = FastAPI(
        title="Quick Click API",
        description="Clicou, vendeu. Automação de vendas multicanal com IA.",
        version="0.1.0",
        docs_url="/docs" if documentacao_ativa else None,
        redoc_url="/redoc" if documentacao_ativa else None,
        openapi_url="/openapi.json" if documentacao_ativa else None,
    )
    registrar_cabecalhos_de_seguranca(app)
    registrar_tratamento_de_erros(app)
    app.include_router(criar_rotas(casos, identificar_vendedor, servico_token=servico_token), prefix=PREFIXO)
    vendedor_atual = Annotated[int, Depends(dependencia_do_vendedor(servico_token, identificar_vendedor))]
    app.include_router(criar_rotas_ia(casos, vendedor_atual), prefix=PREFIXO)
    app.include_router(criar_rotas_anuncios(casos, vendedor_atual), prefix=PREFIXO)
    return app
