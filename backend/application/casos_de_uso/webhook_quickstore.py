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
TOPICO_ITENS = "items"
TOPICOS_SUPORTADOS = {TOPICO_PEDIDOS, TOPICO_ITENS}
STATUS_PEDIDO_VALIDOS = {"paid", "confirmed", "approved", "completed"}
MAX_PEDIDOS_PROCESSADOS_MEMORIA = 2_000


def _agora_utc() -> datetime:
    return datetime.now(UTC)


def _normalizar_titulo(texto: str) -> str:
    return " ".join(str(texto or "").strip().lower().split())


def _status_do_item_no_canal(status_externo: str) -> str:
    limpo = str(status_externo or "").strip().lower()
    if limpo == "active":
        return "publicado"
    if limpo == "paused":
        return "pausado"
    return "nao_publicado"


def _extrair_item_id(recurso: str) -> str:
    texto = str(recurso or "").strip()
    if texto.startswith("/items/"):
        codigo = texto.removeprefix("/items/").strip("/")
    elif texto.startswith("items/"):
        codigo = texto.removeprefix("items/").strip("/")
    else:
        codigo = texto.strip("/")
    if not codigo or len(codigo) > 64 or "/" in codigo or ".." in codigo or not codigo.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Identificador do item inválido.")
    return codigo


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

    def _propagar_dados_nos_canais(
        self,
        vendedor_id: int,
        produto: Produto,
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
                mudancas: dict[str, Any] = {
                    "price": produto.preco_centavos / 100,
                    "available_quantity": max(1, produto.estoque) if pub.status == "publicado" else produto.estoque,
                }
                if produto.estoque <= 0 and pub.status == "publicado":
                    publicador.atualizar_anuncio(token, pub.id_externo, {"status": "paused"})
                else:
                    publicador.atualizar_anuncio(token, pub.id_externo, mudancas)
                if produto.descricao and hasattr(publicador, "atualizar_descricao"):
                    publicador.atualizar_descricao(token, pub.id_externo, produto.descricao)
                sincronizados.append(pub.canal)
            except FalhaNoMarketplace as erro:
                log.warning(
                    "Não deu para propagar dados do item %s para %s (%s).",
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

    def _colocar_item_em_standby_no_vendedor(self, vendedor_id: int, item_id: str) -> dict[str, Any] | None:
        for _ in range(3):
            lista = self._produtos.listar(vendedor_id)
            produto = self._encontrar_produto(lista, item_id, "")
            if produto is None:
                return None
            novas_publicacoes: list[Publicacao] = []
            for pub in produto.publicacoes:
                if pub.canal == QUICKSTORE:
                    novas_publicacoes.append(
                        replace(pub, status="nao_publicado", id_externo=None, permalink=None)
                    )
                else:
                    novas_publicacoes.append(pub)
            agora = self._relogio()
            agora = agora.replace(microsecond=agora.microsecond // 1000 * 1000)
            try:
                salvo = self._produtos.salvar(vendedor_id, replace(produto, publicacoes=novas_publicacoes), agora)
            except AnuncioDesatualizado:
                continue
            return {"produto_id": salvo.id, "item_id": item_id, "status": "nao_publicado"}
        return None

    def _sincronizar_item_do_vendedor(
        self,
        vendedor_id: int,
        item_id: str,
        dados_item: dict[str, Any],
    ) -> dict[str, Any] | None:
        titulo = str(dados_item.get("title") or dados_item.get("family_name") or "").strip()[:300]
        status_canal = _status_do_item_no_canal(str(dados_item.get("status") or ""))
        if str(dados_item.get("status") or "").strip().lower() in ("closed", "inactive"):
            return self._colocar_item_em_standby_no_vendedor(vendedor_id, item_id)

        try:
            preco_centavos = max(0, round(float(dados_item.get("price") or 0) * 100))
        except (TypeError, ValueError):
            preco_centavos = 0
        try:
            estoque = max(0, int(dados_item.get("available_quantity") or 0))
        except (TypeError, ValueError):
            estoque = 0
        try:
            vendidos = max(0, int(dados_item.get("sold_quantity") or 0))
        except (TypeError, ValueError):
            vendidos = 0
        condicao_raw = str(dados_item.get("condition") or "").strip().lower()
        condicao = "usado" if condicao_raw in ("used", "usado", "recondicionado") else "novo"
        descricao = str(dados_item.get("description") or "").strip()[:50_000]
        fotos_externas = [
            str(u).strip()
            for u in (dados_item.get("pictures") or [])
            if isinstance(u, str) and str(u).strip().startswith("https://")
        ][:12]
        atributos_externos = [
            {
                "id": str(a.get("id") or "") or None,
                "nome": str(a.get("name") or a.get("id") or "").strip()[:200],
                "valor": str(a.get("value") if a.get("value") is not None else (a.get("value_name") or "")).strip()[:1000],
            }
            for a in (dados_item.get("attributes") or [])
            if isinstance(a, dict) and (a.get("name") or a.get("id"))
        ]
        permalink_raw = str(dados_item.get("permalink") or "").strip()
        permalink = permalink_raw if permalink_raw.startswith("https://") else None
        categoria_id = str(dados_item.get("category_id") or "").strip() or None
        saude_raw = dados_item.get("health")
        try:
            saude_num = float(saude_raw) if saude_raw is not None else None
            saude = round(saude_num * 100) if saude_num is not None and saude_num <= 1 else (round(saude_num) if saude_num is not None else None)
        except (TypeError, ValueError):
            saude = None

        for _ in range(3):
            lista = self._produtos.listar(vendedor_id)
            produto = self._encontrar_produto(lista, item_id, titulo)
            agora = self._relogio()
            agora = agora.replace(microsecond=agora.microsecond // 1000 * 1000)

            pub_qs = Publicacao(
                canal=QUICKSTORE,
                status=status_canal,
                id_externo=item_id,
                permalink=permalink,
                categoria_id=categoria_id,
                saude=saude,
                vendidos=vendidos,
            )

            if produto is None:
                novo_id = f"qs_{item_id.lower()[:32]}"
                novo_produto = Produto(
                    id=novo_id,
                    titulo=titulo or f"Anúncio {item_id}",
                    descricao=descricao,
                    categoria="outros",
                    condicao=condicao,
                    preco_centavos=preco_centavos,
                    preco_sugerido_centavos=None,
                    estoque=estoque,
                    fotos=fotos_externas,
                    capa=0,
                    atributos=atributos_externos,
                    analise_id=None,
                    criado_em=agora,
                    atualizado_em=agora,
                    publicacoes=[pub_qs],
                )
                try:
                    salvo = self._produtos.salvar(vendedor_id, novo_produto, agora)
                except AnuncioDesatualizado:
                    continue
                return {
                    "produto_id": salvo.id,
                    "item_id": item_id,
                    "status": status_canal,
                    "novo_estoque": salvo.estoque,
                    "canais_sincronizados": [],
                }

            novas_publicacoes: list[Publicacao] = []
            achou_qs = False
            for pub in produto.publicacoes:
                if pub.canal == QUICKSTORE:
                    achou_qs = True
                    novas_publicacoes.append(
                        replace(
                            pub_qs,
                            permalink=permalink or pub.permalink,
                            categoria_id=categoria_id or pub.categoria_id,
                            saude=saude if saude is not None else pub.saude,
                        )
                    )
                else:
                    novo_status_outro = "pausado" if (estoque == 0 and pub.status == "publicado") else pub.status
                    novas_publicacoes.append(replace(pub, status=novo_status_outro))
            if not achou_qs:
                novas_publicacoes.append(pub_qs)

            atualizado = replace(
                produto,
                titulo=titulo or produto.titulo,
                descricao=descricao or produto.descricao,
                condicao=condicao,
                preco_centavos=preco_centavos if preco_centavos > 0 else produto.preco_centavos,
                estoque=estoque,
                fotos=fotos_externas if fotos_externas else produto.fotos,
                atributos=atributos_externos if atributos_externos else produto.atributos,
                publicacoes=novas_publicacoes,
            )
            try:
                salvo = self._produtos.salvar(vendedor_id, atualizado, agora)
            except AnuncioDesatualizado:
                continue

            canais_propagados = self._propagar_dados_nos_canais(vendedor_id, salvo)
            return {
                "produto_id": salvo.id,
                "item_id": item_id,
                "status": status_canal,
                "novo_estoque": salvo.estoque,
                "canais_sincronizados": canais_propagados,
            }
        return None

    def _executar_webhook_item(self, recurso: str, user_id: str, vinculos: list[Any]) -> dict[str, Any]:
        try:
            item_id = _extrair_item_id(recurso)
        except ValueError:
            return {"status": "ignorado", "motivo": "notificacao_incompleta"}

        itens_atualizados: list[dict[str, Any]] = []
        for conta in vinculos:
            vendedor_id = conta.vendedor_id
            token = self._conectar.token_ativo(vendedor_id, QUICKSTORE)
            if not token:
                continue
            try:
                dados_item = self._gateway.obter_anuncio(token, item_id)
            except FalhaNoMarketplace as erro:
                if erro.status == 404:
                    standby = self._colocar_item_em_standby_no_vendedor(vendedor_id, item_id)
                    if standby is not None:
                        itens_atualizados.append(standby)
                else:
                    log.warning("Falha ao buscar item %s na QuickStore para vendedor %s: %s", item_id, vendedor_id, erro)
                continue

            dono_item = str(dados_item.get("seller_id") or "").strip()
            if dono_item and dono_item != user_id:
                log.warning(
                    "Tentativa de spoofing bloqueada no webhook de item QuickStore: item %s pertence a %s, não a %s.",
                    item_id,
                    dono_item,
                    user_id,
                )
                continue

            resultado = self._sincronizar_item_do_vendedor(vendedor_id, item_id, dados_item)
            if resultado is not None:
                itens_atualizados.append(resultado)

        return {
            "status": "ok",
            "topico": TOPICO_ITENS,
            "recurso": recurso,
            "itens_atualizados": itens_atualizados,
        }

    def executar(
        self,
        notificacao: dict[str, Any],
        *,
        topico_header: str | None = None,
    ) -> dict[str, Any]:
        topico = str(topico_header or notificacao.get("topic") or "").strip().lower()
        recurso = str(notificacao.get("resource") or "").strip()
        user_id = str(notificacao.get("user_id") if notificacao.get("user_id") is not None else "").strip()

        if not topico:
            topico = TOPICO_ITENS if recurso.startswith(("/items/", "items/")) else TOPICO_PEDIDOS

        if topico not in TOPICOS_SUPORTADOS:
            return {"status": "ignorado", "motivo": "topico_nao_suportado", "topico": topico}

        if not recurso or not user_id:
            return {"status": "ignorado", "motivo": "notificacao_incompleta"}

        vinculos = self._contas.buscar_por_conta_externa(QUICKSTORE, user_id)
        if not vinculos:
            log.info("Webhook QuickStore recebido para user_id=%s sem conta vinculada.", user_id)
            return {"status": "ignorado", "motivo": "conta_nao_vinculada"}

        if topico == TOPICO_ITENS or recurso.startswith(("/items/", "items/")):
            return self._executar_webhook_item(recurso, user_id, vinculos)

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
