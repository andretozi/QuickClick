"""
Domínio · Usuário (Vendedor e Administrador)

Entidade central com suporte a controle de acesso baseado em papéis (RBAC),
ciclo de vida de moderação (ativa, advertida, suspensa, banida) e auditoria.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import re

PAPEL_VENDEDOR = "vendedor"
PAPEL_ADMIN = "admin"
PAPEIS_VALIDOS = frozenset({PAPEL_VENDEDOR, PAPEL_ADMIN})

STATUS_ATIVA = "ativa"
STATUS_ADVERTIDA = "advertida"
STATUS_SUSPENSA = "suspensa"
STATUS_BANIDA = "banida"
STATUS_CONTA_VALIDOS = frozenset({STATUS_ATIVA, STATUS_ADVERTIDA, STATUS_SUSPENSA, STATUS_BANIDA})

JANELA_SESSAO_PADRAO = timedelta(minutes=30)
_PADRAO_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def normalizar_email(email: str) -> str:
    return (email or "").strip().lower()


def email_valido(email: str) -> bool:
    return bool(_PADRAO_EMAIL.match(normalizar_email(email)))


def extrair_emails_admin(config_valor: str | None) -> frozenset[str]:
    """Interpreta lista de e-mails de administradores separados por vírgula."""
    if not config_valor:
        return frozenset()
    emails = {e.strip().lower() for e in config_valor.split(",") if e.strip()}
    return frozenset(emails)


def mascarar_email(email: str) -> str:
    """Pseudonimização para logs de auditoria e resposta a incidentes (LGPD)."""
    if not email or "@" not in email:
        return "***"
    usuario, dominio = email.split("@", 1)
    if len(usuario) <= 2:
        usuario_mascarado = usuario[0] + "***" if usuario else "***"
    else:
        usuario_mascarado = usuario[:2] + "***"
    return f"{usuario_mascarado}@{dominio}"


@dataclass
class Usuario:
    id: int
    email: str
    nome: str
    loja: str
    plano: str
    tem_senha: bool = True
    papel: str = PAPEL_VENDEDOR
    status_conta: str = STATUS_ATIVA
    motivo_moderacao: str | None = None
    suspensa_ate: datetime | None = None
    token_versao: int = 0
    ultimo_login_em: datetime | None = None
    ultimo_acesso_em: datetime | None = None

    @property
    def eh_admin(self) -> bool:
        return self.papel == PAPEL_ADMIN

    def status_efetivo(self, agora: datetime) -> str:
        if self.status_conta == STATUS_SUSPENSA and self.suspensa_ate is not None:
            agora_norm = agora if agora.tzinfo is not None else agora.replace(tzinfo=UTC)
            ate_norm = (
                self.suspensa_ate
                if self.suspensa_ate.tzinfo is not None
                else self.suspensa_ate.replace(tzinfo=UTC)
            )
            if agora_norm >= ate_norm:
                return STATUS_ATIVA
        if self.status_conta in STATUS_CONTA_VALIDOS:
            return self.status_conta
        return STATUS_ATIVA

    def esta_bloqueado(self, agora: datetime) -> bool:
        return self.status_efetivo(agora) in {STATUS_SUSPENSA, STATUS_BANIDA}

    def advertencia_ativa(self, agora: datetime) -> str | None:
        if self.status_efetivo(agora) == STATUS_ADVERTIDA and self.motivo_moderacao:
            return self.motivo_moderacao
        return None

    def sessao_ativa(self, agora: datetime, janela: timedelta = JANELA_SESSAO_PADRAO) -> bool:
        if self.esta_bloqueado(agora) or self.ultimo_login_em is None:
            return False
        agora_norm = agora if agora.tzinfo is not None else agora.replace(tzinfo=UTC)
        login_norm = (
            self.ultimo_login_em
            if self.ultimo_login_em.tzinfo is not None
            else self.ultimo_login_em.replace(tzinfo=UTC)
        )
        return (agora_norm - login_norm) <= janela
