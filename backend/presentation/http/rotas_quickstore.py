"""
Apresentação · Rotas HTTP dedicadas à QuickStore (anúncios, callback OAuth 2.0 e webhook)

    POST   /api/anuncios/publicar/quickstore          multipart: "anuncio" (JSON) e "fotos" (até 6)
    GET    /api/anuncios/quickstore/{item_id}         lê o anúncio atualizado direto da QuickStore
    PATCH  /api/anuncios/quickstore/{item_id}/status  pausa ou reativa o anúncio na QuickStore
    PUT    /api/anuncios/quickstore/{item_id}         atualiza dados, fotos e descrição na QuickStore
    DELETE /api/anuncios/quickstore/{item_id}         fecha e exclui o anúncio na QuickStore
    GET    /api/quickstore/callback                   callback OAuth 2.0 oficial da QuickStore
    POST   /api/quickstore/webhook                    receptor de Webhooks (orders_v2 / items) da QuickStore
"""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from backend.application.casos_de_uso import CasosDeUso
from backend.domain.erros import CredenciaisInvalidas, ServicoIndisponivel
from backend.presentation.http.esquemas import NotificacaoWebhookQuickStore, RequisicaoStatusAnuncio
from backend.presentation.http.rotas import (
    ERRO_401,
    ERRO_429,
    JANELA_LOGIN_S,
    LimitadorDeTentativas,
    _ip_do_cliente,
)
from backend.presentation.http.rotas_anuncios import ler_payload_anuncio
from backend.presentation.http.rotas_ia import ERROS_IA

MAX_BYTES_WEBHOOK = 32_768
LIMITE_WEBHOOK_IP = 120
LIMITE_FALHAS_WEBHOOK_IP = 15
JANELA_WEBHOOK_S = 60.0


def criar_rotas_quickstore(
    casos: CasosDeUso,
    VendedorAtual,  # noqa: N803 (tipo anotado do FastAPI)
    concluir_oauth_callback: Callable[..., RedirectResponse],
    limitador: LimitadorDeTentativas | None = None,
) -> APIRouter:
    rotas = APIRouter(tags=["quickstore"])
    limitador = limitador or LimitadorDeTentativas()

    @rotas.post(
        "/anuncios/publicar/quickstore",
        summary="Publica o anúncio na QuickStore (montado no back)",
        responses=ERROS_IA,
    )
    async def publicar_na_quickstore(request: Request, vendedor_id: VendedorAtual) -> dict[str, Any]:
        if casos.publicar_na_quickstore is None:
            raise ServicoIndisponivel()
        anuncio, fotos = await ler_payload_anuncio(request)
        return await run_in_threadpool(casos.publicar_na_quickstore.executar, vendedor_id, anuncio, fotos)

    @rotas.get(
        "/anuncios/quickstore/{item_id}",
        summary="Obtém os dados atualizados de um anúncio na QuickStore",
        responses=ERROS_IA,
    )
    async def obter_anuncio_quickstore(item_id: str, vendedor_id: VendedorAtual) -> dict[str, Any]:
        if casos.publicar_na_quickstore is None:
            raise ServicoIndisponivel()
        return await run_in_threadpool(casos.publicar_na_quickstore.obter, vendedor_id, item_id)

    @rotas.patch(
        "/anuncios/quickstore/{item_id}/status",
        summary="Pausa ou reativa um anúncio na QuickStore",
        responses=ERROS_IA,
    )
    async def alterar_status_quickstore(
        item_id: str,
        corpo: RequisicaoStatusAnuncio,
        vendedor_id: VendedorAtual,
    ) -> dict[str, Any]:
        if casos.publicar_na_quickstore is None:
            raise ServicoIndisponivel()
        return await run_in_threadpool(
            casos.publicar_na_quickstore.alterar_status,
            vendedor_id,
            item_id,
            corpo.status,
        )

    @rotas.put(
        "/anuncios/quickstore/{item_id}",
        summary="Atualiza um anúncio existente na QuickStore",
        responses=ERROS_IA,
    )
    async def atualizar_anuncio_quickstore(
        item_id: str,
        request: Request,
        vendedor_id: VendedorAtual,
    ) -> dict[str, Any]:
        if casos.publicar_na_quickstore is None:
            raise ServicoIndisponivel()
        anuncio, fotos = await ler_payload_anuncio(request, aceitar_json_puro=True)
        return await run_in_threadpool(
            casos.publicar_na_quickstore.atualizar,
            vendedor_id,
            item_id,
            anuncio,
            fotos,
        )

    @rotas.delete(
        "/anuncios/quickstore/{item_id}",
        summary="Fecha e exclui um anúncio na QuickStore",
        responses=ERROS_IA,
    )
    async def excluir_anuncio_quickstore(item_id: str, vendedor_id: VendedorAtual) -> dict[str, Any]:
        if casos.publicar_na_quickstore is None:
            raise ServicoIndisponivel()
        return await run_in_threadpool(casos.publicar_na_quickstore.excluir, vendedor_id, item_id)

    @rotas.get(
        "/quickstore/callback",
        summary="Callback OAuth 2.0 oficial da QuickStore (/api/quickstore/callback)",
    )
    def callback_quickstore(
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
        error_description: str | None = None,
    ) -> RedirectResponse:
        return concluir_oauth_callback(
            slug="quickstore",
            code=code,
            state=state,
            error=error,
            error_description=error_description,
        )

    @rotas.post(
        "/quickstore/webhook",
        summary="Receptor de Webhooks de Vendas (orders_v2) da QuickStore",
        responses={**ERRO_401, **ERRO_429},
    )
    async def webhook_quickstore(request: Request) -> dict[str, Any]:
        if casos.webhook_quickstore is None:
            return {"status": "ok"}
        ip_cliente = _ip_do_cliente(request)
        chave_ip = f"webhook_qs:ip:{ip_cliente}"
        chave_falha_ip = f"webhook_qs_falha:ip:{ip_cliente}"
        limitador.conferir(chave_ip, LIMITE_WEBHOOK_IP, JANELA_WEBHOOK_S)
        limitador.conferir(chave_falha_ip, LIMITE_FALHAS_WEBHOOK_IP, JANELA_LOGIN_S)
        limitador.registrar(chave_ip, JANELA_WEBHOOK_S)

        corpo_bruto = await request.body()
        if not corpo_bruto or len(corpo_bruto) > MAX_BYTES_WEBHOOK:
            limitador.registrar(chave_falha_ip, JANELA_LOGIN_S)
            raise ValueError("Payload do webhook inválido ou excede o tamanho permitido.")

        assinatura = request.headers.get("x-quickstore-signature")
        topico = request.headers.get("x-quickstore-topic")
        try:
            casos.webhook_quickstore.validar_assinatura(corpo_bruto, assinatura)
        except CredenciaisInvalidas:
            limitador.registrar(chave_falha_ip, JANELA_LOGIN_S)
            raise

        try:
            notificacao_bruta = await request.json()
            if not isinstance(notificacao_bruta, dict):
                raise ValueError("Payload do webhook inválido.")
            validada = NotificacaoWebhookQuickStore.model_validate(notificacao_bruta)
        except Exception as erro:
            limitador.registrar(chave_falha_ip, JANELA_LOGIN_S)
            raise ValueError("Payload do webhook inválido.") from erro

        return casos.webhook_quickstore.executar(
            validada.model_dump(by_alias=True),
            topico_header=topico,
        )

    return rotas
