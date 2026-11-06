"""
Infraestrutura · Repositório de Moderação e Auditoria via SQLAlchemy.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.domain.moderacao import (
    ConexaoResumo,
    ContaMonitorada,
    PainelModeracao,
    RegistroAuditoria,
    ResumoModeracao,
)
from backend.domain.usuario import (
    PAPEL_ADMIN,
    STATUS_ADVERTIDA,
    STATUS_ATIVA,
    STATUS_BANIDA,
    STATUS_SUSPENSA,
    Usuario,
    normalizar_email,
)
from backend.infrastructure.banco.models import (
    AnaliseIAModel,
    ContaVinculadaModel,
    ProdutoModel,
    RegistroAuditoriaModel,
    User,
    VendedorModel,
)
from backend.infrastructure.banco.repositorio_usuarios import _montar_usuario
from backend.infrastructure.database import SessionLocal


class RepositorioModeracaoSQL:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory

    def registrar_auditoria(
        self,
        admin_id: int | None,
        admin_email: str,
        alvo_id: int | None,
        alvo_identificador: str,
        acao: str,
        motivo: str | None = None,
        detalhes: dict[str, Any] | None = None,
        criado_em: datetime | None = None,
    ) -> RegistroAuditoria:
        agora = criado_em or datetime.now(UTC)
        with self._session_factory() as session:
            reg = RegistroAuditoriaModel(
                admin_id=admin_id,
                admin_email=normalizar_email(admin_email),
                alvo_id=alvo_id,
                alvo_identificador=alvo_identificador.strip(),
                acao=acao.strip(),
                motivo=motivo.strip() if motivo else None,
                detalhes=detalhes or {},
                criado_em=agora,
            )
            session.add(reg)
            session.commit()
            return RegistroAuditoria(
                id=reg.id,
                admin_id=reg.admin_id,
                admin_email=reg.admin_email,
                alvo_id=reg.alvo_id,
                alvo_identificador=reg.alvo_identificador,
                acao=reg.acao,
                motivo=reg.motivo,
                detalhes=reg.detalhes,
                criado_em=reg.criado_em,
            )

    def listar_auditoria(self, limite: int = 50) -> list[RegistroAuditoria]:
        with self._session_factory() as session:
            registros = (
                session.query(RegistroAuditoriaModel)
                .order_by(desc(RegistroAuditoriaModel.criado_em))
                .limit(limite)
                .all()
            )
            return [
                RegistroAuditoria(
                    id=r.id,
                    admin_id=r.admin_id,
                    admin_email=r.admin_email,
                    alvo_id=r.alvo_id,
                    alvo_identificador=r.alvo_identificador,
                    acao=r.acao,
                    motivo=r.motivo,
                    detalhes=r.detalhes,
                    criado_em=r.criado_em,
                )
                for r in registros
            ]

    def obter_painel(
        self,
        filtro_status: str = "todos",
        busca: str = "",
        limite: int = 100,
        agora: datetime | None = None,
    ) -> PainelModeracao:
        momento = agora or datetime.now(UTC)
        busca_limpa = normalizar_email(busca)

        with self._session_factory() as session:
            todos_users = session.query(User).order_by(desc(User.id)).all()
            total_conexoes = session.query(func.count(ContaVinculadaModel.vendedor_id)).scalar() or 0

            contas_monitoradas: list[ContaMonitorada] = []
            resumo_ativas = 0
            resumo_advertidas = 0
            resumo_suspensas = 0
            resumo_banidas = 0
            resumo_sessoes = 0

            # Carrega relações em lote para manter performance sem N+1 queries
            conexoes_por_vendedor: dict[int, list[ConexaoResumo]] = {}
            for c in session.query(ContaVinculadaModel).all():
                conexoes_por_vendedor.setdefault(c.vendedor_id, []).append(
                    ConexaoResumo(marketplace=c.marketplace, apelido=c.apelido, conectada_em=c.conectada_em)
                )

            produtos_por_vendedor: dict[int, int] = dict(
                session.query(ProdutoModel.vendedor_id, func.count(ProdutoModel.id))
                .group_by(ProdutoModel.vendedor_id)
                .all()
            )

            analises_por_vendedor: dict[int, int] = dict(
                session.query(AnaliseIAModel.vendedor_id, func.count(AnaliseIAModel.id))
                .group_by(AnaliseIAModel.vendedor_id)
                .all()
            )

            for u in todos_users:
                montado = _montar_usuario(session, u)
                if montado is None:
                    continue
                usuario, _ = montado
                status_efetivo = usuario.status_efetivo(momento)
                sessao_ativa = usuario.sessao_ativa(momento)

                if status_efetivo == STATUS_ATIVA:
                    resumo_ativas += 1
                elif status_efetivo == STATUS_ADVERTIDA:
                    resumo_advertidas += 1
                elif status_efetivo == STATUS_SUSPENSA:
                    resumo_suspensas += 1
                elif status_efetivo == STATUS_BANIDA:
                    resumo_banidas += 1

                if sessao_ativa:
                    resumo_sessoes += 1

                # Filtro por busca (email, nome, loja ou id)
                bate_busca = True
                if busca_limpa:
                    texto_completo = f"{usuario.id} {usuario.email} {usuario.nome} {usuario.loja}".lower()
                    bate_busca = busca_limpa in texto_completo

                # Filtro por status
                bate_status = True
                if filtro_status == "online":
                    bate_status = sessao_ativa
                elif filtro_status == "admin":
                    bate_status = usuario.eh_admin
                elif filtro_status in {STATUS_ADVERTIDA, STATUS_SUSPENSA, STATUS_BANIDA}:
                    bate_status = status_efetivo == filtro_status

                if bate_busca and bate_status:
                    conexoes = tuple(conexoes_por_vendedor.get(usuario.id, []))
                    contas_monitoradas.append(
                        ContaMonitorada(
                            usuario=usuario,
                            status_efetivo=status_efetivo,
                            sessao_ativa=sessao_ativa,
                            usa_google=bool(u.google_id),
                            criado_em=u.criado_em,
                            marketplaces_conectados=conexoes,
                            total_produtos=produtos_por_vendedor.get(usuario.id, 0),
                            total_analises_ia=analises_por_vendedor.get(usuario.id, 0),
                        )
                    )

            resumo = ResumoModeracao(
                total_contas=len(todos_users),
                sessoes_ativas=resumo_sessoes,
                contas_advertidas=resumo_advertidas,
                contas_suspensas=resumo_suspensas,
                contas_banidas=resumo_banidas,
                conexoes_ativas=total_conexoes,
            )

            return PainelModeracao(
                resumo=resumo,
                contas=contas_monitoradas[:limite],
                total_filtrado=len(contas_monitoradas),
            )
