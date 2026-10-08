"""
Infraestrutura · Gateway da Shopee

HOJE: simulado (herda de GatewaySimulado), sem rede e sem credencial.

COMO SERÁ DE VERDADE pela Shopee Open Platform, API v2 (confira os detalhes na
documentação oficial antes de implementar):
- O app é cadastrado na Shopee Open Platform, que fornece partner_id e partner_key
  (SHOPEE_PARTNER_ID e SHOPEE_PARTNER_KEY no .env).
- Toda chamada é assinada: sign é um HMAC SHA256 feito com a partner_key sobre
  partner_id, caminho da API e timestamp (nas chamadas da loja, também access_token e shop_id).
- gerar_url_autorizacao: o vendedor vai para /api/v2/shop/auth_partner, com partner_id,
  timestamp, sign e o endereço de retorno, e autoriza a loja lá.
- trocar_codigo_por_token: POST /api/v2/auth/token/get com o code e o shop_id que
  voltam no retorno.
- renovar_token: POST /api/v2/auth/access_token/get com o refresh_token.
  O access token vale 4 horas e o refresh token, 30 dias.
"""

from datetime import timedelta

from backend.infrastructure.marketplaces.simulado import GatewaySimulado


class GatewayShopee(GatewaySimulado):
    slug = "shopee"
    validade_do_token = timedelta(hours=4)
