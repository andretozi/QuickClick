"""
Apresentação · Formatos das respostas da API

Modelos pydantic usados só na fronteira HTTP: validam a saída e documentam a API em /docs.
As funções de conversão traduzem os resultados dos casos de uso para JSON.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from backend.application.casos_de_uso.comum import MarketplaceDoVendedor
from backend.application.casos_de_uso.obter_vendedor_atual import ResumoDoVendedor
from backend.domain.marketplace import StatusMarketplace
from backend.domain.plano import Plano


class Saude(BaseModel):
    status: str = Field(examples=["ok"])


class PlanoSaida(BaseModel):
    slug: str = Field(examples=["gratis"])
    nome: str = Field(examples=["Grátis"])
    preco_mensal_centavos: int | None = Field(description="null enquanto o preço não foi definido")
    limite_marketplaces: int | None = Field(description="null quando o plano conecta vários marketplaces")
    multicanal: bool


class ListaDePlanos(BaseModel):
    planos: list[PlanoSaida]


class VendedorSaida(BaseModel):
    id: int
    nome: str
    plano: PlanoSaida
    marketplaces_conectados: int
    pode_conectar_mais: bool
    plano_para_mais_marketplaces: PlanoSaida | None = Field(
        description="Plano que conecta mais marketplaces (null no Pro e no Business)"
    )


class MarketplaceSaida(BaseModel):
    slug: str = Field(examples=["mercado-livre"])
    nome: str = Field(examples=["Mercado Livre"])
    status: StatusMarketplace
    conectado: bool
    conectado_em: datetime | None


class ListaDeMarketplaces(BaseModel):
    marketplaces: list[MarketplaceSaida]


class DetalheDoErro(BaseModel):
    codigo: str = Field(examples=["limite_do_plano"])
    mensagem: str = Field(description="Texto amigável, pronto para aparecer na tela")
    plano_sugerido: str | None = Field(default=None, description="Slug do plano que resolve o limite")


class RespostaDeErro(BaseModel):
    erro: DetalheDoErro


def plano_saida(plano: Plano) -> PlanoSaida:
    return PlanoSaida(
        slug=plano.slug,
        nome=plano.nome,
        preco_mensal_centavos=plano.preco_mensal_centavos,
        limite_marketplaces=plano.limite_marketplaces,
        multicanal=plano.multicanal,
    )


def vendedor_saida(resumo: ResumoDoVendedor) -> VendedorSaida:
    sugerido = resumo.plano_para_mais_marketplaces
    return VendedorSaida(
        id=resumo.vendedor.id,
        nome=resumo.vendedor.nome,
        plano=plano_saida(resumo.vendedor.plano),
        marketplaces_conectados=resumo.marketplaces_conectados,
        pode_conectar_mais=resumo.pode_conectar_mais,
        plano_para_mais_marketplaces=None if sugerido is None else plano_saida(sugerido),
    )


def marketplace_saida(item: MarketplaceDoVendedor) -> MarketplaceSaida:
    return MarketplaceSaida(
        slug=item.marketplace.slug,
        nome=item.marketplace.nome,
        status=item.marketplace.status,
        conectado=item.conectado,
        conectado_em=None if item.conta is None else item.conta.conectada_em,
    )
