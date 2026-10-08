"""Aplicação · Resumo do vendedor: plano, quantos marketplaces estão conectados e se cabe mais um."""

from dataclasses import dataclass

from backend.application.casos_de_uso.comum import obter_vendedor
from backend.application.portas import RepositorioContasVinculadas, RepositorioVendedores
from backend.domain.plano import Plano, plano_para_mais_marketplaces
from backend.domain.vendedor import Vendedor


@dataclass(frozen=True)
class ResumoDoVendedor:
    vendedor: Vendedor
    marketplaces_conectados: int
    pode_conectar_mais: bool
    plano_para_mais_marketplaces: Plano | None  # quem conecta mais (do Grátis e do Essencial, o Pro)


class ObterVendedorAtual:
    def __init__(self, vendedores: RepositorioVendedores, contas: RepositorioContasVinculadas):
        self._vendedores = vendedores
        self._contas = contas

    def executar(self, vendedor_id: int) -> ResumoDoVendedor:
        vendedor = obter_vendedor(self._vendedores, vendedor_id)
        conectados = len(self._contas.listar_do_vendedor(vendedor_id))
        return ResumoDoVendedor(
            vendedor=vendedor,
            marketplaces_conectados=conectados,
            pode_conectar_mais=vendedor.plano.permite_conectar(conectados),
            plano_para_mais_marketplaces=plano_para_mais_marketplaces(vendedor.plano),
        )
