"""
Apresentação · Publicação e gestão do anúncio no Mercado Livre (exige JWT)

    POST   /api/anuncios/publicar/mercado-livre          multipart: "anuncio" (JSON) e "fotos" (até 6)
    GET    /api/anuncios/mercado-livre/{item_id}         lê o anúncio atualizado direto do Mercado Livre
    PATCH  /api/anuncios/mercado-livre/{item_id}/status  pausa ou reativa o anúncio no Mercado Livre
    PUT    /api/anuncios/mercado-livre/{item_id}         atualiza dados, fotos e descrição no Mercado Livre
    DELETE /api/anuncios/mercado-livre/{item_id}         fecha e exclui o anúncio no Mercado Livre
"""

import json
from typing import Any

from fastapi import APIRouter, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from backend.application.casos_de_uso import CasosDeUso
from backend.domain.erros import ServicoIndisponivel
from backend.domain.ia.fotos import MAX_FOTOS_POR_ANALISE
from backend.presentation.http.esquemas import RequisicaoPublicarAnuncio, RequisicaoStatusAnuncio
from backend.presentation.http.rotas_ia import ERROS_IA
from backend.presentation.http.uploads import campo_de_texto, ler_fotos

MAX_BYTES_JSON_ANUNCIO = 100_000


def _ler_anuncio_json(bruto: str) -> dict[str, Any]:
    if len(bruto.encode("utf-8")) > MAX_BYTES_JSON_ANUNCIO:
        raise ValueError("Anúncio inválido.")
    try:
        decodificado = json.loads(bruto)
        if not isinstance(decodificado, dict):
            raise ValueError("Anúncio inválido.")
        return RequisicaoPublicarAnuncio.model_validate(decodificado).model_dump()
    except (json.JSONDecodeError, ValidationError) as erro:
        raise ValueError("Anúncio inválido.") from erro


def criar_rotas_anuncios(casos: CasosDeUso, VendedorAtual) -> APIRouter:  # noqa: N803 (tipo anotado do FastAPI)
    rotas = APIRouter(prefix="/anuncios", tags=["anuncios"])

    @rotas.post("/publicar/mercado-livre", summary="Publica o anúncio no Mercado Livre (montado no back)",
                responses=ERROS_IA)
    async def publicar_no_mercado_livre(request: Request, vendedor_id: VendedorAtual) -> dict[str, Any]:
        if casos.publicar_no_mercado_livre is None:
            raise ServicoIndisponivel()
        fotos = await ler_fotos(request, "fotos", MAX_FOTOS_POR_ANALISE)
        bruto = await campo_de_texto(request, "anuncio") or "{}"
        anuncio = _ler_anuncio_json(bruto)
        return await run_in_threadpool(casos.publicar_no_mercado_livre.executar, vendedor_id, anuncio, fotos)

    @rotas.get("/mercado-livre/{item_id}", summary="Obtém os dados atualizados de um anúncio no Mercado Livre",
               responses=ERROS_IA)
    async def obter_anuncio_mercado_livre(item_id: str, vendedor_id: VendedorAtual) -> dict[str, Any]:
        if casos.publicar_no_mercado_livre is None:
            raise ServicoIndisponivel()
        return await run_in_threadpool(casos.publicar_no_mercado_livre.obter, vendedor_id, item_id)

    @rotas.patch("/mercado-livre/{item_id}/status", summary="Pausa ou reativa um anúncio no Mercado Livre",
                 responses=ERROS_IA)
    async def alterar_status_mercado_livre(item_id: str, corpo: RequisicaoStatusAnuncio,
                                           vendedor_id: VendedorAtual) -> dict[str, Any]:
        if casos.publicar_no_mercado_livre is None:
            raise ServicoIndisponivel()
        return await run_in_threadpool(
            casos.publicar_no_mercado_livre.alterar_status, vendedor_id, item_id, corpo.status
        )

    @rotas.put("/mercado-livre/{item_id}", summary="Atualiza um anúncio existente no Mercado Livre",
               responses=ERROS_IA)
    async def atualizar_anuncio_mercado_livre(item_id: str, request: Request,
                                              vendedor_id: VendedorAtual) -> dict[str, Any]:
        if casos.publicar_no_mercado_livre is None:
            raise ServicoIndisponivel()
        tipo_conteudo = (request.headers.get("content-type") or "").lower()
        if "multipart/form-data" in tipo_conteudo:
            fotos = await ler_fotos(request, "fotos", MAX_FOTOS_POR_ANALISE)
            bruto = await campo_de_texto(request, "anuncio") or "{}"
        else:
            fotos = []
            bruto = (await request.body()).decode("utf-8", errors="replace") or "{}"
        anuncio = _ler_anuncio_json(bruto)
        return await run_in_threadpool(
            casos.publicar_no_mercado_livre.atualizar, vendedor_id, item_id, anuncio, fotos
        )

    @rotas.delete("/mercado-livre/{item_id}", summary="Fecha e exclui um anúncio no Mercado Livre",
                  responses=ERROS_IA)
    async def excluir_anuncio_mercado_livre(item_id: str, vendedor_id: VendedorAtual) -> dict[str, Any]:
        if casos.publicar_no_mercado_livre is None:
            raise ServicoIndisponivel()
        return await run_in_threadpool(casos.publicar_no_mercado_livre.excluir, vendedor_id, item_id)

    return rotas
