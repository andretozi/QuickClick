"""
Apresentação · Limite do corpo do pedido (middleware ASGI)

Recusa com 413 o pedido que passa do limite nos caminhos com o prefixo: pelo Content-Length
e contando os bytes lidos (pedido sem Content-Length também para). O 413 é uma HTTPException,
então sai no formato de erro da API (erros.py).
"""

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class LimiteDoCorpo:
    def __init__(self, app: ASGIApp, prefixo: str, maximo_bytes: int):
        self.app = app
        self.prefixo = prefixo
        self.maximo_bytes = maximo_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(self.prefixo):
            await self.app(scope, receive, send)
            return
        declarado = dict(scope["headers"]).get(b"content-length", b"")
        grande_demais = declarado.isdigit() and int(declarado) > self.maximo_bytes
        lidos = 0

        async def receber() -> Message:
            nonlocal lidos
            if grande_demais:
                raise HTTPException(status_code=413)
            mensagem = await receive()
            lidos += len(mensagem.get("body", b""))
            if lidos > self.maximo_bytes:
                raise HTTPException(status_code=413)
            return mensagem

        await self.app(scope, receber, send)
