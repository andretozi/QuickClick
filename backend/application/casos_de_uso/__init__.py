"""Aplicação · Casos de uso: o que o vendedor faz no sistema, um por arquivo."""

from dataclasses import dataclass

from backend.application.casos_de_uso.conectar_marketplace import ConectarMarketplace
from backend.application.casos_de_uso.desconectar_marketplace import DesconectarMarketplace
from backend.application.casos_de_uso.listar_marketplaces import ListarMarketplaces
from backend.application.casos_de_uso.listar_planos import ListarPlanos
from backend.application.casos_de_uso.obter_vendedor_atual import ObterVendedorAtual


@dataclass(frozen=True)
class CasosDeUso:
    """Todos os casos de uso já montados, entregues à apresentação pela raiz (app)."""

    listar_planos: ListarPlanos
    obter_vendedor_atual: ObterVendedorAtual
    listar_marketplaces: ListarMarketplaces
    conectar_marketplace: ConectarMarketplace
    desconectar_marketplace: DesconectarMarketplace
