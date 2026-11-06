"""Domínio · Entidades puras de moderação administrativa e auditoria."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from backend.domain.usuario import Usuario

ACAO_ADVERTIR = "advertir"
ACAO_SUSPENDER = "suspender"
ACAO_BANIR = "banir"
ACAO_REATIVAR = "reativar"
ACAO_ENCERRAR_SESSAO = "encerrar_sessao"
ACAO_DESVINCULAR_MARKETPLACE = "desvincular_marketplace"
ACAO_EXCLUIR_CONTA = "excluir_conta"

PUNICOES_VALIDAS = frozenset({ACAO_ADVERTIR, ACAO_SUSPENDER, ACAO_BANIR})
FILTROS_STATUS_MODERACAO = frozenset({"todos", "online", "advertida", "suspensa", "banida", "admin"})


@dataclass(frozen=True)
class ConexaoResumo:
    marketplace: str
    apelido: str | None
    conectada_em: str


@dataclass(frozen=True)
class ContaMonitorada:
    usuario: Usuario
    status_efetivo: str
    sessao_ativa: bool
    usa_google: bool
    criado_em: str | None
    marketplaces_conectados: tuple[ConexaoResumo, ...]
    total_produtos: int
    total_analises_ia: int


@dataclass(frozen=True)
class ResumoModeracao:
    total_contas: int
    sessoes_ativas: int
    contas_advertidas: int
    contas_suspensas: int
    contas_banidas: int
    conexoes_ativas: int


@dataclass(frozen=True)
class PainelModeracao:
    resumo: ResumoModeracao
    contas: list[ContaMonitorada]
    total_filtrado: int


@dataclass(frozen=True)
class RegistroAuditoria:
    id: int
    admin_id: int | None
    admin_email: str
    alvo_id: int | None
    alvo_identificador: str
    acao: str
    motivo: str | None
    detalhes: dict[str, Any] | None
    criado_em: datetime
