"""
Domínio · IA · Canais candidatos para o anúncio

Primeiro os marketplaces que o vendedor já conectou (na ordem em que conectou), depois os do
catálogo que combinam com a categoria, a faixa de preço e a condição. Os não conectados
aparecem como "Vale abrir conta" (o front mostra o motivo de uma frase e o link de cadastro).
Só o Mercado Livre publica por enquanto.
"""

from dataclasses import dataclass

from backend.domain.marketplace import CATALOGO

MAX_SUGERIDOS = 4
REAIS = 100  # centavos


@dataclass(frozen=True)
class Afinidade:
    categorias: frozenset[str] | None  # None: combina com tudo
    preco_min_centavos: int = 0
    preco_max_centavos: int | None = None
    aceita_usado: bool = True


# Tabela simples de afinidade (o André ajusta)
AFINIDADE: dict[str, Afinidade] = {
    "mercado-livre": Afinidade(None),
    "shopee": Afinidade(frozenset({"moda", "calcados", "acessorios", "casa", "cozinha", "beleza", "brinquedos",
                                   "eletronicos", "esporte"}), preco_max_centavos=800 * REAIS),
    "amazon": Afinidade(frozenset({"eletronicos", "livros", "casa", "cozinha", "esporte", "brinquedos", "beleza"}),
                        aceita_usado=False),
    "magalu": Afinidade(frozenset({"eletronicos", "casa", "cozinha", "esporte", "brinquedos"}),
                        preco_min_centavos=30 * REAIS, aceita_usado=False),
    "americanas": Afinidade(frozenset({"eletronicos", "casa", "cozinha", "brinquedos", "beleza", "livros"}),
                            aceita_usado=False),
    "casas-bahia": Afinidade(frozenset({"eletronicos", "casa", "cozinha"}), preco_min_centavos=80 * REAIS,
                             aceita_usado=False),
    "shein": Afinidade(frozenset({"moda", "calcados", "acessorios", "beleza"}), preco_max_centavos=400 * REAIS,
                       aceita_usado=False),
    "tiktok-shop": Afinidade(frozenset({"moda", "beleza", "acessorios", "casa", "cozinha"}),
                             preco_max_centavos=500 * REAIS, aceita_usado=False),
    "aliexpress": Afinidade(frozenset({"acessorios", "eletronicos", "casa", "brinquedos"}),
                            preco_max_centavos=500 * REAIS, aceita_usado=False),
}


@dataclass(frozen=True)
class CanalCandidato:
    slug: str
    conectado: bool
    motivo: str | None = None  # a frase da IA no plano pago; no Grátis o front usa o texto fixo do slug

    def para_dict(self) -> dict:
        return {"slug": self.slug, "conectado": self.conectado, "motivo": self.motivo}


def combina(slug: str, categoria: str | None, preco_centavos: int | None, condicao: str | None) -> bool:
    afinidade = AFINIDADE.get(slug)
    if afinidade is None:
        return False
    if categoria and afinidade.categorias is not None and categoria not in afinidade.categorias:
        return False
    if condicao in ("usado", "recondicionado") and not afinidade.aceita_usado:
        return False
    if preco_centavos is not None:
        if preco_centavos < afinidade.preco_min_centavos:
            return False
        if afinidade.preco_max_centavos is not None and preco_centavos > afinidade.preco_max_centavos:
            return False
    return True


def canais_candidatos(conectados: list[str], categoria: str | None, preco_centavos: int | None,
                      condicao: str | None) -> list[CanalCandidato]:
    """Os conectados primeiro (todos), depois até 4 do catálogo que combinam com o produto."""
    no_catalogo = {m.slug for m in CATALOGO}
    candidatos = [CanalCandidato(slug, True) for slug in conectados if slug in no_catalogo]
    ja = {c.slug for c in candidatos}
    sugeridos = [
        CanalCandidato(m.slug, False)
        for m in CATALOGO
        if m.slug not in ja and combina(m.slug, categoria, preco_centavos, condicao)
    ]
    return candidatos + sugeridos[:MAX_SUGERIDOS]


def aplicar_motivos(candidatos: list[CanalCandidato], motivos: dict[str, str]) -> list[CanalCandidato]:
    """Põe a frase da IA em cada canal que ela comentou (a IA só comenta, nunca escolhe fora da lista)."""
    return [CanalCandidato(c.slug, c.conectado, motivos.get(c.slug) or None) for c in candidatos]
