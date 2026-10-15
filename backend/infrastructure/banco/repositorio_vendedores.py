"""Infraestrutura · Vendedores no banco de dados via SQLAlchemy (Azure PostgreSQL)."""

from collections.abc import Callable
from sqlalchemy.orm import Session

from backend.domain.plano import buscar_plano
from backend.domain.vendedor import Vendedor
from backend.infrastructure.banco.models import VendedorModel
from backend.infrastructure.database import SessionLocal


class RepositorioVendedoresSQL:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory

    def obter(self, vendedor_id: int) -> Vendedor | None:
        with self._session_factory() as session:
            linha = session.query(VendedorModel).filter_by(id=vendedor_id).first()
            if linha is None:
                return None
            plano = buscar_plano(linha.plano)
            if plano is None:
                raise ValueError(f"Plano desconhecido no banco para o vendedor {vendedor_id}: {linha.plano!r}")
            return Vendedor(id=linha.id, nome=linha.nome, plano=plano)

    def salvar(self, vendedor: Vendedor) -> None:
        with self._session_factory() as session:
            linha = session.query(VendedorModel).filter_by(id=vendedor.id).first()
            if linha is None:
                linha = VendedorModel(id=vendedor.id, nome=vendedor.nome, plano=vendedor.plano.slug)
                session.add(linha)
            else:
                linha.nome = vendedor.nome
                linha.plano = vendedor.plano.slug
            session.commit()


# Alias para retrocompatibilidade caso alguém importe pelo nome antigo
RepositorioVendedoresSQLite = RepositorioVendedoresSQL
