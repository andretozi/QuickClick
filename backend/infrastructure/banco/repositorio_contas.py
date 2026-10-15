"""Infraestrutura · Contas vinculadas no banco via SQLAlchemy (Azure PostgreSQL)."""

from collections.abc import Callable
from datetime import datetime
from sqlalchemy.orm import Session

from backend.domain.conta_vinculada import ContaVinculada, CredenciaisOAuth
from backend.infrastructure.banco.models import ContaVinculadaModel
from backend.infrastructure.database import SessionLocal


def _para_conta(linha: ContaVinculadaModel) -> ContaVinculada:
    return ContaVinculada(
        vendedor_id=linha.vendedor_id,
        marketplace=linha.marketplace,
        conectada_em=datetime.fromisoformat(linha.conectada_em),
        credenciais=CredenciaisOAuth(
            access_token=linha.access_token,
            refresh_token=linha.refresh_token,
            expira_em=datetime.fromisoformat(linha.token_expira_em),
        ),
    )


class RepositorioContasVinculadasSQL:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory

    def listar_do_vendedor(self, vendedor_id: int) -> list[ContaVinculada]:
        with self._session_factory() as session:
            linhas = (
                session.query(ContaVinculadaModel)
                .filter_by(vendedor_id=vendedor_id)
                .order_by(ContaVinculadaModel.conectada_em)
                .all()
            )
            return [_para_conta(linha) for linha in linhas]

    def buscar(self, vendedor_id: int, marketplace: str) -> ContaVinculada | None:
        with self._session_factory() as session:
            linha = (
                session.query(ContaVinculadaModel)
                .filter_by(vendedor_id=vendedor_id, marketplace=marketplace)
                .first()
            )
            return None if linha is None else _para_conta(linha)

    def salvar(self, conta: ContaVinculada) -> None:
        with self._session_factory() as session:
            linha = (
                session.query(ContaVinculadaModel)
                .filter_by(vendedor_id=conta.vendedor_id, marketplace=conta.marketplace)
                .first()
            )
            if linha is None:
                linha = ContaVinculadaModel(
                    vendedor_id=conta.vendedor_id,
                    marketplace=conta.marketplace,
                    conectada_em=conta.conectada_em.isoformat(),
                    access_token=conta.credenciais.access_token,
                    refresh_token=conta.credenciais.refresh_token,
                    token_expira_em=conta.credenciais.expira_em.isoformat(),
                )
                session.add(linha)
            else:
                linha.conectada_em = conta.conectada_em.isoformat()
                linha.access_token = conta.credenciais.access_token
                linha.refresh_token = conta.credenciais.refresh_token
                linha.token_expira_em = conta.credenciais.expira_em.isoformat()
            session.commit()

    def remover(self, vendedor_id: int, marketplace: str) -> None:
        with self._session_factory() as session:
            session.query(ContaVinculadaModel).filter_by(
                vendedor_id=vendedor_id, marketplace=marketplace
            ).delete()
            session.commit()


# Alias para retrocompatibilidade
RepositorioContasVinculadasSQLite = RepositorioContasVinculadasSQL
