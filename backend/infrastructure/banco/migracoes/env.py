"""
Ambiente do Alembic. A URL vem de config.attributes["url"] (passada pelo migrador) ou do
módulo de configuração (DATABASE_URL); uma conexão aberta pode vir em attributes["connection"].
"""

from alembic import context

from backend.infrastructure.banco import models  # noqa: F401 (registra as tabelas no Base)
from backend.infrastructure.configuracao import configuracao, database_url
from backend.infrastructure.database import Base, criar_engine

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    url = config.attributes.get("url") or database_url(configuracao())
    if not url:
        raise RuntimeError("Falta DATABASE_URL: rode python -m scripts.verificar_config para ver o que falta.")
    return url


def rodar_offline() -> None:
    """Gera o SQL sem conectar (alembic upgrade --sql)."""
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def rodar_online() -> None:
    conexao = config.attributes.get("connection")
    if conexao is not None:
        context.configure(connection=conexao, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = criar_engine(_url())
    try:
        with engine.connect() as conexao:
            context.configure(connection=conexao, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    rodar_offline()
else:
    rodar_online()
