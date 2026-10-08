"""
Apresentação · Rotas da API

Todas ficam debaixo de /api (o prefixo é aplicado em api.py). Cada rota só traduz
HTTP para um caso de uso e o resultado de volta para JSON: a regra mora no domínio.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.application.casos_de_uso import CasosDeUso
from backend.presentation.http.esquemas import (
    ListaDeMarketplaces,
    ListaDePlanos,
    MarketplaceSaida,
    RespostaDeErro,
    Saude,
    VendedorSaida,
    marketplace_saida,
    plano_saida,
    vendedor_saida,
)

ERRO_404 = {404: {"model": RespostaDeErro, "description": "Marketplace ou vendedor não encontrado"}}
ERROS_AO_CONECTAR = {
    **ERRO_404,
    403: {"model": RespostaDeErro, "description": "Limite de marketplaces do plano atingido"},
    409: {"model": RespostaDeErro, "description": "Marketplace ainda em breve"},
}


def criar_rotas(casos: CasosDeUso, identificar_vendedor: Callable[[], int]) -> APIRouter:
    rotas = APIRouter()
    VendedorAtual = Annotated[int, Depends(identificar_vendedor)]

    @rotas.get("/health", tags=["sistema"], summary="Confere se a API está no ar", response_model=Saude)
    def health() -> Saude:
        return Saude(status="ok")

    @rotas.get("/plans", tags=["planos"], summary="Planos de assinatura, do Grátis ao Business", response_model=ListaDePlanos)
    def listar_planos() -> ListaDePlanos:
        return ListaDePlanos(planos=[plano_saida(plano) for plano in casos.listar_planos.executar()])

    @rotas.get(
        "/me",
        tags=["vendedor"],
        summary="Vendedor atual (por enquanto, o de demonstração)",
        response_model=VendedorSaida,
        responses=ERRO_404,
    )
    def vendedor_atual(vendedor_id: VendedorAtual) -> VendedorSaida:
        return vendedor_saida(casos.obter_vendedor_atual.executar(vendedor_id))

    @rotas.get(
        "/marketplaces",
        tags=["marketplaces"],
        summary="Catálogo de marketplaces, com o que o vendedor já conectou",
        response_model=ListaDeMarketplaces,
    )
    def listar_marketplaces(vendedor_id: VendedorAtual) -> ListaDeMarketplaces:
        itens = casos.listar_marketplaces.executar(vendedor_id)
        return ListaDeMarketplaces(marketplaces=[marketplace_saida(item) for item in itens])

    @rotas.post(
        "/marketplaces/{slug}/connection",
        tags=["marketplaces"],
        summary="Conecta uma conta que o vendedor já tem no marketplace (OAuth simulado)",
        response_model=MarketplaceSaida,
        responses=ERROS_AO_CONECTAR,
    )
    def conectar(slug: str, vendedor_id: VendedorAtual) -> MarketplaceSaida:
        return marketplace_saida(casos.conectar_marketplace.executar(vendedor_id, slug))

    @rotas.delete(
        "/marketplaces/{slug}/connection",
        tags=["marketplaces"],
        summary="Desconecta o marketplace e libera a vaga do plano",
        response_model=MarketplaceSaida,
        responses=ERRO_404,
    )
    def desconectar(slug: str, vendedor_id: VendedorAtual) -> MarketplaceSaida:
        return marketplace_saida(casos.desconectar_marketplace.executar(vendedor_id, slug))

    return rotas
