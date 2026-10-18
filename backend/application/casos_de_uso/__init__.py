"""Aplicação · Casos de uso: o que o vendedor faz no sistema, um por arquivo."""

from dataclasses import dataclass

from backend.application.casos_de_uso.autenticar_usuario import AutenticarUsuario, ResultadoAutenticacao
from backend.application.casos_de_uso.conectar_marketplace import ConectarMarketplace
from backend.application.casos_de_uso.desconectar_marketplace import DesconectarMarketplace
from backend.application.casos_de_uso.listar_marketplaces import ListarMarketplaces
from backend.application.casos_de_uso.listar_planos import ListarPlanos
from backend.application.casos_de_uso.obter_usuario_atual import ObterUsuarioAtual
from backend.application.casos_de_uso.obter_vendedor_atual import ObterVendedorAtual
from backend.application.casos_de_uso.publicar_no_mercado_livre import PublicarNoMercadoLivre
from backend.application.casos_de_uso.registrar_usuario import RegistrarUsuario
from backend.application.ia.servico import ServicoDeAnalises


@dataclass(frozen=True)
class CasosDeUso:
    """Todos os casos de uso já montados, entregues à apresentação pela raiz (app)."""

    listar_planos: ListarPlanos
    obter_vendedor_atual: ObterVendedorAtual
    listar_marketplaces: ListarMarketplaces
    conectar_marketplace: ConectarMarketplace
    desconectar_marketplace: DesconectarMarketplace
    autenticar_usuario: AutenticarUsuario | None = None
    registrar_usuario: RegistrarUsuario | None = None
    obter_usuario_atual: ObterUsuarioAtual | None = None
    analises_ia: ServicoDeAnalises | None = None
    publicar_no_mercado_livre: PublicarNoMercadoLivre | None = None
