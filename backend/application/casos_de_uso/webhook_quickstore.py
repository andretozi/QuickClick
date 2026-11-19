"""
Aplicação · Processamento de Webhooks de Vendas da QuickStore (`orders_v2`)

Quando uma compra é concluída na QuickStore, o servidor envia um POST para `/api/quickstore/webhook`
com `X-QuickStore-Topic: orders_v2` e `X-QuickStore-Signature: sha256=<hmac_sha256>`.
Este caso de uso:
1. Valida a assinatura HMAC-SHA256 usando `QUICKSTORE_CLIENT_SECRET`;
2. Identifica o vendedor na Quick Click que vinculou a conta externa (`user_id` da QuickStore);
3. Consulta os detalhes completos do pedido (`GET /orders/{order_id}`) com o Bearer token ativo do vendedor;
4. Deduz a quantidade comprada do estoque do produto na Quick Click (com idempotência por pedido);
5. Propaga o novo estoque para os outros marketplaces onde o mesmo produto está publicado.
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from backend.application.casos_de_uso.conectar_marketplace import ConectarMarketplace
from backend.application.portas import (
    FalhaNoMarketplace,
    GatewayWebhookQuickStore,
    PublicadorMercadoLivre,
    RepositorioContasVinculadas,
    RepositorioDeProdutos,
)
from backend.domain.erros import AnuncioDesatualizado, CredenciaisInvalidas
from backend.domain.produto import Produto, Publicacao

log = logging.getLogger("quickclick.marketplaces")

QUICKSTORE = "quickstore"
TOPICO_PEDIDOS = "orders_v2"
STATUS_PEDIDO_VALIDOS = {"paid", "confirmed", "approved", "completed"}
MAX_PEDIDOS_PROCESSADOS_MEMORIA = 2_000


def _agora_utc() -> datetime:
    return datetime.now(UTC)


def _normalizar_titulo(texto: str) -> str:
    return " ".join(str(texto or "").strip().lower().split())


class ProcessarWebhookQuickStore:
    def __init__(
        self,
        gateway_quickstore: GatewayWebhookQuickStore,
        contas: RepositorioContasVinculadas,
        conectar: ConectarMarketplace,
        produtos: RepositorioDeProdutos,
        publicadores: dict[str, PublicadorMercadoLivre] | None = None,
        relogio: Callable[[], datetime] = _agora_utc,
        exigir_assinatura: bool = True,
    ):
        self._gateway = gateway_quickstore
        self._contas = contas
        self._conectar = conectar
        self._produtos = produtos
        self._publicadores = dict(publicadores or {})
        self._relogio = relogio
        self._exigir_assinatura = exigir_assinatura
        self._trava = threading.Lock()
        self._pedidos_processados: set[str] = set()

    def validar_assinatura(self, corpo_bruto: bytes, assinatura_header: str | None) -> None:
        """Verifica obrigatoriamente o HMAC-SHA256 (fail-closed: sem segredo ou sem assinatura válida, recusa)."""
        if self._gateway.tem_segredo_configurado:
            if not self._gateway.validar_assinatura_webhook(corpo_bruto, assinatura_header):
                raise CredenciaisInvalidas("Assinatura do webhook da QuickStore inválida.")
        elif self._exigir_assinatura:
            raise CredenciaisInvalidas("Segredo do webhook da QuickStore não configurado.")

    def _ja_processado(self, chave_pedido: str) -> bool:
        with self._trava:
            return chave_pedido in self._pedidos_processados

    def _marcar_processado(self, chave_pedido: str) -> None:
        with self._trava:
            if len(self._pedidos_processados) >= MAX_PEDIDOS_PROCESSADOS_MEMORIA:
                self._pedidos_processados.clear()
            self._pedidos_processados.add(chave_pedido)

    def _encontrar_produto(self, lista: list[Produto], item_id: str, titulo: str) -> Produto | None:
        codigo = str(item_id or "").strip()
        if codigo:
            for prod in lista:
                for pub in prod.publicacoes:
                    if pub.canal == QUICKSTORE and str(pub.id_externo or "").strip() == codigo:
                        return prod
            for prod in lista:
                for pub in prod.publicacoes:
                    if str(pub.id_externo or "").strip() == codigo:
                        return prod
        titulo_norm = _normalizar_titulo(titulo)
        if titulo_norm:
            for prod in lista:
                if _normalizar_titulo(prod.titulo) == titulo_norm:
                    return prod
        return None

    def _propagar_estoque_nos_canais(
        self,
        vendedor_id: int,
        produto: Produto,
        novo_estoque: int,
        canal_origem: str = QUICKSTORE,
    ) -> list[str]:
        sincronizados: list[str] = []
        for pub in produto.publicacoes:
            if not pub.id_externo or pub.canal == canal_origem:
                continue
            publicador = self._publicadores.get(pub.canal)
            if publicador is None:
                continue
            token = self._conectar.token_ativo(vendedor_id, pub.canal)
            if not token:
                continue
            try:
                if novo_estoque <= 0:
                    publicador.atualizar_anuncio(token, pub.id_externo, {"status": "paused"})
                else:
                    publicador.atualizar_anuncio(token, pub.id_externo, {"available_quantity": novo_estoque})
                sincronizados.append(pub.canal)
            except FalhaNoMarketplace as erro:
                log.warning(
                    "Não deu para propagar estoque do item %s para %s (%s).",
                    pub.id_externo,
                    pub.canal,
                    erro.status or "sem resposta",
                )
        return sincronizados

    def _abater_item_do_vendedor(
        self,
        vendedor_id: int,
        item_id: str,
        titulo: str,
        quantidade: int,
    ) -> dict[str, Any] | None:
        if quantidade <= 0:
            return None
        for _ in range(3):
            lista = self._produtos.listar(vendedor_id)
            produto = self._encontrar_produto(lista, item_id, titulo)
            if produto is None:
                return None

            novo_estoque = max(0, int(produto.estoque) - quantidade)
            novas_publicacoes: list[Publicacao] = []
            achou_quickstore = False
            for pub in produto.publicacoes:
                eh_item_qs = pub.canal == QUICKSTORE or (item_id and pub.id_externo == item_id)
                if pub.canal == QUICKSTORE:
                    achou_quickstore = True
                novo_status = "pausado" if (novo_estoque == 0 and pub.status == "publicado") else pub.status
                novos_vendidos = int(pub.vendidos or 0) + quantidade if eh_item_qs else int(pub.vendidos or 0)
                novo_id_externo = pub.id_externo or (item_id if pub.canal == QUICKSTORE and item_id else None)
                novas_publicacoes.append(
                    replace(
                        pub,
                        status=novo_status,
                        vendidos=novos_vendidos,
                        id_externo=novo_id_externo,
                    )
                )
            if not achou_quickstore and item_id:
                novas_publicacoes.append(
                    Publicacao(
                        canal=QUICKSTORE,
                        status="pausado" if novo_estoque == 0 else "publicado",
                        id_externo=item_id,
                        vendidos=quantidade,
                    )
                )

            atualizado = replace(
                produto,
                estoque=novo_estoque,
                publicacoes=novas_publicacoes,
            )
            agora = self._relogio()
            agora = agora.replace(microsecond=agora.microsecond // 1000 * 1000)
            try:
                salvo = self._produtos.salvar(vendedor_id, atualizado, agora)
            except AnuncioDesatualizado:
                continue

            canais_propagados = self._propagar_estoque_nos_canais(vendedor_id, salvo, novo_estoque)
            return {
                "produto_id": salvo.id,
                "item_id": item_id,
                "estoque_anterior": produto.estoque,
                "novo_estoque": salvo.estoque,
                "quantidade_vendida": quantidade,
                "canais_sincronizados": canais_propagados,
            }
        return None

    def executar(
        self,
        notificacao: dict[str, Any],
        *,
        topico_header: str | None = None,
    ) -> dict[str, Any]:
        topico = str(topico_header or notificacao.get("topic") or "").strip().lower()
        recurso = str(notificacao.get("resource") or "").strip()
        user_id = str(notificacao.get("user_id") if notificacao.get("user_id") is not None else "").strip()

        if topico and topico != TOPICO_PEDIDOS:
            return {"status": "ignorado", "motivo": "topico_nao_suportado", "topico": topico}

        if not recurso or not user_id:
            return {"status": "ignorado", "motivo": "notificacao_incompleta"}

        vinculos = self._contas.buscar_por_conta_externa(QUICKSTORE, user_id)
        if not vinculos:
            log.info("Webhook QuickStore recebido para user_id=%s sem conta vinculada.", user_id)
            return {"status": "ignorado", "motivo": "conta_nao_vinculada"}

        itens_atualizados: list[dict[str, Any]] = []
        for conta in vinculos:
            vendedor_id = conta.vendedor_id
            token = self._conectar.token_ativo(vendedor_id, QUICKSTORE)
            if not token:
                continue
            try:
                pedido = self._gateway.obter_pedido(token, recurso)
            except (FalhaNoMarketplace, ValueError) as erro:
                log.warning("Falha ao buscar pedido %s na QuickStore para vendedor %s: %s", recurso, vendedor_id, erro)
                continue

            vendedor_do_pedido = pedido.get("seller") if isinstance(pedido.get("seller"), dict) else {}
            id_vendedor_pedido = str(
                vendedor_do_pedido.get("id") if vendedor_do_pedido.get("id") is not None else (pedido.get("seller_id") or "")
            ).strip()
            if id_vendedor_pedido and id_vendedor_pedido != user_id:
                log.warning(
                    "Tentativa de spoofing bloqueada no webhook QuickStore: pedido %s pertence ao seller %s, não a %s.",
                    recurso,
                    id_vendedor_pedido,
                    user_id,
                )
                continue

            pedido_id = str(pedido.get("id") or recurso).strip()
            chave_idempotencia = f"{vendedor_id}:{pedido_id}"
            if self._ja_processado(chave_idempotencia):
                continue

            status_pedido = str(pedido.get("status") or "paid").strip().lower()
            if status_pedido and status_pedido not in STATUS_PEDIDO_VALIDOS:
                continue

            for order_item in pedido.get("order_items") or []:
                if not isinstance(order_item, dict):
                    continue
                bloco_item = order_item.get("item") if isinstance(order_item.get("item"), dict) else {}
                item_id = str(bloco_item.get("id") or order_item.get("item_id") or "").strip()
                titulo = str(bloco_item.get("title") or order_item.get("title") or "").strip()
                try:
                    quantidade = int(order_item.get("quantity") or 0)
                except (TypeError, ValueError):
                    quantidade = 0
                if quantidade <= 0:
                    continue
                resultado = self._abater_item_do_vendedor(vendedor_id, item_id, titulo, quantidade)
                if resultado is not None:
                    itens_atualizados.append(resultado)

            self._marcar_processado(chave_idempotencia)

        return {
            "status": "ok",
            "topico": TOPICO_PEDIDOS,
            "recurso": recurso,
            "itens_atualizados": itens_atualizados,
        }
