"""
Raiz de composição do back.

Liga as camadas e devolve a aplicação FastAPI pronta: a API em /api e o front
buildado (frontend/dist) no resto dos endereços. O main.py chama criar_app().
"""

from pathlib import Path

from fastapi import FastAPI

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
from backend.infrastructure.banco.repositorio_contas import RepositorioContasVinculadasSQLite
from backend.infrastructure.banco.repositorio_vendedores import RepositorioVendedoresSQLite
from backend.infrastructure.banco.sqlite import BancoSQLite
from backend.infrastructure.config import Config, carregar_config
from backend.infrastructure.marketplaces.registro import criar_gateways
from backend.presentation.http.api import criar_api
from backend.presentation.http.front import montar_front

RAIZ_DO_PROJETO = Path(__file__).resolve().parents[2]

# Ainda não existe login de verdade: todo pedido é do vendedor de demonstração,
# com o plano escolhido no .env (QUICKCLICK_PLANO_DEMO, Grátis por padrão).
ID_VENDEDOR_DEMO = 1
NOME_VENDEDOR_DEMO = "Vendedor de demonstração"


def criar_app(config: Config | None = None) -> FastAPI:
    config = config or carregar_config(RAIZ_DO_PROJETO)

    plano_demo = buscar_plano(config.plano_demo)
    if plano_demo is None:
        validos = ", ".join(plano.slug for plano in PLANOS)
        raise ValueError(f"QUICKCLICK_PLANO_DEMO inválido: {config.plano_demo!r}. Use um destes: {validos}.")

    banco = BancoSQLite(config.caminho_banco)
    banco.criar_tabelas()
    vendedores = RepositorioVendedoresSQLite(banco)
    contas = RepositorioContasVinculadasSQLite(banco)
    vendedores.salvar(Vendedor(id=ID_VENDEDOR_DEMO, nome=NOME_VENDEDOR_DEMO, plano=plano_demo))

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
