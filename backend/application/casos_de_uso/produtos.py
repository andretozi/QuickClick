"""
Caso de uso · Gerenciar os produtos (anúncios da Quick Click) guardados no banco

O vendedor vem sempre do token. Produto de outro vendedor é tratado como inexistente (404, nunca 403).
"""

from collections.abc import Callable
from datetime import datetime

from backend.application.portas import RepositorioDeProdutos
from backend.domain.erros import AnuncioNaoEncontrado
from backend.domain.produto import Produto

NAO_ENCONTRADO = "Não encontramos esse anúncio na sua conta."


class GerenciarProdutos:
    def __init__(self, produtos: RepositorioDeProdutos, relogio: Callable[[], datetime]):
        self._produtos = produtos
        self._relogio = relogio

    def listar(self, vendedor_id: int) -> list[Produto]:
        """Do mais recente ao mais antigo (última gravação)."""
        return self._produtos.listar(vendedor_id)

    def obter(self, vendedor_id: int, produto_id: str) -> Produto:
        produto = self._produtos.obter(vendedor_id, produto_id)
        if produto is None:
            raise AnuncioNaoEncontrado(NAO_ENCONTRADO)
        return produto

    def salvar(self, vendedor_id: int, produto: Produto) -> Produto:
        """Cria ou substitui. `produto.atualizado_em` é a versão que o navegador leu (409 se ficou velha)."""
        agora = self._relogio()
        # A versão vai em milissegundos: o Date do navegador não guarda microssegundos e daria 409 à toa
        agora = agora.replace(microsecond=agora.microsecond // 1000 * 1000)
        return self._produtos.salvar(vendedor_id, produto, agora)

    def importar(self, vendedor_id: int, produto: Produto) -> bool:
        """Importação única do navegador: False quando o produto ou o item do canal já existe."""
        return self._produtos.importar(vendedor_id, produto)

    def remover(self, vendedor_id: int, produto_id: str) -> None:
        if not self._produtos.remover(vendedor_id, produto_id):
            raise AnuncioNaoEncontrado(NAO_ENCONTRADO)
