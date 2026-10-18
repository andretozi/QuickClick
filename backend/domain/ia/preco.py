"""
Domínio · IA · Estatística de preço

Contas sempre no Python; a IA só interpreta. Itens parecidos ativos → tira os fora da curva
pelo intervalo interquartil → p25, mediana, p75, quantidade e quantos têm frete grátis.
No Grátis o sugerido é a mediana, ajustada pela condição (usado: entre o p25 e a mediana).
"""

from dataclasses import asdict, dataclass

MINIMO_DE_ITENS = 3  # com menos que isso não dá estatística confiável
FATOR_IQR = 1.5


@dataclass(frozen=True)
class Concorrente:
    preco_centavos: int
    frete_gratis: bool


@dataclass(frozen=True)
class EstatisticaDePreco:
    quantidade: int
    descartados: int
    p25: int
    mediana: int
    p75: int
    minimo: int
    maximo: int
    com_frete_gratis: int

    def para_dict(self) -> dict:
        return asdict(self)


def percentil(ordenados: list[int], p: float) -> float:
    """Percentil com interpolação linear (como o numpy padrão)."""
    if not ordenados:
        raise ValueError("Sem valores para o percentil.")
    posicao = (len(ordenados) - 1) * p
    baixo = int(posicao)
    alto = min(baixo + 1, len(ordenados) - 1)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (posicao - baixo)


def sem_fora_da_curva(concorrentes: list[Concorrente]) -> list[Concorrente]:
    precos = sorted(c.preco_centavos for c in concorrentes)
    if len(precos) < 4:
        return list(concorrentes)
    q1, q3 = percentil(precos, 0.25), percentil(precos, 0.75)
    folga = (q3 - q1) * FATOR_IQR
    return [c for c in concorrentes if q1 - folga <= c.preco_centavos <= q3 + folga]


def estatistica(concorrentes: list[Concorrente]) -> EstatisticaDePreco | None:
    validos = [c for c in concorrentes if c.preco_centavos > 0]
    filtrados = sem_fora_da_curva(validos)
    if len(filtrados) < MINIMO_DE_ITENS:
        return None
    precos = sorted(c.preco_centavos for c in filtrados)
    return EstatisticaDePreco(
        quantidade=len(filtrados),
        descartados=len(validos) - len(filtrados),
        p25=round(percentil(precos, 0.25)),
        mediana=round(percentil(precos, 0.5)),
        p75=round(percentil(precos, 0.75)),
        minimo=precos[0],
        maximo=precos[-1],
        com_frete_gratis=sum(1 for c in filtrados if c.frete_gratis),
    )


def arredondar_para_vitrine(centavos: int) -> int:
    """R$ 187,34 vira R$ 187,90: o jeito que o comprador vê preço nos marketplaces."""
    if centavos < 1000:
        return max(100, round(centavos / 10) * 10)
    return (centavos // 100) * 100 + 90


def preco_sugerido_por_regra(est: EstatisticaDePreco, condicao: str | None) -> int:
    """Grátis: mediana para novo; entre o p25 e a mediana para usado ou recondicionado."""
    if condicao in ("usado", "recondicionado"):
        return arredondar_para_vitrine((est.p25 + est.mediana) // 2)
    return arredondar_para_vitrine(est.mediana)


def preco_da_ia_aceitavel(preco_centavos: int, est: EstatisticaDePreco) -> bool:
    """A sugestão da IA precisa ficar perto dos dados reais (entre metade do p25 e uma vez e meia o p75)."""
    return est.p25 // 2 <= preco_centavos <= est.p75 * 3 // 2
