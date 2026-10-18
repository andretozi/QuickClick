"""
Apresentação · Quem está pedindo: o vendedor do token JWT (Authorization: Bearer <token>).

`identificar_vendedor` é um fallback opcional para testes ou modo sem token.
"""

from collections.abc import Callable

from fastapi import Request

from backend.application.portas import ServicoToken
from backend.domain.erros import NaoAutenticado


def dependencia_do_vendedor(servico_token: ServicoToken | None,
                            identificar_vendedor: Callable[..., int] | None = None) -> Callable[[Request], int]:
    def obter_vendedor_autenticado(request: Request) -> int:
        header = request.headers.get("Authorization")
        if header and header.startswith("Bearer "):
            token = header.split(" ", 1)[1].strip()
            if servico_token is not None:
                payload = servico_token.validar_token(token)
                return int(payload["sub"])
        if identificar_vendedor is not None:
            return identificar_vendedor()
        raise NaoAutenticado("Autenticação obrigatória. Envie o cabeçalho Authorization: Bearer <token>.")

    return obter_vendedor_autenticado
