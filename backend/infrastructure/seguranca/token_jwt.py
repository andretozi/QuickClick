"""
Infraestrutura · Serviço de Tokens JWT (JSON Web Tokens).

Utiliza algoritmo HS256 para assinatura simétrica de tokens de autenticação.
O segredo vem da configuração (QUICKCLICK_JWT_SECRET) e nunca do código.

Cada token carrega a sua finalidade ("fin"): o de acesso serve para entrar na API;
o de estado do OAuth só volta do marketplace no callback, vale 15 minutos e não
serve como login (ele passa pela URL do marketplace).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from backend.domain.erros import TokenInvalido

FINALIDADE_ACESSO = "acesso"
FINALIDADE_ESTADO_OAUTH = "estado_oauth"
DURACAO_PADRAO = timedelta(days=7)
DURACAO_ESTADO_OAUTH = timedelta(minutes=15)


class ServicoJWT:
    def __init__(self, segredo: str, duracao: timedelta = DURACAO_PADRAO):
        if not segredo:
            raise ValueError("O serviço de tokens precisa de um segredo (QUICKCLICK_JWT_SECRET).")
        self._segredo = segredo
        self._duracao = duracao

    def gerar_token(self, user_id: int, email: str, finalidade: str = FINALIDADE_ACESSO) -> str:
        agora = datetime.now(UTC)
        duracao = self._duracao if finalidade == FINALIDADE_ACESSO else DURACAO_ESTADO_OAUTH
        payload = {
            "sub": str(user_id),
            "email": email.strip().lower(),
            "fin": finalidade,
            "iat": agora,
            "exp": agora + duracao,
        }
        return jwt.encode(payload, self._segredo, algorithm="HS256")

    def validar_token(self, token: str, finalidade: str = FINALIDADE_ACESSO) -> dict[str, Any]:
        if not token:
            raise TokenInvalido("Token de autenticação não fornecido.")
        try:
            payload = jwt.decode(token, self._segredo, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as erro:
            raise TokenInvalido("Token expirado. Faça login novamente.") from erro
        except jwt.InvalidTokenError as erro:
            raise TokenInvalido("Token inválido.") from erro

        # Tokens antigos não têm "fin": eram de acesso, menos o estado do OAuth ("oauth:<slug>")
        antigo_de_oauth = "fin" not in payload and str(payload.get("email", "")).startswith("oauth:")
        recebida = FINALIDADE_ESTADO_OAUTH if antigo_de_oauth else payload.get("fin", FINALIDADE_ACESSO)
        if recebida != finalidade:
            raise TokenInvalido("Token inválido.")
        return payload
