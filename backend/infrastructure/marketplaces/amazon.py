"""
Infraestrutura · Gateway da Amazon

HOJE: simulado (herda de GatewaySimulado), sem rede e sem credencial.

COMO SERÁ DE VERDADE pela Selling Partner API (confira os detalhes na documentação
oficial antes de implementar):
- A autorização é feita pelo Seller Central e os tokens vêm do Login with Amazon (LWA).
  O app registrado tem um application_id e as credenciais LWA, client_id e
  client_secret (AMAZON_* no .env).
- gerar_url_autorizacao: o vendedor vai para a tela de consentimento do Seller Central,
      https://sellercentral.amazon.com.br/apps/authorize/consent?application_id=<id>&state=<estado>
  e a Amazon devolve o vendedor com spapi_oauth_code, state e selling_partner_id.
- trocar_codigo_por_token: POST https://api.amazon.com/auth/o2/token (Login with Amazon)
  com grant_type=authorization_code, code, client_id e client_secret.
- O access token vale 1 hora. renovar_token faz o mesmo POST com grant_type=refresh_token.
- As chamadas da Selling Partner API levam o access token no cabeçalho x-amz-access-token.
"""

from datetime import timedelta

from backend.infrastructure.marketplaces.simulado import GatewaySimulado


class GatewayAmazon(GatewaySimulado):
    slug = "amazon"
    validade_do_token = timedelta(hours=1)
