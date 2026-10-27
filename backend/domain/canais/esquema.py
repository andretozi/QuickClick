"""
Domínio · Canais · Esquema de campos que um canal pede para uma categoria

Cada canal (Mercado Livre, Shopee, Amazon) descreve os campos no próprio formato; aqui fica o
modelo comum: id e nome do campo, se é obrigatório, o tipo, a lista fechada de valores, a unidade
e a chave nossa que ele representa (vazia quando o campo é só do canal).
"""

from dataclasses import dataclass
from enum import StrEnum


class TipoDeCampo(StrEnum):
    TEXTO = "texto"
    NUMERO = "numero"
    LISTA = "lista"
    BOOLEANO = "booleano"


@dataclass(frozen=True)
class CampoDoCanal:
    canal: str  # id do catálogo: "mercado-livre", "shopee", "amazon"
    id: str  # id do campo no canal
    nome: str
    obrigatorio: bool
    tipo: TipoDeCampo
    valores: tuple[tuple[str, str], ...] = ()  # (id, nome) quando a lista é fechada
    unidade: str = ""
    chave: str = ""  # a chave nossa; vazia = campo próprio do canal


@dataclass(frozen=True)
class EsquemaDoCanal:
    canal: str
    categoria_id: str
    categoria_nome: str
    campos: tuple[CampoDoCanal, ...] = ()

    def obrigatorios(self) -> tuple[CampoDoCanal, ...]:
        """Os campos obrigatórios, na ordem do esquema."""
        return tuple(c for c in self.campos if c.obrigatorio)

    def por_chave(self) -> dict[str, tuple[CampoDoCanal, ...]]:
        """Chave nossa → todos os campos que a representam, na ordem do esquema (sem os campos próprios do canal)."""
        grupos: dict[str, list[CampoDoCanal]] = {}
        for campo in self.campos:
            if campo.chave:
                grupos.setdefault(campo.chave, []).append(campo)
        return {chave: tuple(campos) for chave, campos in grupos.items()}
