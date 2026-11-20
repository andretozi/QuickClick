"""
Caso de uso · Gerenciar os produtos (anúncios da Quick Click) guardados no banco

O vendedor vem sempre do token. Produto de outro vendedor é tratado como inexistente (404, nunca 403).
"""

from collections.abc import Callable
from datetime import datetime
import logging
from typing import Any

from backend.application.casos_de_uso.publicar_no_mercado_livre import PublicarNoMercadoLivre
from backend.application.portas import RepositorioDeProdutos
from backend.domain.erros import AnuncioNaoEncontrado
from backend.domain.produto import Produto, Publicacao

log = logging.getLogger("quickclick.marketplaces")

NAO_ENCONTRADO = "Não encontramos esse anúncio na sua conta."
QUICKSTORE = "quickstore"


def _publicacao_do_canal(produto: Produto | None, canal: str) -> Publicacao | None:
    if produto is None:
        return None
    for pub in produto.publicacoes:
        if pub.canal == canal:
            return pub
    return None


def _dados_do_produto_mudaram(anterior: Produto, novo: Produto) -> bool:
    pub_antiga = _publicacao_do_canal(anterior, QUICKSTORE)
    pub_nova = _publicacao_do_canal(novo, QUICKSTORE)
    preco_qs_antigo = (
        pub_antiga.preco_centavos if pub_antiga and pub_antiga.preco_centavos is not None else anterior.preco_centavos
    )
    preco_qs_novo = (
        pub_nova.preco_centavos if pub_nova and pub_nova.preco_centavos is not None else novo.preco_centavos
    )
    return (
        anterior.titulo != novo.titulo
        or anterior.descricao != novo.descricao
        or anterior.preco_centavos != novo.preco_centavos
        or preco_qs_antigo != preco_qs_novo
        or anterior.estoque != novo.estoque
        or anterior.condicao != novo.condicao
        or anterior.fotos != novo.fotos
        or anterior.atributos != novo.atributos
    )


def _payload_para_publicador(produto: Produto, pub: Publicacao) -> dict[str, Any]:
    atributos = []
    for item in produto.atributos or []:
        if isinstance(item, dict):
            chave = str(item.get("nome") or item.get("chave") or item.get("id") or "").strip()
            valor = item.get("valor")
            if chave and valor is not None and str(valor).strip() != "":
                atributos.append({"chave": chave, "valor": str(valor).strip()})
    preco_canal = pub.preco_centavos if pub.preco_centavos is not None else produto.preco_centavos
    return {
        "titulo": produto.titulo,
        "descricao": produto.descricao,
        "preco_centavos": max(100, int(preco_canal or 0)),
        "estoque": int(produto.estoque or 0),
        "condicao": produto.condicao,
        "atributos": atributos,
        "analise_id": produto.analise_id,
        "ml_categoria_id": pub.categoria_id,
        "fotos_mantidas": list(produto.fotos or [])[:6],
    }


class GerenciarProdutos:
    def __init__(
        self,
        produtos: RepositorioDeProdutos,
        relogio: Callable[[], datetime],
        *,
        publicar_na_quickstore: PublicarNoMercadoLivre | None = None,
    ):
        self._produtos = produtos
        self._relogio = relogio
        self._publicar_na_quickstore = publicar_na_quickstore

    def listar(self, vendedor_id: int) -> list[Produto]:
        """Do mais recente ao mais antigo (última gravação)."""
        return self._produtos.listar(vendedor_id)

    def obter(self, vendedor_id: int, produto_id: str) -> Produto:
        produto = self._produtos.obter(vendedor_id, produto_id)
        if produto is None:
            raise AnuncioNaoEncontrado(NAO_ENCONTRADO)
        return produto

    def _sincronizar_com_quickstore(
        self,
        vendedor_id: int,
        anterior: Produto | None,
        salvo: Produto,
    ) -> None:
        if self._publicar_na_quickstore is None or anterior is None:
            return
        pub_antiga = _publicacao_do_canal(anterior, QUICKSTORE)
        pub_nova = _publicacao_do_canal(salvo, QUICKSTORE)
        id_antigo = str(pub_antiga.id_externo or "").strip() if pub_antiga else ""
        id_novo = str(pub_nova.id_externo or "").strip() if pub_nova else ""

        if id_antigo and (pub_nova is None or pub_nova.status == "nao_publicado" or not id_novo):
            try:
                self._publicar_na_quickstore.excluir(vendedor_id, id_antigo)
            except Exception as erro:
                log.debug("Não deu para encerrar item %s na QuickStore ao salvar produto: %s", id_antigo, erro)
            return

        if not id_novo or id_novo != id_antigo or pub_nova is None:
            return

        try:
            if _dados_do_produto_mudaram(anterior, salvo):
                self._publicar_na_quickstore.atualizar(
                    vendedor_id,
                    id_novo,
                    _payload_para_publicador(salvo, pub_nova),
                )
            if pub_antiga and pub_antiga.status != pub_nova.status and pub_nova.status in ("publicado", "pausado"):
                self._publicar_na_quickstore.alterar_status(vendedor_id, id_novo, pub_nova.status)
        except Exception as erro:
            log.debug("Não deu para sincronizar item %s na QuickStore ao salvar produto: %s", id_novo, erro)

    def salvar(self, vendedor_id: int, produto: Produto, *, sincronizar_quickstore: bool = True) -> Produto:
        """Cria ou substitui. `produto.atualizado_em` é a versão que o navegador leu (409 se ficou velha)."""
        anterior = self._produtos.obter(vendedor_id, produto.id)
        agora = self._relogio()
        # A versão vai em milissegundos: o Date do navegador não guarda microssegundos e daria 409 à toa
        agora = agora.replace(microsecond=agora.microsecond // 1000 * 1000)
        salvo = self._produtos.salvar(vendedor_id, produto, agora)
        if sincronizar_quickstore:
            self._sincronizar_com_quickstore(vendedor_id, anterior, salvo)
        return salvo

    def importar(self, vendedor_id: int, produto: Produto) -> bool:
        """Importação única do navegador: False quando o produto ou o item do canal já existe."""
        return self._produtos.importar(vendedor_id, produto)

    def remover(self, vendedor_id: int, produto_id: str) -> None:
        anterior = self._produtos.obter(vendedor_id, produto_id)
        if not self._produtos.remover(vendedor_id, produto_id):
            raise AnuncioNaoEncontrado(NAO_ENCONTRADO)
        if self._publicar_na_quickstore is not None and anterior is not None:
            pub_qs = _publicacao_do_canal(anterior, QUICKSTORE)
            id_qs = str(pub_qs.id_externo or "").strip() if pub_qs else ""
            if id_qs:
                try:
                    self._publicar_na_quickstore.excluir(vendedor_id, id_qs)
                except Exception as erro:
                    log.debug("Não deu para excluir item %s na QuickStore ao remover produto: %s", id_qs, erro)
