"""
Modelos ORM (SQLAlchemy) para o banco de dados Azure PostgreSQL.
Localizados na camada de infraestrutura para preservar a pureza da camada de domínio.

As tabelas nascem e mudam só pelas migrações do Alembic (banco/migracoes), sempre aditivas.
JSON vira JSONB no Postgres e JSON no SQLite dos testes.
"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB

from backend.infrastructure.database import Base

Json = JSON().with_variant(JSONB(), "postgresql")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # O banco de produção nasceu com email e password_hash aceitando vazio; o cadastro sempre preenche os dois
    email = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=True)
    nome = Column(String, nullable=True)
    loja = Column(String, nullable=True)
    criado_em = Column(String, nullable=True)
    confirmou_maioridade_em = Column(String, nullable=True)  # ISO, gravado no cadastro


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
    access_token = Column(String, nullable=False)  # cifrado: "enc:v1:..."
    refresh_token = Column(String, nullable=False)  # cifrado: "enc:v1:..."
    token_expira_em = Column(String, nullable=False)
    conta_externa_id = Column(String, nullable=True)
    apelido = Column(String, nullable=True)


class AnaliseIAModel(Base):
    """Uma análise da IA no criar anúncio. Guarda os resultados de cada etapa, nunca as fotos."""

    __tablename__ = "ia_analises"

    id = Column(String(36), primary_key=True)
    vendedor_id = Column(Integer, ForeignKey("vendedores.id", ondelete="CASCADE"), nullable=False)
    plano_no_momento = Column(String(20), nullable=False)
    nivel = Column(String(10), nullable=False)  # gratis | pago
    status = Column(String(30), nullable=False)
    etapa_atual = Column(String(30), nullable=True)
    fotos_meta = Column(Json, nullable=True)  # por foto: qualidade, largura e altura
    leitura = Column(Json, nullable=True)
    atributos_confirmados = Column(Json, nullable=True)
    ml_categoria_id = Column(String(40), nullable=True)
    pesquisa_chave = Column(String(200), nullable=True)
    preco = Column(Json, nullable=True)
    texto = Column(Json, nullable=True)
    canais = Column(Json, nullable=True)
    avisos = Column(Json, nullable=True)  # mensagens para a tela (ex.: orçamento do dia, foto escura)
    erro_codigo = Column(String(60), nullable=True)
    erro_mensagem_usuario = Column(String(500), nullable=True)
    criado_em = Column(DateTime(timezone=True), nullable=False)
    atualizado_em = Column(DateTime(timezone=True), nullable=False)
    concluida_em = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_ia_analises_vendedor_criado", "vendedor_id", "criado_em"),
        Index("ix_ia_analises_status", "status"),
    )


class UsoIAModel(Base):
    """Uma chamada a um provedor de IA: tokens, cache, buscas, custo estimado e tempo."""

    __tablename__ = "ia_uso"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vendedor_id = Column(Integer, ForeignKey("vendedores.id", ondelete="SET NULL"), nullable=True)
    analise_id = Column(String(36), ForeignKey("ia_analises.id", ondelete="SET NULL"), nullable=True)
    etapa = Column(String(30), nullable=False)
    provedor = Column(String(20), nullable=False)
    modelo = Column(String(60), nullable=False)
    versao_prompt = Column(String(40), nullable=True)
    tokens_entrada = Column(Integer, nullable=False, default=0)
    tokens_saida = Column(Integer, nullable=False, default=0)
    cache_lido = Column(Integer, nullable=False, default=0)
    cache_gravado = Column(Integer, nullable=False, default=0)
    buscas_web = Column(Integer, nullable=False, default=0)
    custo_estimado_usd = Column(Numeric(12, 6), nullable=False, default=0)
    duracao_ms = Column(Integer, nullable=False, default=0)
    criado_em = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_ia_uso_criado", "criado_em"),
        Index("ix_ia_uso_analise", "analise_id"),
    )


class PesquisaMercadoModel(Base):
    """Cache da pesquisa de mercado (perfil do comprador) por categoria ou produto e condição."""

    __tablename__ = "pesquisas_mercado"

    chave = Column(String(200), primary_key=True)
    conteudo = Column(Json, nullable=False)
    fontes = Column(Json, nullable=True)
    criado_em = Column(DateTime(timezone=True), nullable=False)
    expira_em = Column(DateTime(timezone=True), nullable=False)


class CategoriaMLCacheModel(Base):
    """Cache dos atributos de uma categoria do Mercado Livre (24 horas)."""

    __tablename__ = "ml_categorias_cache"

    categoria_id = Column(String(40), primary_key=True)
    atributos = Column(Json, nullable=False)
    expira_em = Column(DateTime(timezone=True), nullable=False)
