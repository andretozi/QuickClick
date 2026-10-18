"""
Apresentação · Rotas da IA no criar anúncio (todas exigem JWT)

    GET  /api/ia/cota                      plano, nível, análises usadas e restantes, o que o plano tem
    POST /api/ia/analises                  multipart "fotos" (até 6): cria e dispara em segundo plano (202)
    GET  /api/ia/analises/{id}             estado, etapa, resultados parciais e mensagens
    POST /api/ia/analises/{id}/fotos       multipart "foto" + "tipo" (etiqueta, verso, detalhe)
    POST /api/ia/analises/{id}/confirmacao atributos confirmados e respostas (JSON)
    POST /api/ia/analises/{id}/retomar     multipart "fotos" opcional (quando a leitura não terminou)

As fotos ficam só em memória (uploads.py).
"""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from backend.application.casos_de_uso import CasosDeUso
from backend.domain.erros import FotoInvalida, IAIndisponivel
from backend.domain.ia.fotos import MAX_FOTOS_POR_ANALISE
from backend.presentation.http.esquemas import RequisicaoConfirmacaoIA, RespostaDeErro
from backend.presentation.http.uploads import campo_de_texto, ler_fotos

ERROS_IA = {
    400: {"model": RespostaDeErro, "description": "Foto inválida (foto_invalida)"},
    401: {"model": RespostaDeErro, "description": "Token inválido, expirado ou ausente"},
    403: {"model": RespostaDeErro, "description": "Cota do mês esgotada (cota_esgotada)"},
    404: {"model": RespostaDeErro, "description": "Análise não encontrada"},
    409: {"model": RespostaDeErro, "description": "Análise em andamento, estado inválido ou fotos necessárias"},
    429: {"model": RespostaDeErro, "description": "Limite de análises por hora (limite_por_hora)"},
    503: {"model": RespostaDeErro, "description": "IA indisponível agora (ia_indisponivel)"},
}


def criar_rotas_ia(casos: CasosDeUso, VendedorAtual) -> APIRouter:  # noqa: N803 (tipo anotado do FastAPI)
    rotas = APIRouter(prefix="/ia", tags=["ia"])

    def servico():
        if casos.analises_ia is None:
            raise IAIndisponivel()
        return casos.analises_ia

    @rotas.get("/cota", summary="Cota de análises do mês e o que o plano tem", responses=ERROS_IA)
    def cota(vendedor_id: VendedorAtual) -> dict[str, Any]:
        return servico().cota(vendedor_id)

    @rotas.post("/analises", status_code=202, summary="Cria uma análise com até 6 fotos", responses=ERROS_IA)
    async def criar(request: Request, vendedor_id: VendedorAtual) -> JSONResponse:
        fotos = await ler_fotos(request, "fotos", MAX_FOTOS_POR_ANALISE)
        if not fotos:
            raise FotoInvalida("Manda pelo menos uma foto do produto.")
        resultado = await run_in_threadpool(servico().criar, vendedor_id, fotos)
        return JSONResponse(status_code=202, content=resultado)

    @rotas.get("/analises/{analise_id}", summary="Andamento e resultados da análise", responses=ERROS_IA)
    def obter(analise_id: str, vendedor_id: VendedorAtual) -> dict[str, Any]:
        return servico().obter(vendedor_id, analise_id)

    @rotas.post("/analises/{analise_id}/fotos", summary="Foto extra (etiqueta, verso, detalhe)", responses=ERROS_IA)
    async def foto_extra(analise_id: str, request: Request, vendedor_id: VendedorAtual) -> dict[str, Any]:
        fotos = await ler_fotos(request, "foto", 1)
        if not fotos:
            raise FotoInvalida("Manda a foto da etiqueta, do verso ou do detalhe.")
        tipo = await campo_de_texto(request, "tipo")
        return await run_in_threadpool(servico().foto_extra, vendedor_id, analise_id, fotos[0], tipo)

    @rotas.post("/analises/{analise_id}/confirmacao", summary="Confirma os atributos e continua", responses=ERROS_IA)
    def confirmar(analise_id: str, vendedor_id: VendedorAtual, corpo: RequisicaoConfirmacaoIA) -> dict[str, Any]:
        return servico().confirmar(vendedor_id, analise_id, corpo.model_dump())

    @rotas.post("/analises/{analise_id}/retomar", summary="Retoma uma análise interrompida ou com falha",
                responses=ERROS_IA)
    async def retomar(analise_id: str, request: Request, vendedor_id: VendedorAtual) -> dict[str, Any]:
        fotos = await ler_fotos(request, "fotos", MAX_FOTOS_POR_ANALISE)
        return await run_in_threadpool(servico().retomar, vendedor_id, analise_id, fotos or None)

    return rotas
