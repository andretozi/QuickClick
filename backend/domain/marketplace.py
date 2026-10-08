"""
Domínio · Marketplaces

O catálogo oficial: onde o vendedor pode conectar uma conta que já tem.
A lista da landing (frontend/src/domain/content/marketplacesContent.js) acompanha
este catálogo: mudou aqui, mude lá também.
"""

from dataclasses import dataclass
from enum import StrEnum

from backend.domain.erros import MarketplaceEmBreve, MarketplaceNaoEncontrado


class StatusMarketplace(StrEnum):
    DISPONIVEL = "disponivel"  # integração oficial do projeto
    EM_BREVE = "em_breve"


@dataclass(frozen=True)
class Marketplace:
    slug: str
    nome: str
    status: StatusMarketplace

    @property
    def disponivel(self) -> bool:
        return self.status is StatusMarketplace.DISPONIVEL


CATALOGO: tuple[Marketplace, ...] = (
    Marketplace("mercado-livre", "Mercado Livre", StatusMarketplace.DISPONIVEL),
    Marketplace("shopee", "Shopee", StatusMarketplace.DISPONIVEL),
    Marketplace("amazon", "Amazon", StatusMarketplace.DISPONIVEL),
    Marketplace("magalu", "Magalu", StatusMarketplace.EM_BREVE),
    Marketplace("americanas", "Americanas", StatusMarketplace.EM_BREVE),
    Marketplace("casas-bahia", "Casas Bahia", StatusMarketplace.EM_BREVE),
    Marketplace("shein", "Shein", StatusMarketplace.EM_BREVE),
    Marketplace("tiktok-shop", "TikTok Shop", StatusMarketplace.EM_BREVE),
    Marketplace("aliexpress", "AliExpress", StatusMarketplace.EM_BREVE),
)


def obter_marketplace(slug: str) -> Marketplace:
    """O marketplace do catálogo com esse slug, disponível ou não."""
    for marketplace in CATALOGO:
        if marketplace.slug == slug:
            return marketplace
    raise MarketplaceNaoEncontrado(slug)


def obter_marketplace_disponivel(slug: str) -> Marketplace:
    """O marketplace pronto para conectar, ou um erro explicando por que ainda não dá."""
    marketplace = obter_marketplace(slug)
    if not marketplace.disponivel:
        raise MarketplaceEmBreve(marketplace.nome, [m.nome for m in CATALOGO if m.disponivel])
    return marketplace
