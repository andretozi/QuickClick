"""
Aplicação · IA · Escolha do provedor por plano (nível) e a ordem de reserva

    etapa       pago                                   grátis
    leitura     Opus 5.5 → Haiku 5.5 (chave paga)      Gemini Flash grátis → Haiku 5.5 (chave grátis)
    pesquisa    Sonnet 5.5 (web) → Haiku (paga)        Haiku (grátis), sem web
    preço       Opus 5.5 (sem fotos) → regra Python    só regra Python
    texto       Sonnet 5.5 → Haiku (paga)              Gemini Flash grátis → Haiku (grátis)
    correção    Haiku (paga)                           Haiku (grátis)

Decisão: a reserva do pago fica na chave paga da Anthropic (as fotos de quem paga não vão para a
camada grátis do Google por causa de uma falha). Quando o orçamento do dia estoura, o nível
efetivo vira grátis de propósito, com aviso na tela.
Um provedor sem chave, ou com a chave recusada há menos de 10 minutos, é pulado.
"""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeVar

from backend.application.ia.modelos import FalhaDoProvedor, RespostaDaIA
from backend.application.ia.portas import (
    LeitorDeProduto,
    LigadorDeAtributos,
    PesquisadorDeMercado,
    PesquisadorDePrecosNaWeb,
    Precificador,
    ProvedorDeIA,
    Redator,
)
from backend.domain.ia.analise import Nivel

log = logging.getLogger("quickclick.ia")

P = TypeVar("P", bound=ProvedorDeIA)


@dataclass(frozen=True)
class ProvedoresDeIA:
    leitor_visao_pago: LeitorDeProduto | None = None
    leitor_rapido_pago: LeitorDeProduto | None = None
    leitor_gemini_gratis: LeitorDeProduto | None = None
    leitor_rapido_gratis: LeitorDeProduto | None = None
    pesquisador_pago: PesquisadorDeMercado | None = None
    pesquisador_rapido_pago: PesquisadorDeMercado | None = None
    pesquisador_gratis: PesquisadorDeMercado | None = None
    precificador_pago: Precificador | None = None
    precos_na_web_pago: PesquisadorDePrecosNaWeb | None = None
    redator_pago: Redator | None = None
    redator_rapido_pago: Redator | None = None
    redator_gemini_gratis: Redator | None = None
    redator_rapido_gratis: Redator | None = None
    ligador_pago: LigadorDeAtributos | None = None
    ligador_gratis: LigadorDeAtributos | None = None


def _disponiveis(candidatos: Sequence[P | None]) -> list[P]:
    return [c for c in candidatos if c is not None and c.disponivel()]


def leitores(p: ProvedoresDeIA, nivel: Nivel) -> list[LeitorDeProduto]:
    if nivel is Nivel.PAGO:
        return _disponiveis([p.leitor_visao_pago, p.leitor_rapido_pago])
    return _disponiveis([p.leitor_gemini_gratis, p.leitor_rapido_gratis])


def pesquisadores(p: ProvedoresDeIA, nivel: Nivel) -> list[PesquisadorDeMercado]:
    if nivel is Nivel.PAGO:
        return _disponiveis([p.pesquisador_pago, p.pesquisador_rapido_pago])
    return _disponiveis([p.pesquisador_gratis])


def precificadores(p: ProvedoresDeIA, nivel: Nivel) -> list[Precificador]:
    return _disponiveis([p.precificador_pago]) if nivel is Nivel.PAGO else []


def precos_na_web(p: ProvedoresDeIA, nivel: Nivel) -> list[PesquisadorDePrecosNaWeb]:
    return _disponiveis([p.precos_na_web_pago]) if nivel is Nivel.PAGO else []


def redatores(p: ProvedoresDeIA, nivel: Nivel) -> list[Redator]:
    if nivel is Nivel.PAGO:
        return _disponiveis([p.redator_pago, p.redator_rapido_pago])
    return _disponiveis([p.redator_gemini_gratis, p.redator_rapido_gratis])


def corretores(p: ProvedoresDeIA, nivel: Nivel) -> list[Redator]:
    return _disponiveis([p.redator_rapido_pago if nivel is Nivel.PAGO else p.redator_rapido_gratis])


def ligadores(p: ProvedoresDeIA, nivel: Nivel) -> list[LigadorDeAtributos]:
    return _disponiveis([p.ligador_pago if nivel is Nivel.PAGO else p.ligador_gratis])


def tentar_em_ordem(provedores: Sequence[P], chamada: Callable[[P], RespostaDaIA]
                    ) -> tuple[RespostaDaIA, P] | None:
    """Tenta cada provedor na ordem; devolve a primeira resposta boa, ou None se todos falharem."""
    for provedor in provedores:
        try:
            return chamada(provedor), provedor
        except FalhaDoProvedor as falha:
            log.warning("IA: %s falhou (%s); tentando a reserva.", provedor.nome, falha.motivo)
    return None
