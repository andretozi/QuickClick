"""
Raiz de composição do back.

Liga as camadas e devolve a aplicação FastAPI pronta: a API em /api e o front
buildado (frontend/dist) no resto dos endereços. O main.py chama criar_app().
Persistência conectada diretamente ao Azure Database for PostgreSQL.
"""

from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.orm import Session

from backend.application.casos_de_uso import (
    CasosDeUso,
    ConectarMarketplace,
    DesconectarMarketplace,
    ListarMarketplaces,
    ListarPlanos,
    ObterVendedorAtual,
)
from backend.domain.plano import PLANOS, buscar_plano
from backend.domain.vendedor import Vendedor
from backend.infrastructure.banco import models  # noqa: F401
from backend.infrastructure.banco.repositorio_contas import RepositorioContasVinculadasSQL
from backend.infrastructure.banco.repositorio_vendedores import RepositorioVendedoresSQL
from backend.infrastructure.config import Config, carregar_config
from backend.infrastructure.database import Base, SessionLocal, engine
from backend.infrastructure.marketplaces.registro import criar_gateways
from backend.presentation.http.api import criar_api
from backend.presentation.http.front import montar_front

RAIZ_DO_PROJETO = Path(__file__).resolve().parents[2]

# Ainda não existe login de verdade: todo pedido é do vendedor de demonstração,
# com o plano escolhido no .env (QUICKCLICK_PLANO_DEMO, Grátis por padrão).
ID_VENDEDOR_DEMO = 1
NOME_VENDEDOR_DEMO = "Vendedor de demonstração"


def criar_app(
    config: Config | None = None,
    session_factory: Callable[[], Session] | None = None,
) -> FastAPI:
    config = config or carregar_config(RAIZ_DO_PROJETO)
    session_factory = session_factory or SessionLocal

    # Sincroniza automaticamente as tabelas no Azure PostgreSQL
    if session_factory is SessionLocal:
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as erro:
            print(f"[banco] Aviso: não foi possível conectar ao Azure PostgreSQL ({erro}). "
                  "Verifique o DATABASE_URL ou AZURE_DB_* no arquivo .env.")

    plano_demo = buscar_plano(config.plano_demo)
    if plano_demo is None:
        validos = ", ".join(plano.slug for plano in PLANOS)
        raise ValueError(f"QUICKCLICK_PLANO_DEMO inválido: {config.plano_demo!r}. Use um destes: {validos}.")

    vendedores = RepositorioVendedoresSQL(session_factory)
    contas = RepositorioContasVinculadasSQL(session_factory)
    try:
        vendedores.salvar(Vendedor(id=ID_VENDEDOR_DEMO, nome=NOME_VENDEDOR_DEMO, plano=plano_demo))
    except Exception as erro:
        print(f"[banco] Aviso: vendedor demo não inicializado no Azure ({erro}).")

    casos = CasosDeUso(
        listar_planos=ListarPlanos(),
        obter_vendedor_atual=ObterVendedorAtual(vendedores, contas),
        listar_marketplaces=ListarMarketplaces(contas),
        conectar_marketplace=ConectarMarketplace(vendedores, contas, criar_gateways()),
        desconectar_marketplace=DesconectarMarketplace(contas),
    )

    app = criar_api(casos, identificar_vendedor=lambda: ID_VENDEDOR_DEMO)
    montar_front(app, config.pasta_front)
    return app
