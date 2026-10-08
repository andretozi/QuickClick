"""
Apresentação · Entrega do front

O front buildado (frontend/dist) é servido em todos os endereços que não são da API.
Um caminho que não é arquivo cai no index.html, porque as páginas do React usam "#/".
"""

from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class FrontEstatico(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as erro:
            caminho = scope["path"]
            # Endereço desconhecido em /api continua sendo 404 da API, nunca a página do site
            if erro.status_code != 404 or caminho == "/api" or caminho.startswith("/api/"):
                raise
            return await super().get_response("index.html", scope)


def montar_front(app: FastAPI, pasta: Path) -> None:
    """Liga o front no "/" depois das rotas da API. Sem build, só a API responde."""
    if (pasta / "index.html").is_file():
        app.mount("/", FrontEstatico(directory=pasta, html=True), name="front")
