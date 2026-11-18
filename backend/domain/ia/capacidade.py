"""
Domínio · IA · O que cada plano tem, cotas e limites

    Plano       Análises por mês   Leitura da foto        Pesquisa de mercado     Preço               Texto
    gratis      5                  Gemini Flash grátis    não (perfil sem web)    só Python           Gemini Flash grátis
                                   (reserva: Haiku)                               (mediana)           (reserva: Haiku)
    essencial   40                 Sonnet 5.5             sim, com cache          Python + Sonnet     Sonnet 5.5
    pro         120                Opus 5.5               sim, com cache          Python + Opus       Sonnet 5.5
    business    400                Opus 5.5               sim, com cache          Python + Opus       Sonnet 5.5

Uma análise só conta na cota quando termina (pronta). Falha do provedor não conta.
O Pro e o Business têm também a análise de mercado (só dos marketplaces integrados) e o orientador (Opus) na
pesquisa, quando ADVISOR_ATIVO está ligado. O plano pago nunca cai no Gemini grátis: com o orçamento do dia
da chave paga esgotado, ele fica sem IA até amanhã.
O André ajusta os números aqui.
"""

from dataclasses import dataclass
from decimal import Decimal

from backend.domain.erros import AnaliseEmAndamento, CotaEsgotada, LimitePorHora
from backend.domain.ia.analise import Nivel

ANALISES_POR_MES: dict[str, int] = {"gratis": 5, "essencial": 40, "pro": 120, "business": 400}
PLANOS_DE_PONTA = ("pro", "business")
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
    def modelo_de_ponta(self) -> bool:
        """Opus na leitura da foto e no preço, e orientador na pesquisa: só no Pro e no Business (o Essencial usa o Sonnet)."""
        return self.nivel is Nivel.PAGO and self.plano in PLANOS_DE_PONTA

    @property
    def analise_de_mercado(self) -> bool:
        """Bloco de análise de mercado do passo de canais (só do Mercado Livre, o único integrado)."""
        return self.modelo_de_ponta

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


def orcamento_esgotado(capacidade: CapacidadeIA, gasto_hoje_usd: Decimal, orcamento_diario_usd: Decimal) -> bool:
    """O teto do dia vale só para a chave paga (o grátis não gasta dela). Esgotou: o plano pago espera amanhã."""
    return capacidade.nivel is Nivel.PAGO and gasto_hoje_usd >= orcamento_diario_usd
