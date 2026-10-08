"""Aplicação · Peças usadas por mais de um caso de uso."""

from dataclasses import dataclass
from datetime import UTC, datetime

from backend.application.portas import RepositorioVendedores
from backend.domain.conta_vinculada import ContaVinculada
from backend.domain.erros import VendedorNaoEncontrado
from backend.domain.marketplace import Marketplace
from backend.domain.vendedor import Vendedor


@dataclass(frozen=True)
class MarketplaceDoVendedor:
    """Um marketplace do catálogo visto por um vendedor: conectado ou não."""

    marketplace: Marketplace
    conta: ContaVinculada | None

    @property
    def conectado(self) -> bool:
        return self.conta is not None


def agora_utc() -> datetime:
    return datetime.now(UTC)


def obter_vendedor(vendedores: RepositorioVendedores, vendedor_id: int) -> Vendedor:
    vendedor = vendedores.obter(vendedor_id)
    if vendedor is None:
        raise VendedorNaoEncontrado(vendedor_id)
    return vendedor
