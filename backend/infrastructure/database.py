"""
Infraestrutura · Conexão com o banco (Azure Database for PostgreSQL, db-quickclick).

O engine nasce na primeira utilização, depois que a configuração carregou, e não na
importação do módulo. A URL vem do módulo de configuração (DATABASE_URL). As tabelas
são criadas e alteradas só pelas migrações do Alembic (backend/infrastructure/banco/migracoes).
"""

import threading
from urllib.parse import urlsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.domain.erros import ServicoIndisponivel
from backend.infrastructure.configuracao import configuracao, database_url

Base = declarative_base()

# Sem limite, cada tentativa espera o timeout de TCP do sistema (21 s no Windows, ~127 s no
# Linux do App Service) quando o firewall do Postgres descarta a conexão. Duas tentativas na
# partida passam dos 230 s que o App Service espera o container responder, e ele dá 503.
TIMEOUT_CONEXAO_S = 10

# O Flexible Server B1ms aceita poucas conexões: o pool fica pequeno.
POOL_SIZE = 5
MAX_OVERFLOW = 5

HOST_DO_BANCO_REAL = "postgres.database.azure.com"

_trava = threading.Lock()
_engine = None
_fabrica: sessionmaker | None = None
_trava_de_testes = False


def ativar_trava_de_testes() -> None:
    """Chamado pelos testes: daqui em diante, criar um engine para o banco real é erro."""
    global _trava_de_testes
    _trava_de_testes = True


def _conferir_trava_de_testes(url: str) -> None:
    if _trava_de_testes and HOST_DO_BANCO_REAL in (urlsplit(url).hostname or ""):
        raise RuntimeError(
            "Teste tentou usar o banco real (postgres.database.azure.com). "
            "Os testes usam SQLite em memória ou repositórios falsos."
        )


def criar_engine(url: str, timeout_s: int = TIMEOUT_CONEXAO_S):
    """Engine do Postgres com pool_pre_ping e limite de tempo para abrir cada conexão."""
    _conferir_trava_de_testes(url)
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        connect_args={"connect_timeout": timeout_s},
    )


def obter_engine():
    """O engine do processo, criado na primeira chamada."""
    global _engine, _fabrica
    with _trava:
        if _engine is None:
            url = database_url(configuracao())
            if url is None:
                raise ServicoIndisponivel(
                    "O banco de dados não está configurado neste computador. "
                    "Rode python -m scripts.verificar_config para ver o que falta."
                )
            _engine = criar_engine(url)
            _fabrica = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        return _engine


def SessionLocal() -> Session:  # noqa: N802 (nome mantido: é a fábrica padrão dos repositórios)
    """Uma sessão nova no banco do processo (o engine nasce aqui, na primeira vez)."""
    obter_engine()
    return _fabrica()


def get_db():
    """Gerador de sessão do SQLAlchemy para injeção de dependência."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
