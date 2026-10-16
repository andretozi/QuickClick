"""
Infraestrutura · Repositório de Usuários via SQLAlchemy (Azure PostgreSQL).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from sqlalchemy.orm import Session

from backend.domain.usuario import Usuario
from backend.infrastructure.banco.models import User, VendedorModel
from backend.infrastructure.database import SessionLocal


class RepositorioUsuariosSQL:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory

    def obter_por_id(self, user_id: int) -> tuple[Usuario, str] | None:
        with self._session_factory() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user is None:
                return None
            vendedor = session.query(VendedorModel).filter_by(id=user.id).first()
            plano = vendedor.plano if vendedor else "gratis"
            usuario = Usuario(
                id=user.id,
                email=user.email,
                nome=user.nome or "",
                loja=user.loja or "",
                plano=plano,
            )
            return usuario, user.password_hash

    def obter_por_email(self, email: str) -> tuple[Usuario, str] | None:
        email_normalizado = email.strip().lower()
        with self._session_factory() as session:
            user = session.query(User).filter_by(email=email_normalizado).first()
            if user is None:
                return None
            vendedor = session.query(VendedorModel).filter_by(id=user.id).first()
            plano = vendedor.plano if vendedor else "gratis"
            usuario = Usuario(
                id=user.id,
                email=user.email,
                nome=user.nome or "",
                loja=user.loja or "",
                plano=plano,
            )
            return usuario, user.password_hash

    def salvar(
        self,
        email: str,
        password_hash: str,
        nome: str,
        loja: str,
        plano: str = "gratis",
    ) -> Usuario:
        email_normalizado = email.strip().lower()
        agora = datetime.now(UTC).isoformat()
        with self._session_factory() as session:
            user = session.query(User).filter_by(email=email_normalizado).first()
            if user is None:
                user = User(
                    email=email_normalizado,
                    password_hash=password_hash,
                    nome=nome.strip(),
                    loja=loja.strip(),
                    criado_em=agora,
                )
                session.add(user)
                session.flush()

                vendedor = session.query(VendedorModel).filter_by(id=user.id).first()
                if vendedor is not None:
                    vendedor.nome = nome.strip() or email_normalizado
                    vendedor.plano = plano
                else:
                    vendedor = VendedorModel(
                        id=user.id,
                        nome=nome.strip() or email_normalizado,
                        plano=plano,
                    )
                    session.add(vendedor)
            else:
                user.password_hash = password_hash
                user.nome = nome.strip()
                user.loja = loja.strip()
                vendedor = session.query(VendedorModel).filter_by(id=user.id).first()
                if vendedor is not None:
                    vendedor.nome = nome.strip() or email_normalizado
                    vendedor.plano = plano
                else:
                    session.add(VendedorModel(id=user.id, nome=nome.strip(), plano=plano))

            session.commit()
            return Usuario(
                id=user.id,
                email=user.email,
                nome=user.nome or "",
                loja=user.loja or "",
                plano=plano,
            )
