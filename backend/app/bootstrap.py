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
    AutenticarUsuario,
    CasosDeUso,
    ConectarMarketplace,
    DesconectarMarketplace,
    ListarMarketplaces,
    ListarPlanos,
    ObterUsuarioAtual,
    ObterVendedorAtual,
    RegistrarUsuario,
)
from backend.infrastructure.banco import models  # noqa: F401
from backend.infrastructure.banco.repositorio_contas import RepositorioContasVinculadasSQL
from backend.infrastructure.banco.repositorio_usuarios import RepositorioUsuariosSQL
from backend.infrastructure.banco.repositorio_vendedores import RepositorioVendedoresSQL
from backend.infrastructure.config import Config, carregar_config
from backend.infrastructure.database import Base, SessionLocal, engine
from backend.infrastructure.marketplaces.registro import criar_gateways
from backend.infrastructure.seguranca.hasher import HasherPBKDF2
from backend.infrastructure.seguranca.token_jwt import ServicoJWT
from backend.presentation.http.api import criar_api
from backend.presentation.http.front import montar_front

RAIZ_DO_PROJETO = Path(__file__).resolve().parents[2]


def criar_app(
    config: Config | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
    identificar_vendedor=None,
) -> FastAPI:
    config = config or carregar_config(RAIZ_DO_PROJETO)

    # Cria as tabelas no Azure PostgreSQL apenas na inicialização padrão do sistema
    if engine is not None and session_factory is SessionLocal:
        try:
            Base.metadata.create_all(bind=engine)
        except Exception as erro:
            print(f"[banco] Aviso: não foi possível conectar ao Azure PostgreSQL ({erro}). "
                  "Verifique o DATABASE_URL ou AZURE_DB_* no arquivo .env.")

    vendedores = RepositorioVendedoresSQL(session_factory)
    contas = RepositorioContasVinculadasSQL(session_factory)
    usuarios = RepositorioUsuariosSQL(session_factory)

    hasher = HasherPBKDF2()
    token_service = ServicoJWT()

    casos = CasosDeUso(
        listar_planos=ListarPlanos(),
        obter_vendedor_atual=ObterVendedorAtual(vendedores, contas),
        listar_marketplaces=ListarMarketplaces(contas),
        conectar_marketplace=ConectarMarketplace(vendedores, contas, criar_gateways()),
        desconectar_marketplace=DesconectarMarketplace(contas),
        autenticar_usuario=AutenticarUsuario(usuarios, hasher, token_service),
        registrar_usuario=RegistrarUsuario(usuarios, hasher, token_service),
        obter_usuario_atual=ObterUsuarioAtual(usuarios),
    )

    app = criar_api(casos, identificar_vendedor=identificar_vendedor, servico_token=token_service)
    montar_front(app, config.pasta_front)
    return app
