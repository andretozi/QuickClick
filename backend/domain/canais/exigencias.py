"""
Domínio · Canais · Exigências: a união do que os canais conectados pedem

Cada chave nossa aparece uma vez, com os canais que a pedem; campo sem chave (só de um canal) vira
exigência própria. Falta o que é obrigatório e o vendedor ainda não confirmou: valor que a IA só
leu nunca conta como confirmado.
"""

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from backend.domain.canais.esquema import CampoDoCanal, EsquemaDoCanal, TipoDeCampo
from backend.domain.canais.ficha import FichaDoProduto

# Ordem de força do tipo quando os canais discordam: lista ganha de booleano, que ganha de número
_TIPOS_FORTES = (TipoDeCampo.LISTA, TipoDeCampo.BOOLEANO, TipoDeCampo.NUMERO)


@dataclass(frozen=True)
class Exigencia:
    chave: str  # a chave nossa; "" = campo próprio de um canal
    nome: str
    tipo: TipoDeCampo
    valores: tuple[str, ...] = ()  # nomes da lista fechada (ou do booleano); vazio nos outros tipos
    unidade: str = ""
    obrigatoria: bool = False
    canais: tuple[str, ...] = ()
    campos: tuple[CampoDoCanal, ...] = ()


def comparavel(texto: str) -> str:
    """Sem acento, sem caixa e sem espaços extras: ' Não ' e 'nao' casam."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return " ".join("".join(c for c in decomposto if not unicodedata.combining(c)).split()).casefold()


def _nomes(campo: CampoDoCanal | None) -> tuple[str, ...]:
    return tuple(dict.fromkeys(nome for _, nome in campo.valores)) if campo is not None else ()


def _exigencia(chave: str, campos: list[CampoDoCanal], valores: tuple[str, ...] | None = None) -> Exigencia:
    tipos = {c.tipo for c in campos}
    tipo = next((t for t in _TIPOS_FORTES if t in tipos), TipoDeCampo.TEXTO)
    if valores is None and tipo in (TipoDeCampo.LISTA, TipoDeCampo.BOOLEANO):
        valores = _nomes(next((c for c in campos if c.tipo is tipo and c.valores), None))
    numerico = next((c for c in campos if c.tipo is TipoDeCampo.NUMERO), None)
    return Exigencia(
        chave=chave, nome=campos[0].nome, tipo=tipo, valores=valores or (),
        unidade=numerico.unidade if tipo is TipoDeCampo.NUMERO and numerico is not None else "",
        obrigatoria=any(c.obrigatorio for c in campos), canais=tuple(dict.fromkeys(c.canal for c in campos)),
        campos=tuple(campos),
    )


def _unir_chave(chave: str, campos: list[CampoDoCanal]) -> list[Exigencia]:
    listas: dict[str, CampoDoCanal] = {}
    for campo in campos:
        if campo.tipo is TipoDeCampo.LISTA:
            listas.setdefault(campo.canal, campo)
    if len(listas) < 2:
        return [_exigencia(chave, campos)]
    primeira, *outras = listas.values()
    nomes_das_outras = [{comparavel(n) for n in _nomes(o)} for o in outras]
    comuns = tuple(n for n in _nomes(primeira) if all(comparavel(n) in nomes for nomes in nomes_das_outras))
    if comuns:
        return [_exigencia(chave, campos, comuns)]
    # Nenhum valor serve a todos: cada canal pergunta o dele, como campo próprio
    return [_exigencia("", [c for c in campos if c.canal == canal]) for canal in dict.fromkeys(c.canal for c in campos)]


def unir_exigencias(esquemas: Iterable[EsquemaDoCanal]) -> tuple[Exigencia, ...]:
    """Na ordem do primeiro esquema, depois o que os seguintes acrescentam."""
    grupos: dict[tuple[str, ...], list[CampoDoCanal]] = {}
    for esquema in esquemas:
        for campo in esquema.campos:
            grupo = (campo.chave,) if campo.chave else ("", campo.canal, campo.id)
            grupos.setdefault(grupo, []).append(campo)
    exigencias: list[Exigencia] = []
    for grupo, campos in grupos.items():
        exigencias += _unir_chave(grupo[0], campos) if grupo[0] else [_exigencia("", campos)]
    return tuple(exigencias)


def faltantes(exigencias: Iterable[Exigencia], ficha: FichaDoProduto) -> tuple[Exigencia, ...]:
    """Obrigatórias sem valor confirmado na ficha. Campo próprio obrigatório sempre falta (a ficha não o guarda)."""
    confirmadas = {v.chave for v in ficha.valores if v.confirmado}
    return tuple(e for e in exigencias if e.obrigatoria and (not e.chave or e.chave not in confirmadas))
