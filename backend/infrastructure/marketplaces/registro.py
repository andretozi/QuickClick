"""Infraestrutura · Registro dos gateways: um para cada marketplace disponível no catálogo."""

from backend.application.portas import GatewayMarketplace
from backend.domain.marketplace import CATALOGO
from backend.infrastructure.marketplaces.amazon import GatewayAmazon
from backend.infrastructure.marketplaces.mercado_livre import GatewayMercadoLivre
from backend.infrastructure.marketplaces.shopee import GatewayShopee


def criar_gateways() -> dict[str, GatewayMarketplace]:
    gateways = {gateway.slug: gateway for gateway in (GatewayMercadoLivre(), GatewayShopee(), GatewayAmazon())}
    sem_gateway = [m.slug for m in CATALOGO if m.disponivel and m.slug not in gateways]
    if sem_gateway:
        raise RuntimeError(f"Marketplace disponível sem gateway: {', '.join(sem_gateway)}")
    return gateways
