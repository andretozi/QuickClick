"""
Aplicação · IA · O que entra e sai das portas

Fotos só existem em memória (FotoPreparada); nada aqui vai para o banco além do uso e dos
resultados em JSON.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from backend.domain.ia.fotos import MedidaDaFoto, QualidadeFoto


@dataclass(frozen=True)
class ArquivoDeFoto:
    """Uma foto como chegou na requisição (só em memória)."""

    nome: str
    conteudo: bytes = field(repr=False)
    tipo_declarado: str = ""


@dataclass(frozen=True)
class FotoPreparada:
    """Foto conferida, girada, sem metadados (EXIF e localização) e em RGB."""

    indice: int
    leitura_jpeg: bytes = field(repr=False)  # lado maior 1568, JPEG 90: o que vai para a IA
    detalhe_jpeg: bytes = field(repr=False)  # lado maior até 2576: só para recortar a etiqueta
    largura: int = 0  # da foto recebida, depois de girar
    altura: int = 0
    medida: MedidaDaFoto | None = None

    @property
    def qualidade(self) -> QualidadeFoto:
        return self.medida.qualidade if self.medida else QualidadeFoto.OK

    def meta(self) -> dict[str, Any]:
        """O que pode ir para o banco: só qualidade, largura e altura (nunca a imagem)."""
        return {"indice": self.indice, "qualidade": self.qualidade.value, "largura": self.largura,
                "altura": self.altura}


class Fidelidade(StrEnum):
    NAO_VERIFICADA = "nao_verificada"  # MVP: sem tratamento, nada a verificar
    FIEL = "fiel"
    LEVE = "leve"  # mantém a tratada com aviso
    GRAVE = "grave"  # descarta a tratada


@dataclass(frozen=True)
class ContextoDaChamada:
    """Quem pediu e em que etapa: vai para o registro de uso (ia_uso)."""

    vendedor_id: int | None
    analise_id: str | None
    etapa: str


@dataclass(frozen=True)
class UsoDeIA:
    vendedor_id: int | None
    analise_id: str | None
    etapa: str
    provedor: str
    modelo: str
    versao_prompt: str | None
    tokens_entrada: int
    tokens_saida: int
    cache_lido: int
    cache_gravado: int
    buscas_web: int
    custo_estimado_usd: Decimal
    duracao_ms: int
    criado_em: datetime


@dataclass(frozen=True)
class RespostaDaIA:
    dados: dict[str, Any]
    provedor: str
    modelo: str


class FalhaDoProvedor(Exception):
    """O provedor não respondeu do jeito certo (rede, limite, chave, recusa, JSON fora do esquema).

    `chave_recusada`: 401 ou 403 (chave vencida, revogada ou sem permissão): o provedor fica
    desligado por 10 minutos e a análise usa a reserva.
    """

    def __init__(self, provedor: str, motivo: str, temporaria: bool = False, chave_recusada: bool = False):
        super().__init__(f"{provedor}: {motivo}")
        self.provedor = provedor
        self.motivo = motivo
        self.temporaria = temporaria
        self.chave_recusada = chave_recusada


@dataclass(frozen=True)
class EntradaDaLeitura:
    fotos: tuple[FotoPreparada, ...]
    categorias: tuple[str, ...]


@dataclass(frozen=True)
class EntradaDaReleitura:
    """Releitura de uma etiqueta (recorte) ou de uma foto extra, com a leitura atual como contexto."""

    fotos_da_leitura: tuple[FotoPreparada, ...]  # o mesmo começo da leitura (aproveita o cache)
    leitura_atual: dict[str, Any]
    imagem_jpeg: bytes = field(repr=False)
    tipo: str = "etiqueta"  # etiqueta | foto_extra


@dataclass(frozen=True)
class EntradaDaPesquisa:
    produto: str
    categoria: str
    condicao: str
    atributos: tuple[tuple[str, str], ...]
    com_web: bool


@dataclass(frozen=True)
class EntradaDoPreco:
    dados_do_mercado: dict[str, Any]  # estatística, tarifas e o sugerido pela regra
    atributos: tuple[tuple[str, str], ...]
    condicao: str
    defeitos: tuple[str, ...]
    canais_candidatos: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class EntradaDoTexto:
    produto: str
    categoria: str
    condicao: str
    atributos: tuple[tuple[str, str], ...]
    defeitos: tuple[str, ...]
    perfil: dict[str, Any] | None


@dataclass(frozen=True)
class PrecoObservado:
    preco_centavos: int
    frete_gratis: bool


@dataclass(frozen=True)
class CategoriaSugerida:
    categoria_id: str
    nome: str
    dominio: str = ""


@dataclass(frozen=True)
class ConfiguracaoDaIA:
    """Interruptores e limites que a análise consulta (vindos da configuração, na partida)."""

    ia_ativa: bool = True
    pesquisa_web_ativa: bool = True
    tratamento_foto_ativo: bool = False  # versão final
    orcamento_diario_usd: Decimal = Decimal("0.30")
