"""
Infraestrutura · Gateway da Shopee (A ser implementado).

Documentação técnica: Shopee Open Platform API v2.
"""

from backend.application.portas import GatewayMarketplace


class GatewayShopee(GatewayMarketplace):
    slug = "shopee"
