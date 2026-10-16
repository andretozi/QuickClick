"""
Infraestrutura · Gateway da Amazon (A ser implementado).

Documentação técnica: Selling Partner API (SP-API) e Login with Amazon (LWA).
"""

from backend.application.portas import GatewayMarketplace


class GatewayAmazon(GatewayMarketplace):
    slug = "amazon"
