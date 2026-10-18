"""
Apresentação · Publicação do anúncio montada no back (exige JWT)

    POST /api/anuncios/publicar/mercado-livre   multipart: "anuncio" (JSON) e "fotos" (até 6)

Substitui a antiga POST /api/marketplaces/{slug}/products, que aceitava qualquer dict.
"""

import json
from typing import Any

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from backend.application.casos_de_uso import CasosDeUso
from backend.domain.erros import ServicoIndisponivel
from backend.domain.ia.fotos import MAX_FOTOS_POR_ANALISE
from backend.presentation.http.rotas_ia import ERROS_IA
from backend.presentation.http.uploads import campo_de_texto, ler_fotos


def criar_rotas_anuncios(casos: CasosDeUso, VendedorAtual) -> APIRouter:  # noqa: N803 (tipo anotado do FastAPI)
    rotas = APIRouter(prefix="/anuncios", tags=["anuncios"])

    @rotas.post("/publicar/mercado-livre", summary="Publica o anúncio no Mercado Livre (montado no back)",
                responses=ERROS_IA)
    async def publicar_no_mercado_livre(request: Request, vendedor_id: VendedorAtual) -> dict[str, Any]:
        if casos.publicar_no_mercado_livre is None:
            raise ServicoIndisponivel()
        fotos = await ler_fotos(request, "fotos", MAX_FOTOS_POR_ANALISE)
        try:
            anuncio = json.loads(await campo_de_texto(request, "anuncio") or "{}")
        except json.JSONDecodeError as erro:
            raise ValueError("Anúncio inválido.") from erro
        return await run_in_threadpool(casos.publicar_no_mercado_livre.executar, vendedor_id, anuncio, fotos)

    return rotas
