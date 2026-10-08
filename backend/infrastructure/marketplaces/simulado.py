"""
Infraestrutura · Gateway OAuth 2.0 simulado

Faz o papel do marketplace sem acessar a rede e sem segredo nenhum: monta uma URL de
autorização de mentira e devolve tokens falsos, com a mesma validade dos tokens reais.
Cada marketplace herda daqui e documenta como será a integração de verdade.
"""

import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from backend.domain.conta_vinculada import CredenciaisOAuth


def _agora_utc() -> datetime:
    return datetime.now(UTC)


class GatewaySimulado:
    slug = "simulado"
    validade_do_token = timedelta(hours=1)

    def __init__(self, agora: Callable[[], datetime] = _agora_utc):
        self._agora = agora

    def gerar_url_autorizacao(self, estado: str) -> str:
        consulta = urlencode({"response_type": "code", "state": estado})
        return f"https://simulado.quickclick.local/{self.slug}/autorizar?{consulta}"

    def trocar_codigo_por_token(self, codigo: str) -> CredenciaisOAuth:
        if not codigo:
            raise ValueError("Código de autorização vazio.")
        return self._novas_credenciais()

    def renovar_token(self, refresh_token: str) -> CredenciaisOAuth:
        if not refresh_token:
            raise ValueError("Refresh token vazio.")
        return self._novas_credenciais()

    def _novas_credenciais(self) -> CredenciaisOAuth:
        return CredenciaisOAuth(
            access_token=f"simulado_{secrets.token_hex(16)}",
            refresh_token=f"simulado_{secrets.token_hex(16)}",
            expira_em=self._agora() + self.validade_do_token,
        )
