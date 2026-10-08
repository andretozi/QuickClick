"""
Domínio · Conta vinculada

A conta que o vendedor já tem num marketplace, ligada à Quick Click por OAuth 2.0.
O vendedor autoriza direto no marketplace: a gente guarda só os tokens de acesso,
nunca a senha.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CredenciaisOAuth:
    access_token: str = field(repr=False)  # repr=False: token nunca aparece em log
    refresh_token: str = field(repr=False)
    expira_em: datetime

    def expirada(self, agora: datetime) -> bool:
        return agora >= self.expira_em


@dataclass(frozen=True)
class ContaVinculada:
    vendedor_id: int
    marketplace: str  # slug do catálogo
    conectada_em: datetime
    credenciais: CredenciaisOAuth
