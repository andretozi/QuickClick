"""
Aplicação · Conectar e operar marketplace

O vendedor liga à Quick Click uma conta que já tem num marketplace através de OAuth 2.0.
A autorização é feita diretamente no marketplace e os tokens de acesso são trocados
pelo código oficial de autorização. A mesma instância gerencia a geração da URL OAuth,
a vinculação da conta, a renovação automática de token e a listagem/publicação de anúncios.
"""

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from backend.application.casos_de_uso.comum import MarketplaceDoVendedor, agora_utc, obter_vendedor
from backend.application.portas import GatewayMarketplace, RepositorioContasVinculadas, RepositorioVendedores
from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.domain.erros import MarketplaceNaoEncontrado
from backend.domain.marketplace import Marketplace, obter_marketplace_disponivel


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

    def _validar_conexao(self, vendedor_id: int, slug: str) -> tuple[Marketplace, ContaVinculada | None]:
        marketplace = obter_marketplace_disponivel(slug)
        vendedor = obter_vendedor(self._vendedores, vendedor_id)

        existente = self._contas.buscar(vendedor_id, slug)
        if existente is None:
            conectados = len(self._contas.listar_do_vendedor(vendedor_id))
            vendedor.plano.garantir_vaga(conectados)

        return marketplace, existente

    def _obter_conta_e_gateway_ativo(self, vendedor_id: int, slug: str) -> tuple[CredenciaisOAuth, GatewayMarketplace]:
        conta = self._contas.buscar(vendedor_id, slug)
        if conta is None:
            raise MarketplaceNaoEncontrado(f"Conta do marketplace '{slug}' não está conectada.")

        gateway = self._gateways.get(slug)
        if gateway is None:
            raise MarketplaceNaoEncontrado(f"Gateway para marketplace '{slug}' não disponível.")

        credenciais = conta.credenciais
        if credenciais.expirada(self._agora()):
            credenciais = gateway.renovar_token(credenciais.refresh_token)
            self._contas.salvar(
                ContaVinculada(
                    vendedor_id=vendedor_id,
                    marketplace=slug,
                    conectada_em=conta.conectada_em,
                    credenciais=credenciais,
                )
            )

        return credenciais, gateway

    def gerar_url_autorizacao(self, vendedor_id: int, slug: str, estado: str) -> str:
        self._validar_conexao(vendedor_id, slug)
        gateway = self._gateways[slug]
        return gateway.gerar_url_autorizacao(estado)

    def executar(self, vendedor_id: int, slug: str, codigo_autorizacao: str = "") -> MarketplaceDoVendedor:
        marketplace, existente = self._validar_conexao(vendedor_id, slug)
        if existente is not None:
            return MarketplaceDoVendedor(marketplace, existente)

        if not codigo_autorizacao:
            raise ValueError(f"Código de autorização OAuth obrigatório para conectar o marketplace '{slug}'.")

        gateway = self._gateways[slug]
        credenciais = gateway.trocar_codigo_por_token(codigo_autorizacao)

        conta = ContaVinculada(vendedor_id, slug, self._agora(), credenciais)
        self._contas.salvar(conta)
        return MarketplaceDoVendedor(marketplace, conta)

    def listar_produtos(self, vendedor_id: int, slug: str) -> list[dict[str, Any]]:
        credenciais, gateway = self._obter_conta_e_gateway_ativo(vendedor_id, slug)
        return gateway.listar_anuncios(credenciais.access_token, credenciais.conta_externa_id)

    def publicar_produto(self, vendedor_id: int, slug: str, dados_produto: dict[str, Any]) -> dict[str, Any]:
        credenciais, gateway = self._obter_conta_e_gateway_ativo(vendedor_id, slug)
        return gateway.publicar_anuncio(credenciais.access_token, dados_produto)
