"""
Aplicação · IA · Portas

O que o orquestrador da análise precisa do mundo de fora. A infraestrutura implementa
(Pillow, Anthropic, Gemini, Mercado Livre, banco); os testes usam versões falsas, sem rede.

Contrato comum dos provedores de IA: `nome` (para logs e ia_uso), `disponivel()` (chave
presente e não recusada nos últimos 10 minutos) e FalhaDoProvedor em qualquer erro.
Cada adaptador registra o próprio uso (RegistroDeUso) e tenta de novo só em erro temporário.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

from backend.application.ia.modelos import (
    ArquivoDeFoto,
    CategoriaSugerida,
    ContextoDaChamada,
    EntradaDaLeitura,
    EntradaDaPesquisa,
    EntradaDaReleitura,
    EntradaDoPreco,
    EntradaDoTexto,
    Fidelidade,
    FotoPreparada,
    PrecoObservado,
    RespostaDaIA,
    UsoDeIA,
)
from backend.domain.canais.esquema import EsquemaDoCanal
from backend.domain.ia.atributos_ml import AtributoML


class ProvedorDeIA(Protocol):
    nome: str

    def disponivel(self) -> bool: ...


class PreparadorDeFotos(Protocol):
    def preparar(self, arquivos: list[ArquivoDeFoto], primeiro_indice: int = 0) -> list[FotoPreparada]:
        """Confere o conteúdo real (não só a extensão), limites, orientação, apaga metadados,
        mede a qualidade e gera as versões de leitura e de detalhe. FotoInvalida se não der."""
        ...

    def recortar(self, foto: FotoPreparada, caixa: tuple[int, int, int, int]) -> bytes:
        """Recorte da caixa (0 a 1000) na versão de detalhe, em JPEG."""
        ...

    def ampliar_para_publicacao(self, conteudo_jpeg: bytes) -> bytes:
        """Amplia e reforça a área útil da foto quando o marketplace recusa por excesso de bordas brancas."""
        ...


class TratadorDeFoto(Protocol):
    """Versão final: tratar a foto (fundo branco, luz, recorte) preservando o produto e os defeitos.
    No MVP (SemTratamento) devolve a mesma foto, sem custo."""

    def tratar(self, foto: FotoPreparada, contexto: ContextoDaChamada) -> FotoPreparada: ...


class GuardiaoDeFidelidade(Protocol):
    """Versão final: compara a original com a tratada. "grave" descarta a tratada, "leve" mantém com
    aviso. No MVP devolve "nao_verificada"."""

    def verificar(self, original: FotoPreparada, tratada: FotoPreparada,
                  contexto: ContextoDaChamada) -> Fidelidade: ...


class LeitorDeProduto(ProvedorDeIA, Protocol):
    def ler(self, entrada: EntradaDaLeitura, contexto: ContextoDaChamada) -> RespostaDaIA: ...

    def reler(self, entrada: EntradaDaReleitura, contexto: ContextoDaChamada) -> RespostaDaIA: ...


class PesquisadorDeMercado(ProvedorDeIA, Protocol):
    def pesquisar(self, entrada: EntradaDaPesquisa, contexto: ContextoDaChamada) -> RespostaDaIA: ...


class Precificador(ProvedorDeIA, Protocol):
    def precificar(self, entrada: EntradaDoPreco, contexto: ContextoDaChamada) -> RespostaDaIA: ...


class PesquisadorDePrecosNaWeb(ProvedorDeIA, Protocol):
    """Reserva do preço no pago: preços de itens parecidos nos marketplaces brasileiros, pela busca na web."""

    def buscar_precos(self, produto: str, condicao: str, atributos: tuple[tuple[str, str], ...],
                      contexto: ContextoDaChamada) -> RespostaDaIA: ...


class Redator(ProvedorDeIA, Protocol):
    def escrever(self, entrada: EntradaDoTexto, contexto: ContextoDaChamada) -> RespostaDaIA: ...

    def corrigir(self, texto: dict[str, Any], trechos: list[str], contexto: ContextoDaChamada) -> RespostaDaIA: ...


class LigadorDeAtributos(ProvedorDeIA, Protocol):
    """IA rápida: liga as sobras (que a regra não ligou) aos IDs de atributo do Mercado Livre."""

    def ligar(self, sobras: list[tuple[str, str]], da_categoria: list[AtributoML],
              contexto: ContextoDaChamada) -> RespostaDaIA: ...


class FontePrecosMarketplace(Protocol):
    """Dados reais do Mercado Livre, com o token do vendedor."""

    def descobrir_categoria(self, termos: list[str], access_token: str) -> CategoriaSugerida | None: ...

    def atributos_da_categoria(self, categoria_id: str, access_token: str) -> list[AtributoML]: ...

    def buscar_parecidos(self, termos: list[str], categoria_id: str | None, condicao: str,
                         access_token: str) -> list[PrecoObservado] | None:
        """None quando a busca não está liberada para o app (403) ou não respondeu."""
        ...

    def tarifa(self, preco_centavos: int, categoria_id: str, access_token: str) -> int | None:
        """Tarifa de venda do anúncio clássico, em centavos."""
        ...


class FonteDeEsquema(Protocol):
    """Campos que um canal pede para uma categoria, no modelo genérico."""

    def descobrir_categoria(self, termos: list[str], access_token: str) -> CategoriaSugerida | None: ...

    def esquema(self, categoria_id: str, access_token: str) -> EsquemaDoCanal: ...


class RegistroDeUso(Protocol):
    def registrar(self, uso: UsoDeIA) -> None: ...


class OrcamentoDeIA(Protocol):
    def gasto_de_hoje_usd(self, agora: datetime) -> Decimal: ...


class RepositorioDeAnalises(Protocol):
    def criar(self, dados: dict[str, Any]) -> None: ...

    def obter(self, analise_id: str) -> dict[str, Any] | None: ...

    def atualizar(self, analise_id: str, campos: dict[str, Any]) -> None: ...

    def prontas_no_mes(self, vendedor_id: int, agora: datetime) -> int: ...

    def em_andamento(self, vendedor_id: int) -> int: ...

    def criadas_desde(self, vendedor_id: int, desde: datetime) -> int: ...

    def marcar_paradas_como_interrompidas(self, agora: datetime) -> int: ...


class CacheDePesquisas(Protocol):
    def obter(self, chave: str, agora: datetime) -> dict[str, Any] | None: ...

    def salvar(self, chave: str, conteudo: dict[str, Any], fontes: list[str], agora: datetime,
               expira_em: datetime) -> None: ...


class CacheDeCategoriasML(Protocol):
    def obter(self, categoria_id: str, agora: datetime) -> list[dict[str, Any]] | None: ...

    def salvar(self, categoria_id: str, atributos: list[dict[str, Any]], expira_em: datetime) -> None: ...


class ContasDoVendedor(Protocol):
    """Marketplaces que o vendedor conectou (na ordem em que conectou) e o token do Mercado Livre em dia."""

    def conectados(self, vendedor_id: int) -> list[str]: ...

    def token_mercado_livre(self, vendedor_id: int) -> str | None: ...


class Executor(Protocol):
    """Roda a análise em segundo plano (ThreadPoolExecutor pequeno; nos testes, na hora)."""

    def submit(self, fn, /, *args, **kwargs): ...
