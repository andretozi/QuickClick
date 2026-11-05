"""
Infraestrutura · Repositório de Usuários via SQLAlchemy (Azure PostgreSQL).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.domain.erros import CredenciaisInvalidas, EmailJaCadastrado, VendedorNaoEncontrado
from backend.domain.usuario import Usuario, normalizar_email
from backend.infrastructure.banco.models import (
    AiUsage,
    AnaliseIAModel,
    ContaVinculadaModel,
    MarketplaceToken,
    ProdutoModel,
    PublicacaoModel,
    User,
    UsoIAModel,
    VendedorModel,
)
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
        tem_senha=bool(user.password_hash),
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
        email_normalizado = normalizar_email(email)
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

    def atualizar_perfil(self, user_id: int, nome: str, email: str, loja: str) -> Usuario:
        email_normalizado = normalizar_email(email)
        nome_limpo = nome.strip()
        loja_limpa = loja.strip()
        with self._session_factory() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user is None:
                raise VendedorNaoEncontrado(user_id)

            conflito = session.query(User).filter(User.email == email_normalizado, User.id != user_id).first()
            if conflito is not None:
                raise EmailJaCadastrado()

            user.email = email_normalizado
            user.nome = nome_limpo
            user.loja = loja_limpa
            user.store_name = loja_limpa or None

            vendedor = session.query(VendedorModel).filter_by(id=user_id).first()
            if vendedor is not None:
                vendedor.nome = nome_limpo or loja_limpa or email_normalizado

            try:
                session.commit()
            except IntegrityError as erro:
                session.rollback()
                raise EmailJaCadastrado() from erro

            montado = _montar_usuario(session, user)
            assert montado is not None
            return montado[0]

    def atualizar_senha(self, user_id: int, password_hash: str) -> None:
        with self._session_factory() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user is None:
                raise VendedorNaoEncontrado(user_id)
            user.password_hash = password_hash
            session.commit()

    def remover(self, user_id: int) -> None:
        """Elimina definitivamente o usuário e seus registros vinculados (conformidade LGPD)."""
        with self._session_factory() as session:
            session.query(PublicacaoModel).filter_by(vendedor_id=user_id).delete(synchronize_session=False)
            session.query(ProdutoModel).filter_by(vendedor_id=user_id).delete(synchronize_session=False)
            session.query(UsoIAModel).filter_by(vendedor_id=user_id).update(
                {"vendedor_id": None, "analise_id": None}, synchronize_session=False
            )
            session.query(AnaliseIAModel).filter_by(vendedor_id=user_id).delete(synchronize_session=False)
            session.query(ContaVinculadaModel).filter_by(vendedor_id=user_id).delete(synchronize_session=False)
            session.query(MarketplaceToken).filter_by(user_id=user_id).delete(synchronize_session=False)
            session.query(AiUsage).filter_by(user_id=user_id).delete(synchronize_session=False)
            session.query(VendedorModel).filter_by(id=user_id).delete(synchronize_session=False)
            session.query(User).filter_by(id=user_id).delete(synchronize_session=False)
            session.commit()

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
        email_normalizado = normalizar_email(email)
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

            montado = _montar_usuario(session, user)
            assert montado is not None
            return montado[0]
