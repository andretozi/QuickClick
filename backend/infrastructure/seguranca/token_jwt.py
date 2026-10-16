"""
Infraestrutura · Serviço de Tokens JWT (JSON Web Tokens).

Utiliza algoritmo HS256 para assinatura simétrica de tokens de autenticação.
Controla emissão, expiração e validação com tratamento rigoroso de segurança.
"""

import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from backend.domain.erros import TokenInvalido

SEGREDO_PADRAO = "quickclick-default-jwt-secret-key-change-in-production-2026"
DURACAO_PADRAO = timedelta(days=7)


class ServicoJWT:
    def __init__(self, segredo: str | None = None, duracao: timedelta = DURACAO_PADRAO):
        self._segredo = segredo or os.getenv("JWT_SECRET") or SEGREDO_PADRAO
        self._duracao = duracao

    def gerar_token(self, user_id: int, email: str) -> str:
        agora = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "email": email.strip().lower(),
            "iat": agora,
            "exp": agora + self._duracao,
        }
        return jwt.encode(payload, self._segredo, algorithm="HS256")

    def validar_token(self, token: str) -> dict[str, Any]:
        if not token:
            raise TokenInvalido("Token de autenticação não fornecido.")
        try:
            return jwt.decode(token, self._segredo, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as erro:
            raise TokenInvalido("Token expirado. Faça login novamente.") from erro
        except jwt.InvalidTokenError as erro:
            raise TokenInvalido("Token inválido.") from erro
