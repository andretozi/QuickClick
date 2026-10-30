"""
Domínio · Produto (o anúncio da Quick Click) e as publicações dele nos canais

O produto pertence a um vendedor; o vendedor fica fora da entidade e vem sempre do token,
nunca do que o navegador manda. `atualizado_em` é a versão do registro.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Publicacao:
    canal: str  # slug do catálogo
    status: str  # publicado | pausado | nao_publicado
    id_externo: str | None = None
    permalink: str | None = None
    categoria_id: str | None = None
    saude: float | None = None
    vendidos: int = 0


@dataclass(frozen=True)
class Produto:
    id: str
    titulo: str
    descricao: str
    categoria: str
    condicao: str  # novo | usado
    preco_centavos: int
    preco_sugerido_centavos: int | None
    estoque: int
    fotos: list[str]
    capa: int
    atributos: list[dict[str, Any]]
    analise_id: str | None
    criado_em: datetime
    atualizado_em: datetime
    publicacoes: list[Publicacao] = field(default_factory=list)
