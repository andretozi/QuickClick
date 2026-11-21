"""
Caso de uso · Gerenciar os produtos (anúncios da Quick Click) guardados no banco

O vendedor vem sempre do token. Produto de outro vendedor é tratado como inexistente (404, nunca 403).
"""

from collections.abc import Callable, Sequence
from datetime import datetime

from backend.application.portas import RepositorioDeProdutos, SincronizadorDeCanal
from backend.domain.erros import AnuncioNaoEncontrado
from backend.domain.produto import Produto

NAO_ENCONTRADO = "Não encontramos esse anúncio na sua conta."


class GerenciarProdutos:
    def __init__(
        self,
        produtos: RepositorioDeProdutos,
        relogio: Callable[[], datetime],
        *,
        sincronizadores: Sequence[SincronizadorDeCanal] = (),
    ):
        self._produtos = produtos
        self._relogio = relogio
        self._sincronizadores = tuple(sincronizadores)

    def listar(self, vendedor_id: int) -> list[Produto]:
        """Do mais recente ao mais antigo (última gravação)."""
        return self._produtos.listar(vendedor_id)

    def obter(self, vendedor_id: int, produto_id: str) -> Produto:
        produto = self._produtos.obter(vendedor_id, produto_id)
        if produto is None:
            raise AnuncioNaoEncontrado(NAO_ENCONTRADO)
        return produto

    def salvar(
        self,
        vendedor_id: int,
        produto: Produto,
        *,
        sincronizar_canais: bool = True,
        sincronizar_quickstore: bool = True,
    ) -> Produto:
        """Cria ou substitui. `produto.atualizado_em` é a versão que o navegador leu (409 se ficou velha)."""
        anterior = self._produtos.obter(vendedor_id, produto.id)
        agora = self._relogio()
        # A versão vai em milissegundos: o Date do navegador não guarda microssegundos e daria 409 à toa
        agora = agora.replace(microsecond=agora.microsecond // 1000 * 1000)
        salvo = self._produtos.salvar(vendedor_id, produto, agora)
        if sincronizar_canais and sincronizar_quickstore:
            for sincronizador in self._sincronizadores:
                sincronizador.sincronizar_ao_salvar(vendedor_id, anterior, salvo)
        return salvo

    def importar(self, vendedor_id: int, produto: Produto) -> bool:
        """Importação única do navegador: False quando o produto ou o item do canal já existe."""
        return self._produtos.importar(vendedor_id, produto)

    def remover(self, vendedor_id: int, produto_id: str) -> None:
        anterior = self._produtos.obter(vendedor_id, produto_id)
        if not self._produtos.remover(vendedor_id, produto_id):
            raise AnuncioNaoEncontrado(NAO_ENCONTRADO)
        if anterior is not None:
            for sincronizador in self._sincronizadores:
                sincronizador.sincronizar_ao_remover(vendedor_id, anterior)
