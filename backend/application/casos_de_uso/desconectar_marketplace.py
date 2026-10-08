"""
Aplicação · Desconectar marketplace

Desliga a conta do marketplace e libera a vaga do plano. Com a integração real,
aqui também se revoga o acesso no marketplace, quando a API dele permitir.
"""

from backend.application.casos_de_uso.comum import MarketplaceDoVendedor
from backend.application.portas import RepositorioContasVinculadas
from backend.domain.marketplace import obter_marketplace


class DesconectarMarketplace:
    def __init__(self, contas: RepositorioContasVinculadas):
        self._contas = contas

    def executar(self, vendedor_id: int, slug: str) -> MarketplaceDoVendedor:
        marketplace = obter_marketplace(slug)
        self._contas.remover(vendedor_id, slug)  # se não estava conectado, não muda nada
        return MarketplaceDoVendedor(marketplace, None)
