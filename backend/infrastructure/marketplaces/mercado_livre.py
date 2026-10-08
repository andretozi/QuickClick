"""
Infraestrutura · Gateway do Mercado Livre

HOJE: simulado (herda de GatewaySimulado), sem rede e sem credencial.

COMO SERÁ DE VERDADE (confira os detalhes na documentação oficial antes de implementar):
- API REST direta, com um cliente HTTP (httpx). Os SDKs oficiais do Mercado Livre foram
  arquivados em 2022 e não devem ser usados.
- gerar_url_autorizacao: o vendedor vai para
      https://auth.mercadolivre.com.br/authorization?response_type=code
          &client_id=<MERCADO_LIVRE_CLIENT_ID>&redirect_uri=<MERCADO_LIVRE_REDIRECT_URI>&state=<estado>
  e autoriza lá, com a conta e a senha dele.
- trocar_codigo_por_token: POST https://api.mercadolibre.com/oauth/token com
  grant_type=authorization_code, client_id, client_secret, code e redirect_uri.
- O access token vale 6 horas. renovar_token faz o mesmo POST com
  grant_type=refresh_token; cada renovação devolve um refresh token novo, que
  substitui o anterior no banco.
- Credenciais no .env (MERCADO_LIVRE_*), nunca no código.
"""

from datetime import timedelta

from backend.infrastructure.marketplaces.simulado import GatewaySimulado


class GatewayMercadoLivre(GatewaySimulado):
    slug = "mercado-livre"
    validade_do_token = timedelta(hours=6)
