"""Aplicação · IA · Contas de marketplace do vendedor, pelos casos de uso que já existem."""

import logging

from backend.application.casos_de_uso.conectar_marketplace import ConectarMarketplace
from backend.application.portas import RepositorioContasVinculadas
from backend.domain.erros import ServicoIndisponivel

log = logging.getLogger("quickclick.ia")

MERCADO_LIVRE = "mercado-livre"


class ContasPelosCasosDeUso:
    def __init__(self, contas: RepositorioContasVinculadas, conectar: ConectarMarketplace):
        self._contas = contas
        self._conectar = conectar

    def conectados(self, vendedor_id: int) -> list[str]:
        try:
            return [conta.marketplace for conta in self._contas.listar_do_vendedor(vendedor_id)]
        except ServicoIndisponivel:  # sem a chave de criptografia, a análise segue sem os marketplaces
            return []

    def token_mercado_livre(self, vendedor_id: int) -> str | None:
        return self.token(vendedor_id, MERCADO_LIVRE)

    def token(self, vendedor_id: int, canal: str) -> str | None:
        try:
            return self._conectar.token_ativo(vendedor_id, canal)
        except ServicoIndisponivel:
            return None
