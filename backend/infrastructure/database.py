"""
Infraestrutura · Conexão com o Banco de Dados Azure PostgreSQL.

Configurado especificamente para o servidor do Azure:
db-quickclick.postgres.database.azure.com

As variáveis são obtidas diretamente do ambiente da Azure (Application Settings / Environment Variables).
"""

import os
from pathlib import Path
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base

# Carrega .env somente se o arquivo existir fisicamente (na Azure, o os.environ já é injetado pelo portal)
_raiz = Path(__file__).resolve().parents[2]
if (_raiz / ".env").is_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(_raiz / ".env")
    except ImportError:
        pass
elif (_raiz / "backend" / ".env").is_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(_raiz / "backend" / ".env")
    except ImportError:
        pass


def normalizar_url_postgres(url: str) -> str:
    """Normaliza o esquema da URL para compatibilidade com SQLAlchemy e drivers psycopg/psycopg2."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def obter_database_url() -> str:
    """
    Retorna a URL de conexão para o PostgreSQL no Azure.
    Lê diretamente das variáveis de ambiente injetadas pelo Azure App Service / Web App:
      1. DATABASE_URL (Application Settings ou Environment Variables)
      2. POSTGRESQLCONNSTR_DATABASE_URL (se adicionado na aba Connection Strings do Azure)
      3. Variáveis individuais: AZURE_DB_USER, AZURE_DB_PASSWORD, etc.
    """
    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRESQLCONNSTR_DATABASE_URL")
        or os.getenv("AZURE_POSTGRESQL_CONNECTIONSTRING")
    )
    if url:
        return normalizar_url_postgres(url)

    # Variáveis individuais no Azure App Service
    user = os.getenv("AZURE_DB_USER") or os.getenv("DB_USER")
    password = os.getenv("AZURE_DB_PASSWORD") or os.getenv("DB_PASSWORD")
    host = os.getenv("AZURE_DB_HOST") or os.getenv("DB_HOST", "db-quickclick.postgres.database.azure.com")
    port = os.getenv("AZURE_DB_PORT") or os.getenv("DB_PORT", "5432")
    db = os.getenv("AZURE_DB_NAME") or os.getenv("DB_NAME", "postgres")

    if user and password:
        user_enc = quote_plus(user)
        pass_enc = quote_plus(password)
        return f"postgresql+psycopg2://{user_enc}:{pass_enc}@{host}:{port}/{db}?sslmode=require"

    # Template padrão para o servidor Azure
    return f"postgresql+psycopg2://seu_usuario:sua_senha@{host}:{port}/{db}?sslmode=require"


DATABASE_URL = obter_database_url()

# Sem limite, cada tentativa espera o timeout de TCP do sistema (21 s no Windows, ~127 s no
# Linux do App Service) quando o firewall do Postgres descarta a conexão. Duas tentativas na
# partida passam dos 230 s que o App Service espera o container responder, e ele dá 503.
TIMEOUT_CONEXAO_S = 10


def criar_engine(url: str, timeout_s: int = TIMEOUT_CONEXAO_S):
    """Engine do Postgres com pool_pre_ping e limite de tempo para abrir cada conexão."""
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args={"connect_timeout": timeout_s},
    )


# Engine conectada diretamente ao Azure PostgreSQL
engine = criar_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Gerador de sessão do SQLAlchemy para injeção de dependência."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
