"""Aplicação · Catálogo inteiro de marketplaces, marcando o que o vendedor já conectou."""

from backend.application.casos_de_uso.comum import MarketplaceDoVendedor
from backend.application.portas import RepositorioContasVinculadas
from backend.domain.marketplace import CATALOGO


class ListarMarketplaces:
    def __init__(self, contas: RepositorioContasVinculadas):
        self._contas = contas

    def executar(self, vendedor_id: int) -> list[MarketplaceDoVendedor]:
        contas = {conta.marketplace: conta for conta in self._contas.listar_do_vendedor(vendedor_id)}
        return [MarketplaceDoVendedor(marketplace, contas.get(marketplace.slug)) for marketplace in CATALOGO]
