"""
Modelos ORM (SQLAlchemy) para o banco de dados Azure PostgreSQL.
Localizados na camada de infraestrutura para preservar a pureza da camada de domínio.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from backend.infrastructure.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nome = Column(String, nullable=True)
    loja = Column(String, nullable=True)
    criado_em = Column(String, nullable=True)


class MarketplaceToken(Base):
    __tablename__ = "marketplace_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    access_token = Column(String)
    refresh_token = Column(String)


class AiUsage(Base):
    __tablename__ = "ai_usage"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    credits_left = Column(Integer, default=3)


class VendedorModel(Base):
    __tablename__ = "vendedores"

    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    plano = Column(String, nullable=False)


class ContaVinculadaModel(Base):
    __tablename__ = "contas_vinculadas"

    vendedor_id = Column(Integer, ForeignKey("vendedores.id", ondelete="CASCADE"), primary_key=True)
    marketplace = Column(String, primary_key=True)
    conectada_em = Column(String, nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    token_expira_em = Column(String, nullable=False)
