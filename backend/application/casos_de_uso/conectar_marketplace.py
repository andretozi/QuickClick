"""
Aplicação · Conectar marketplace

O vendedor liga à Quick Click uma conta que já tem num marketplace. Ele autoriza
direto no marketplace (OAuth 2.0) e a gente nunca vê a senha.

Nesta versão a autorização é SIMULADA: não há credenciais reais e o "marketplace"
aprova na hora. Com credenciais reais, o fluxo vira duas etapas:
    1. POST /api/marketplaces/{slug}/connection valida as regras abaixo e devolve a
       URL de autorização (gateway.gerar_url_autorizacao); o front leva o vendedor até ela.
    2. O marketplace devolve o vendedor para GET /api/marketplaces/{slug}/callback com
       o código, que é trocado pelos tokens (gateway.trocar_codigo_por_token).
"""

import secrets
from collections.abc import Callable, Mapping
from datetime import datetime

from backend.application.casos_de_uso.comum import MarketplaceDoVendedor, agora_utc, obter_vendedor
from backend.application.portas import GatewayMarketplace, RepositorioContasVinculadas, RepositorioVendedores
from backend.domain.conta_vinculada import ContaVinculada
from backend.domain.marketplace import obter_marketplace_disponivel

# Na simulação, o código que o marketplace devolveria depois de o vendedor aprovar
CODIGO_DE_AUTORIZACAO_SIMULADO = "codigo_simulado"


class ConectarMarketplace:
    def __init__(
        self,
        vendedores: RepositorioVendedores,
        contas: RepositorioContasVinculadas,
        gateways: Mapping[str, GatewayMarketplace],
        agora: Callable[[], datetime] = agora_utc,
    ):
        self._vendedores = vendedores
        self._contas = contas
        self._gateways = gateways
        self._agora = agora

    def executar(self, vendedor_id: int, slug: str) -> MarketplaceDoVendedor:
        marketplace = obter_marketplace_disponivel(slug)  # existe e não está "em breve"
        vendedor = obter_vendedor(self._vendedores, vendedor_id)

        existente = self._contas.buscar(vendedor_id, slug)
        if existente is not None:  # já conectado: nada muda e não ocupa outra vaga
            return MarketplaceDoVendedor(marketplace, existente)

        conectados = len(self._contas.listar_do_vendedor(vendedor_id))
        vendedor.plano.garantir_vaga(conectados)  # regra do limite de marketplaces do plano

        gateway = self._gateways[slug]
        estado = secrets.token_urlsafe(16)
        gateway.gerar_url_autorizacao(estado)  # de verdade: o vendedor abre esta URL e aprova
        credenciais = gateway.trocar_codigo_por_token(CODIGO_DE_AUTORIZACAO_SIMULADO)  # de verdade: vem do callback

        conta = ContaVinculada(vendedor_id, slug, self._agora(), credenciais)
        self._contas.salvar(conta)
        return MarketplaceDoVendedor(marketplace, conta)
