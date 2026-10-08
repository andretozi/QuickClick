"""Domínio · Vendedor: quem usa a Quick Click para vender nos marketplaces."""

from dataclasses import dataclass

from backend.domain.plano import Plano


@dataclass(frozen=True)
class Vendedor:
    id: int
    nome: str
    plano: Plano
