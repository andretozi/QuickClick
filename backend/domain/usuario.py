"""Domínio · Usuário do sistema."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Usuario:
    id: int
    email: str
    nome: str
    loja: str
    plano: str
