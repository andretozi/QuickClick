"""
Infraestrutura · Repositório de Usuários via SQLAlchemy (Azure PostgreSQL).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.domain.erros import CredenciaisInvalidas, EmailJaCadastrado
from backend.domain.usuario import Usuario
from backend.infrastructure.banco.models import User, VendedorModel
from backend.infrastructure.database import SessionLocal


def _montar_usuario(session: Session, user: User | None) -> tuple[Usuario, str | None] | None:
    if user is None:
        return None
    vendedor = session.query(VendedorModel).filter_by(id=user.id).first()
    plano = vendedor.plano if vendedor else "gratis"
    loja = user.store_name or user.loja or ""
    usuario = Usuario(
        id=user.id,
        email=user.email,
        nome=user.nome or "",
        loja=loja,
        plano=plano,
    )
    return usuario, user.password_hash


class RepositorioUsuariosSQL:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory

    def obter_por_id(self, user_id: int) -> tuple[Usuario, str | None] | None:
        with self._session_factory() as session:
            user = session.query(User).filter_by(id=user_id).first()
            return _montar_usuario(session, user)

    def obter_por_email(self, email: str) -> tuple[Usuario, str | None] | None:
        email_normalizado = email.strip().lower()
        with self._session_factory() as session:
            user = session.query(User).filter_by(email=email_normalizado).first()
            return _montar_usuario(session, user)

    def obter_por_google_id(self, google_id: str) -> tuple[Usuario, str | None] | None:
        google_id_limpo = google_id.strip()
        if not google_id_limpo:
            return None
        with self._session_factory() as session:
            user = session.query(User).filter_by(google_id=google_id_limpo).first()
            return _montar_usuario(session, user)

    def vincular_google_id(self, user_id: int, google_id: str) -> None:
        google_id_limpo = google_id.strip()
        if not google_id_limpo:
            return
        with self._session_factory() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user is None:
                return
            if user.google_id and user.google_id != google_id_limpo:
                raise CredenciaisInvalidas("Esta conta já está vinculada a outro login do Google.")
            if not user.google_id:
                user.google_id = google_id_limpo
                try:
                    session.commit()
                except IntegrityError as erro:
                    session.rollback()
                    raise CredenciaisInvalidas("Este login do Google já está vinculado a outra conta.") from erro

    def salvar(
        self,
        email: str,
        password_hash: str | None,
        nome: str,
        loja: str,
        plano: str = "gratis",
        confirmou_maioridade_em: str | None = None,
        google_id: str | None = None,
    ) -> Usuario:
        email_normalizado = email.strip().lower()
        nome_limpo = nome.strip()
        loja_limpa = loja.strip()
        google_id_limpo = google_id.strip() if google_id else None
        agora = datetime.now(UTC).isoformat()

        with self._session_factory() as session:
            user = session.query(User).filter_by(email=email_normalizado).first()
            if user is None:
                user = User(
                    email=email_normalizado,
                    criado_em=agora,
                )
                session.add(user)

            user.password_hash = password_hash
            user.nome = nome_limpo
            user.loja = loja_limpa
            user.store_name = loja_limpa or None
            if google_id_limpo is not None:
                user.google_id = google_id_limpo
            if confirmou_maioridade_em:
                user.confirmou_maioridade_em = confirmou_maioridade_em

            try:
                session.flush()

                vendedor = session.query(VendedorModel).filter_by(id=user.id).first()
                if vendedor is None:
                    vendedor = VendedorModel(id=user.id)
                    session.add(vendedor)
                vendedor.nome = nome_limpo or loja_limpa or email_normalizado
                vendedor.plano = plano

                session.commit()
            except IntegrityError as erro:
                session.rollback()
                raise EmailJaCadastrado() from erro

            return Usuario(
                id=user.id,
                email=user.email,
                nome=user.nome or "",
                loja=user.store_name or user.loja or "",
                plano=plano,
            )
