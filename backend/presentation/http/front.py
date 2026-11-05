"""
Apresentação · Entrega do front

O front buildado (frontend/dist) é servido em todos os endereços que não são da API.
Um caminho que não é arquivo cai no index.html, porque as páginas do React usam "#/".
O index.html nunca é guardado em cache pelo navegador para evitar apontar para bundles
antigos após um deploy; os assets com hash do Vite (/assets/*) recebem cache imutável.
"""

from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class FrontEstatico(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        caminho_relativo = path.replace("\\", "/").lstrip("/")
        eh_html_entrada = caminho_relativo in ("", ".", "index.html") or caminho_relativo.endswith("/index.html")
        try:
            resposta = await super().get_response(path, scope)
        except HTTPException as erro:
            caminho = scope["path"]
            # Endereço desconhecido em /api continua sendo 404 da API, nunca a página do site
            if erro.status_code != 404 or caminho == "/api" or caminho.startswith("/api/"):
                raise
            eh_html_entrada = True
            resposta = await super().get_response("index.html", scope)

        tipo = resposta.headers.get("content-type", "")
        if eh_html_entrada or tipo.startswith("text/html"):
            resposta.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            resposta.headers["Pragma"] = "no-cache"
            resposta.headers["Expires"] = "0"
        elif caminho_relativo.startswith("assets/") or scope.get("path", "").startswith("/assets/"):
            resposta.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resposta


def montar_front(app: FastAPI, pasta: Path) -> None:
    """Liga o front no "/" depois das rotas da API. Sem build, só a API responde."""
    if (pasta / "index.html").is_file():
        app.mount("/", FrontEstatico(directory=pasta, html=True), name="front")
