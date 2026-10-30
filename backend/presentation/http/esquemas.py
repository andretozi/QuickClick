"""
Apresentação · Formatos das respostas e entradas da API

Modelos pydantic usados só na fronteira HTTP: validam a entrada e a saída.
As funções de conversão traduzem os resultados dos casos de uso para JSON.
"""

from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator

from backend.application.casos_de_uso.comum import MarketplaceDoVendedor
from backend.application.casos_de_uso.obter_vendedor_atual import ResumoDoVendedor
from backend.domain.marketplace import CATALOGO, StatusMarketplace
from backend.domain.plano import Plano
from backend.domain.produto import Produto, Publicacao
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


PADRAO_ID_PRODUTO = r"^[A-Za-z0-9_-]{1,40}$"
MAX_CENTAVOS = 1_000_000_000
UrlDaFoto = Annotated[str, Field(max_length=1000, pattern=r"^https://")]  # data: e http: são recusados
Permalink = Annotated[str, Field(max_length=500, pattern=r"^https://")]
TextoDoAtributo = Annotated[str, Field(max_length=1000)]
NumeroFinito = Annotated[float, Field(allow_inf_nan=False)]


class AtributoDoProduto(BaseModel):
    id: str | None = Field(default=None, max_length=60)
    nome: str = Field(default="", max_length=200)
    valor: TextoDoAtributo | int | NumeroFinito | bool | None = None


class PublicacaoDoProduto(BaseModel):
    canal: str = Field(max_length=40, examples=["mercado-livre"])
    status: Literal["publicado", "pausado", "nao_publicado"]
    id_externo: str | None = Field(default=None, max_length=60, examples=["MLB1234567890"])
    permalink: Permalink | None = None
    categoria_id: str | None = Field(default=None, max_length=40)
    saude: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    vendidos: int = Field(default=0, ge=0, le=10_000_000)

    @field_validator("canal")
    @classmethod
    def _canal_do_catalogo(cls, canal: str) -> str:
        if canal not in {marketplace.slug for marketplace in CATALOGO}:
            raise ValueError("canal fora do catálogo")
        return canal


class ProdutoApi(BaseModel):
    """Um anúncio no banco, igual na entrada e na saída. O vendedor vem do token: campo extra no corpo é ignorado."""

    id: str = Field(pattern=PADRAO_ID_PRODUTO, examples=["a_k3j9x0q2mz"])
    titulo: str = Field(max_length=300)
    descricao: str = Field(default="", max_length=50_000)
    categoria: str = Field(max_length=40)
    condicao: Literal["novo", "usado"]
    preco_centavos: int = Field(ge=0, le=MAX_CENTAVOS)
    preco_sugerido_centavos: int | None = Field(default=None, ge=0, le=MAX_CENTAVOS)
    estoque: int = Field(ge=0, le=1_000_000)
    fotos: list[UrlDaFoto] = Field(default_factory=list, max_length=12)
    capa: int = Field(default=0, ge=0, le=11)
    atributos: list[AtributoDoProduto] = Field(default_factory=list, max_length=200)
    analise_id: str | None = Field(default=None, max_length=36)
    criado_em: datetime
    atualizado_em: datetime = Field(description="Versão lida; no PUT, 409 se o servidor tiver uma mais nova")
    publicacoes: list[PublicacaoDoProduto] = Field(default_factory=list, max_length=len(CATALOGO))

    @field_validator("publicacoes")
    @classmethod
    def _um_por_canal(cls, publicacoes: list[PublicacaoDoProduto]) -> list[PublicacaoDoProduto]:
        if len({p.canal for p in publicacoes}) != len(publicacoes):
            raise ValueError("canal repetido")
        return publicacoes


class ListaDeProdutos(BaseModel):
    produtos: list[ProdutoApi]


class ResultadoDaImportacao(BaseModel):
    importado: bool = Field(description="false: o produto ou o item do canal já existia")


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


def produto_do_corpo(corpo: ProdutoApi, produto_id: str) -> Produto:
    dados = corpo.model_dump(exclude={"id", "publicacoes"})
    return Produto(id=produto_id, **dados, publicacoes=[Publicacao(**p.model_dump()) for p in corpo.publicacoes])


def produto_saida(produto: Produto) -> ProdutoApi:
    return ProdutoApi.model_validate(asdict(produto))
