"""Domínio · Usuário do sistema e regras puras de email."""

from dataclasses import dataclass
import re

_PADRAO_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def email_valido(email: str) -> bool:
    return bool(_PADRAO_EMAIL.match(normalizar_email(email)))


@dataclass(frozen=True)
class Usuario:
    id: int
    email: str
    nome: str
    loja: str
    plano: str
    tem_senha: bool = True
