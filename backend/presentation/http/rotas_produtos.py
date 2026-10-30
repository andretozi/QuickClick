"""
Apresentação · Anúncios da Quick Click guardados no banco, por vendedor (exige JWT)

    GET    /api/produtos                  {"produtos": [Produto]}, do mais recente ao mais antigo
    GET    /api/produtos/{produto_id}     Produto
    PUT    /api/produtos/{produto_id}     cria ou substitui (vale o id do caminho); 409 se outra aba gravou antes
    POST   /api/produtos/importar         importação única do navegador: {"importado": true ou false}
    DELETE /api/produtos/{produto_id}     204; apaga o produto e as publicações dele

Produto de outro vendedor responde 404, nunca 403. Nada aqui registra corpo, foto ou título.
O corpo tem limite de 512 KB (limite_do_corpo.py, registrado em api.py).
"""

from typing import Annotated

from fastapi import APIRouter, Path, Response
from starlette.concurrency import run_in_threadpool

from backend.application.casos_de_uso import CasosDeUso
from backend.application.casos_de_uso.produtos import GerenciarProdutos
from backend.domain.erros import ServicoIndisponivel
from backend.presentation.http.esquemas import (
    PADRAO_ID_PRODUTO,
    ListaDeProdutos,
    ProdutoApi,
    RespostaDeErro,
    ResultadoDaImportacao,
    produto_do_corpo,
    produto_saida,
)

MAX_BYTES_DO_PRODUTO = 512 * 1024

ProdutoId = Annotated[str, Path(pattern=PADRAO_ID_PRODUTO)]

ERROS_PRODUTOS = {
    401: {"model": RespostaDeErro, "description": "Token inválido, expirado ou ausente"},
    404: {"model": RespostaDeErro, "description": "Anúncio não encontrado (anuncio_nao_encontrado)"},
    409: {"model": RespostaDeErro, "description": "Outra aba ou aparelho gravou antes (anuncio_desatualizado)"},
    413: {"model": RespostaDeErro, "description": "Corpo acima de 512 KB (pedido_grande_demais)"},
    422: {"model": RespostaDeErro, "description": "Dado fora dos limites (parametro_invalido)"},
}


def criar_rotas_produtos(casos: CasosDeUso, VendedorAtual) -> APIRouter:  # noqa: N803 (tipo anotado do FastAPI)
    rotas = APIRouter(prefix="/produtos", tags=["produtos"], responses=ERROS_PRODUTOS)

    def servico() -> GerenciarProdutos:
        if casos.produtos is None:
            raise ServicoIndisponivel()
        return casos.produtos

    @rotas.get("", summary="Anúncios do vendedor, do mais recente ao mais antigo")
    async def listar(vendedor_id: VendedorAtual) -> ListaDeProdutos:
        produtos = await run_in_threadpool(servico().listar, vendedor_id)
        return ListaDeProdutos(produtos=[produto_saida(p) for p in produtos])

    @rotas.post("/importar", summary="Importa um anúncio do navegador, uma vez só")
    async def importar(corpo: ProdutoApi, vendedor_id: VendedorAtual) -> ResultadoDaImportacao:
        importado = await run_in_threadpool(servico().importar, vendedor_id, produto_do_corpo(corpo, corpo.id))
        return ResultadoDaImportacao(importado=importado)

    @rotas.get("/{produto_id}", summary="Um anúncio do vendedor")
    async def obter(produto_id: ProdutoId, vendedor_id: VendedorAtual) -> ProdutoApi:
        return produto_saida(await run_in_threadpool(servico().obter, vendedor_id, produto_id))

    @rotas.put("/{produto_id}", summary="Cria ou substitui o anúncio e as publicações dele")
    async def salvar(produto_id: ProdutoId, corpo: ProdutoApi, vendedor_id: VendedorAtual) -> ProdutoApi:
        produto = await run_in_threadpool(servico().salvar, vendedor_id, produto_do_corpo(corpo, produto_id))
        return produto_saida(produto)

    @rotas.delete("/{produto_id}", status_code=204, summary="Apaga o anúncio e as publicações dele")
    async def remover(produto_id: ProdutoId, vendedor_id: VendedorAtual) -> Response:
        await run_in_threadpool(servico().remover, vendedor_id, produto_id)
        return Response(status_code=204)

    return rotas
