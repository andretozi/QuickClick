"""
Domínio · IA · O que cada plano tem, cotas e limites

    Plano       Análises por mês   Leitura da foto        Pesquisa de mercado     Preço               Texto
    gratis      5                  Gemini Flash grátis    não (perfil sem web)    só Python           Gemini Flash grátis
                                   (reserva: Haiku)                               (mediana)           (reserva: Haiku)
    essencial   40                 Opus 5.5               sim, com cache          Python + Opus       Sonnet 5.5
    pro         120                Opus 5.5               sim, com cache          Python + Opus       Sonnet 5.5
    business    400                Opus 5.5               sim, com cache          Python + Opus       Sonnet 5.5

Uma análise só conta na cota quando termina (pronta). Falha do provedor não conta.
O André ajusta os números aqui.
"""

from dataclasses import dataclass
from decimal import Decimal

from backend.domain.erros import AnaliseEmAndamento, CotaEsgotada, LimitePorHora
from backend.domain.ia.analise import Nivel

ANALISES_POR_MES: dict[str, int] = {"gratis": 5, "essencial": 40, "pro": 120, "business": 400}
ANALISES_POR_HORA = 10
ANALISES_AO_MESMO_TEMPO = 1
ORCAMENTO_DIARIO_PADRAO_USD = Decimal("0.30")


@dataclass(frozen=True)
class CapacidadeIA:
    plano: str
    nivel: Nivel
    analises_por_mes: int

    @property
    def pesquisa_de_mercado(self) -> bool:
        """Pesquisa com busca na web e cache (o Grátis tem só um perfil do comprador, sem web)."""
        return self.nivel is Nivel.PAGO

    @property
    def preco_com_analise(self) -> bool:
        """Preço com análise da concorrência pela IA (o Grátis usa só a mediana, em Python)."""
        return self.nivel is Nivel.PAGO


def capacidade_do_plano(slug: str) -> CapacidadeIA:
    """Plano desconhecido vale como Grátis (nunca libera IA paga por engano)."""
    if slug not in ANALISES_POR_MES:
        slug = "gratis"
    nivel = Nivel.GRATIS if slug == "gratis" else Nivel.PAGO
    return CapacidadeIA(plano=slug, nivel=nivel, analises_por_mes=ANALISES_POR_MES[slug])


def restantes(capacidade: CapacidadeIA, usadas_no_mes: int) -> int:
    return max(0, capacidade.analises_por_mes - usadas_no_mes)


def garantir_pode_comecar(capacidade: CapacidadeIA, usadas_no_mes: int, em_andamento: int,
                          na_ultima_hora: int) -> None:
    """Cota do mês, uma análise por vez e no máximo 10 por hora."""
    if em_andamento >= ANALISES_AO_MESMO_TEMPO:
        raise AnaliseEmAndamento()
    if restantes(capacidade, usadas_no_mes) <= 0:
        raise CotaEsgotada(capacidade.analises_por_mes)
    if na_ultima_hora >= ANALISES_POR_HORA:
        raise LimitePorHora(ANALISES_POR_HORA)


def nivel_efetivo(nivel: Nivel, gasto_hoje_usd: Decimal, orcamento_diario_usd: Decimal) -> tuple[Nivel, bool]:
    """(nível que vale agora, se o orçamento do dia estourou). Estourou: a IA paga cai no caminho grátis."""
    if nivel is Nivel.PAGO and gasto_hoje_usd >= orcamento_diario_usd:
        return Nivel.GRATIS, True
    return nivel, False
