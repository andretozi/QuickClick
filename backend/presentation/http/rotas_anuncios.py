"""
Apresentação · Utilitários HTTP compartilhados de leitura e validação de anúncio multipart/JSON
"""

import json
from typing import Any

from fastapi import Request
from pydantic import ValidationError

from backend.application.ia.modelos import ArquivoDeFoto
from backend.domain.ia.fotos import MAX_FOTOS_POR_ANALISE
from backend.presentation.http.esquemas import RequisicaoPublicarAnuncio
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


async def ler_payload_anuncio(
    request: Request,
    *,
    aceitar_json_puro: bool = False,
) -> tuple[dict[str, Any], list[ArquivoDeFoto]]:
    tipo_conteudo = (request.headers.get("content-type") or "").lower()
    if not aceitar_json_puro or "multipart/form-data" in tipo_conteudo:
        fotos = await ler_fotos(request, "fotos", MAX_FOTOS_POR_ANALISE)
        bruto = await campo_de_texto(request, "anuncio") or "{}"
    else:
        fotos = []
        bruto = (await request.body()).decode("utf-8", errors="replace") or "{}"
    anuncio = _ler_anuncio_json(bruto)
    return anuncio, fotos
