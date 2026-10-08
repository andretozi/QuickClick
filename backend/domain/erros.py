"""
Domínio · Erros de negócio

Cada erro tem um código estável (para quem consome a API) e uma mensagem amigável,
que aparece na tela do vendedor. Por isso as mensagens seguem a regra de escrita:
sem traço e sem barra.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.domain.plano import Plano


def juntar_nomes(nomes: Sequence[str]) -> str:
    """["Mercado Livre", "Shopee", "Amazon"] vira "Mercado Livre, Shopee e Amazon"."""
    if len(nomes) <= 1:
        return "".join(nomes)
    return f"{', '.join(nomes[:-1])} e {nomes[-1]}"


class ErroDeDominio(Exception):
    codigo = "erro_de_negocio"

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class VendedorNaoEncontrado(ErroDeDominio):
    codigo = "vendedor_nao_encontrado"

    def __init__(self, vendedor_id: int):
        super().__init__("Não encontramos a sua conta de vendedor.")
        self.vendedor_id = vendedor_id


class MarketplaceNaoEncontrado(ErroDeDominio):
    codigo = "marketplace_nao_encontrado"

    def __init__(self, slug: str):
        super().__init__("Esse marketplace não existe no nosso catálogo.")
        self.slug = slug


class MarketplaceEmBreve(ErroDeDominio):
    codigo = "marketplace_em_breve"

    def __init__(self, nome: str, disponiveis: Sequence[str]):
        super().__init__(
            f"A integração com {nome} ainda está chegando. "
            f"Por enquanto dá pra conectar {juntar_nomes(disponiveis)}."
        )
        self.nome = nome


class LimiteDoPlanoAtingido(ErroDeDominio):
    codigo = "limite_do_plano"

    def __init__(self, plano: Plano, plano_sugerido: Plano | None):
        limite = plano.limite_marketplaces
        quantidade = f"{limite} marketplace" if limite == 1 else f"{limite} marketplaces"
        mensagem = f"No plano {plano.nome} você conecta {quantidade}."
        if plano_sugerido is not None:
            mensagem += f" Pra conectar mais, mude para o plano {plano_sugerido.nome}."
        super().__init__(mensagem)
        self.plano = plano
        self.plano_sugerido = plano_sugerido
