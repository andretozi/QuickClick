"""
Infraestrutura · IA · Tabela de preços (US$ por milhão de tokens) e o custo estimado de cada chamada

Conferida em 2026-10-17 em https://platform.claude.com/docs/en/about-claude/pricing:
    Opus 5.5    entrada 4    cache 5m 5      cache 1h 8     cache lido 0,20   saída 20
    Sonnet 5.5  entrada 2    cache 5m 2,50   cache 1h 4     cache lido 0,10   saída 10
    Haiku 5.5   entrada 0,10 cache 5m 0,125  cache 1h 0,20  cache lido 0,01   saída 0,50  (até 100 mil tokens)
                entrada 0,50 cache 5m 0,625  cache 1h 1     cache lido 0,05   saída 2,50  (acima de 100 mil)
    Busca na web: US$ 10 por 1.000 buscas.
Gemini na camada grátis: custo zero (o projeto quickclick-gratis não tem cobrança).
Modelo fora da tabela: estimado pelo preço do Opus (para o orçamento do dia errar para mais).
"""

from dataclasses import dataclass
from decimal import Decimal

MILHAO = Decimal(1_000_000)
PRECO_POR_BUSCA_WEB = Decimal("0.01")
LIMITE_PROMPT_CURTO_HAIKU = 100_000


@dataclass(frozen=True)
class Preco:
    entrada: Decimal
    cache_5m: Decimal
    cache_1h: Decimal
    cache_lido: Decimal
    saida: Decimal


def _p(entrada, cache_5m, cache_1h, cache_lido, saida) -> Preco:
    return Preco(*(Decimal(str(v)) for v in (entrada, cache_5m, cache_1h, cache_lido, saida)))


PRECOS: dict[str, Preco] = {
    "claude-opus-5-5": _p(4, 5, 8, 0.20, 20),
    "claude-sonnet-5-5": _p(2, 2.5, 4, 0.10, 10),
    "claude-haiku-5-5": _p(0.10, 0.125, 0.20, 0.01, 0.50),
}
PRECO_HAIKU_PROMPT_LONGO = _p(0.50, 0.625, 1, 0.05, 2.50)
PRECO_DESCONHECIDO = PRECOS["claude-opus-5-5"]


def custo_anthropic(modelo: str, entrada: int, saida: int, cache_lido: int, cache_gravado: int,
                    buscas_web: int, ttl_cache: str) -> Decimal:
    preco = PRECOS.get(modelo, PRECO_DESCONHECIDO)
    if modelo == "claude-haiku-5-5" and entrada + cache_lido + cache_gravado > LIMITE_PROMPT_CURTO_HAIKU:
        preco = PRECO_HAIKU_PROMPT_LONGO
    escrita = preco.cache_1h if ttl_cache == "1h" else preco.cache_5m
    tokens = (
        Decimal(entrada) * preco.entrada
        + Decimal(cache_gravado) * escrita
        + Decimal(cache_lido) * preco.cache_lido
        + Decimal(saida) * preco.saida
    ) / MILHAO
    return (tokens + Decimal(buscas_web) * PRECO_POR_BUSCA_WEB).quantize(Decimal("0.000001"))
