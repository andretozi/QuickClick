"""
Apresentação · Formatos das respostas e entradas da API

Modelos pydantic usados só na fronteira HTTP: validam a entrada e a saída.
As funções de conversão traduzem os resultados dos casos de uso para JSON.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.application.casos_de_uso.comum import MarketplaceDoVendedor
from backend.application.casos_de_uso.obter_vendedor_atual import ResumoDoVendedor
from backend.domain.marketplace import StatusMarketplace
from backend.domain.plano import Plano
from backend.domain.usuario import Usuario


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
    troca_de_plano_livre: bool = Field(default=True, description="false: a troca de plano espera o pagamento "
                                       "(PUT /api/me/plano responde 402)")


class RequisicaoTrocarPlano(BaseModel):
    plano: str = Field(max_length=40, examples=["pro"], description="gratis, essencial, pro ou business")


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


class UrlAutorizacaoSaida(BaseModel):
    url: str = Field(description="URL de autorização OAuth no marketplace")


class RequisicaoConectar(BaseModel):
    codigo_autorizacao: str | None = Field(default=None, max_length=512, description="Código retornado pelo fluxo OAuth oficial")


class UsuarioSaida(BaseModel):
    id: int
    email: str
    nome: str
    loja: str
    plano: str


class RespostaAutenticacao(BaseModel):
    token: str = Field(description="Token de autenticação JWT Bearer")
    usuario: UsuarioSaida


class RequisicaoCadastro(BaseModel):
    email: str = Field(max_length=254, examples=["vendedor@quickclick.com.br"])
    senha: str = Field(min_length=6, max_length=256, description="Senha com no mínimo 6 caracteres")
    nome: str = Field(default="", max_length=120, examples=["André Tozi"])
    loja: str = Field(default="", max_length=120, examples=["Minha Loja Oficial"])
    maior_de_idade: bool = Field(default=False, description="Confirma que tem 18 anos ou mais (obrigatório)")


class RequisicaoLogin(BaseModel):
    email: str = Field(max_length=254, examples=["vendedor@quickclick.com.br"])
    senha: str = Field(max_length=256, description="Senha do usuário")


class AtributoEntrada(BaseModel):
    chave: str = Field(default="", max_length=80)
    valor: str = Field(default="", max_length=300)


class CampoProprioEntrada(BaseModel):
    canal: str = Field(default="", max_length=40)
    id: str = Field(default="", max_length=80)
    valor: str = Field(default="", max_length=300)


class RequisicaoConfirmacaoIA(BaseModel):
    produto: str = Field(default="", max_length=200)
    categoria: str = Field(default="outros", max_length=60)
    condicao: str = Field(default="desconhecido", max_length=40)
    atributos: list[AtributoEntrada] = Field(default_factory=list, max_length=60)
    defeitos: list[str] = Field(default_factory=list, max_length=20)
    campos_proprios: list[CampoProprioEntrada] = Field(default_factory=list, max_length=60)


class RequisicaoPublicarAnuncio(BaseModel):
    titulo: str = Field(default="", max_length=200)
    descricao: str = Field(default="", max_length=60_000)
    preco_centavos: Any = Field(default=None)
    estoque: Any = Field(default=1)
    condicao: str = Field(default="novo", max_length=40)
    atributos: list[AtributoEntrada] = Field(default_factory=list, max_length=60)
    analise_id: str | None = Field(default=None, max_length=80)
    ml_categoria_id: str | None = Field(default=None, max_length=40)
    fotos_mantidas: list[str] = Field(default_factory=list, max_length=6)


class RequisicaoStatusAnuncio(BaseModel):
    status: str = Field(max_length=20, examples=["pausado", "publicado"])


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


def usuario_saida(usuario: Usuario) -> UsuarioSaida:
    return UsuarioSaida(
        id=usuario.id,
        email=usuario.email,
        nome=usuario.nome,
        loja=usuario.loja,
        plano=usuario.plano,
    )
