"""
Infraestrutura · Gateway OAuth 2.0, API REST e validação de Webhooks da QuickStore.

A QuickStore implementa o mesmo contrato de rotas e payloads da API do Mercado Livre
(sob a URL base configurada em QUICKSTORE_BASE_URL), além de enviar notificações de
vendas (tópico orders_v2) assinadas com HMAC-SHA256 usando QUICKSTORE_CLIENT_SECRET.
"""

import base64
import hashlib
import hmac
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from backend.application.portas import FalhaNoMarketplace
from backend.domain.conta_vinculada import CredenciaisOAuth

URL_BASE_QUICKSTORE_PADRAO = "https://quickstore-fwdyccgqfudmd0b9.chilecentral-01.azurewebsites.net"
CLIENT_ID_QUICKSTORE_PADRAO = "QuickClickApp"
CLIENT_SECRET_QUICKSTORE_PADRAO = "QS_QUICKCLICK_OFFICIAL_2026"
REDIRECT_URI_QUICKSTORE_PADRAO = (
    "https://quickclick-cudkaseffgceaaaq.chilecentral-01.azurewebsites.net/api/quickstore/callback"
)


def _agora_utc() -> datetime:
    return datetime.now(UTC)


def _extrair_descricao(valor: Any) -> str:
    if isinstance(valor, dict):
        return str(valor.get("plain_text") or valor.get("text") or "").strip()
    if valor is None:
        return ""
    return str(valor).strip()


def _resumo_do_item(body: dict[str, Any], descricao: str = "") -> dict[str, Any]:
    fotos: list[str] = []
    for p in body.get("pictures") or []:
        if isinstance(p, dict):
            url_foto = p.get("secure_url") or p.get("url") or p.get("source")
            if url_foto:
                fotos.append(str(url_foto))
        elif isinstance(p, str) and p.strip():
            fotos.append(p.strip())
    atributos: list[dict[str, str]] = []
    for a in body.get("attributes") or []:
        if not isinstance(a, dict) or (a.get("tags") or {}).get("hidden"):
            continue
        nome = str(a.get("name") or a.get("id") or "").strip()
        valor_bruto = a.get("value_name") if a.get("value_name") is not None else a.get("value")
        valor = str(valor_bruto if valor_bruto is not None else "").strip()
        if nome and valor:
            atributos.append({"id": str(a.get("id") or ""), "name": nome, "value": valor})
    thumbnail = str(body.get("secure_thumbnail") or body.get("thumbnail") or (fotos[0] if fotos else ""))
    descricao_final = (
        _extrair_descricao(descricao)
        or _extrair_descricao(body.get("description"))
        or _extrair_descricao(body.get("plain_text"))
    )
    return {
        "id": body.get("id"),
        "title": body.get("title") or body.get("family_name") or "",
        "family_name": body.get("family_name"),
        "description": descricao_final,
        "price": body.get("price"),
        "status": body.get("status"),
        "condition": body.get("condition") or "new",
        "available_quantity": body.get("available_quantity", 0),
        "sold_quantity": body.get("sold_quantity", 0),
        "category_id": body.get("category_id"),
        "permalink": body.get("permalink"),
        "thumbnail": thumbnail,
        "pictures": fotos or ([thumbnail] if thumbnail else []),
        "attributes": atributos,
        "health": body.get("health"),
        "seller_id": str(body.get("seller_id") or ""),
        "tags": [str(t) for t in (body.get("tags") or []) if isinstance(t, str)],
        "last_updated": body.get("last_updated") or body.get("date_created"),
    }


class ErroDaQuickStore(FalhaNoMarketplace):
    """Resposta de erro da API da QuickStore, com o status HTTP (0 quando nem respondeu)."""


class GatewayQuickStore:
    slug = "quickstore"
    validade_do_token = timedelta(hours=6)

    def __init__(
        self,
        base_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        agora: Callable[[], datetime] = _agora_utc,
        client: httpx.Client | None = None,
    ):
        self._agora = agora
        self._base_url = (base_url or URL_BASE_QUICKSTORE_PADRAO).strip().rstrip("/")
        self._client_id = (client_id or CLIENT_ID_QUICKSTORE_PADRAO).strip()
        segredo = CLIENT_SECRET_QUICKSTORE_PADRAO if client_secret is None else client_secret
        self._client_secret = segredo.strip()
        self._redirect_uri = (redirect_uri or REDIRECT_URI_QUICKSTORE_PADRAO).strip()
        self._client = client

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def client_id(self) -> str:
        return self._client_id

    @property
    def tem_segredo_configurado(self) -> bool:
        return bool(self._client_secret)

    def _obter_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=15.0)
        return self._client

    def fechar(self) -> None:
        if self._client is not None and not self._client.is_closed:
            self._client.close()

    def _garantir_configurado(self) -> None:
        if not self._client_id or not self._client_secret:
            raise RuntimeError(
                "Credenciais da QuickStore não configuradas. "
                "Defina QUICKSTORE_CLIENT_ID e QUICKSTORE_CLIENT_SECRET (rode python -m scripts.verificar_config)."
            )

    def _executar_requisicao(
        self,
        metodo: str,
        url: str,
        *,
        access_token: str | None = None,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        mensagem_erro: str = "Falha na comunicação com a QuickStore",
    ) -> Any:
        cabecalhos: dict[str, str] = {"Accept": "application/json"}
        if access_token:
            cabecalhos["Authorization"] = f"Bearer {access_token}"
        if headers:
            cabecalhos.update(headers)

        client = self._obter_client()
        try:
            resposta = client.request(
                metodo,
                url,
                headers=cabecalhos,
                data=data,
                json=json,
                params=params,
                files=files,
            )
            resposta.raise_for_status()
            if not resposta.content:
                return {}
            return resposta.json()
        except httpx.HTTPStatusError as erro:
            detalhe = erro.response.text
            try:
                corpo = erro.response.json()
            except Exception:
                corpo = None
            raise ErroDaQuickStore(
                f"{mensagem_erro} ({erro.response.status_code}): {detalhe[:500]}",
                erro.response.status_code,
                corpo,
            ) from erro
        except Exception as erro:
            raise ErroDaQuickStore(f"{mensagem_erro}: {type(erro).__name__}") from erro

    def gerar_url_autorizacao(self, estado: str) -> str:
        """Gera a URL de autorização OAuth 2.0 na QuickStore."""
        self._garantir_configurado()
        return (
            f"{self._base_url}/authorization?response_type=code"
            f"&client_id={quote(self._client_id, safe='')}"
            f"&redirect_uri={quote(self._redirect_uri, safe='')}"
            f"&state={quote(estado, safe='')}"
        )

    def _requisitar_token(self, payload: dict[str, Any], mensagem_erro: str) -> dict[str, Any]:
        self._garantir_configurado()
        return self._executar_requisicao(
            "POST",
            f"{self._base_url}/oauth/token",
            headers={"Content-Type": "application/json"},
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                **payload,
            },
            mensagem_erro=mensagem_erro,
        )

    def _criar_credenciais(
        self,
        dados: dict[str, Any],
        refresh_padrao: str = "",
        apelido: str | None = None,
        conta_externa_override: str | None = None,
    ) -> CredenciaisOAuth:
        expires_in = int(dados.get("expires_in", 21600) or 21600)
        conta_id = conta_externa_override or str(dados.get("user_id", ""))
        return CredenciaisOAuth(
            access_token=dados["access_token"],
            refresh_token=dados.get("refresh_token", refresh_padrao),
            expira_em=self._agora() + timedelta(seconds=expires_in),
            conta_externa_id=conta_id,
            apelido=apelido,
        )

    def trocar_codigo_por_token(self, codigo: str) -> CredenciaisOAuth:
        """Troca o código OAuth retornado pela QuickStore por access_token e refresh_token."""
        if not codigo:
            raise ValueError("Código de autorização vazio.")

        dados = self._requisitar_token(
            {
                "grant_type": "authorization_code",
                "code": codigo,
                "redirect_uri": self._redirect_uri,
            },
            mensagem_erro="Erro ao obter token da QuickStore",
        )

        access_token = dados["access_token"]
        user_id = str(dados.get("user_id", ""))
        try:
            perfil = self.obter_perfil_usuario(access_token)
            apelido = perfil.get("nickname")
            if not user_id and perfil.get("id") is not None:
                user_id = str(perfil["id"])
        except Exception:
            apelido = f"QS_{user_id}" if user_id else "QUICKSTORE"

        return self._criar_credenciais(dados, apelido=apelido, conta_externa_override=user_id)

    def renovar_token(self, refresh_token: str) -> CredenciaisOAuth:
        """Renova o access_token utilizando o refresh_token junto à QuickStore."""
        if not refresh_token:
            raise ValueError("Refresh token vazio.")

        dados = self._requisitar_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            mensagem_erro="Falha ao renovar token com a QuickStore",
        )
        return self._criar_credenciais(dados, refresh_padrao=refresh_token)

    def obter_perfil_usuario(self, access_token: str) -> dict[str, Any]:
        """GET /users/me para obter perfil do vendedor conectado na QuickStore."""
        return self._executar_requisicao(
            "GET",
            f"{self._base_url}/users/me",
            access_token=access_token,
            mensagem_erro="Falha ao obter perfil do usuário na QuickStore",
        )

    def _ler_descricao(self, access_token: str, item_id: str) -> str:
        if not item_id:
            return ""
        try:
            dados = self._executar_requisicao(
                "GET",
                f"{self._base_url}/items/{quote(str(item_id), safe='')}/description",
                access_token=access_token,
                mensagem_erro="Falha ao ler descrição do anúncio na QuickStore",
            )
            if not isinstance(dados, dict):
                return ""
            return str(dados.get("plain_text") or dados.get("text") or "").strip()
        except ErroDaQuickStore:
            return ""

    def listar_anuncios(self, access_token: str, conta_externa_id: str | None = None) -> list[dict[str, Any]]:
        """GET /users/{user_id}/items/search para listar os produtos do vendedor na QuickStore."""
        user_id = conta_externa_id
        if not user_id:
            perfil = self.obter_perfil_usuario(access_token)
            user_id = str(perfil.get("id", ""))

        busca_dados = self._executar_requisicao(
            "GET",
            f"{self._base_url}/users/{quote(str(user_id), safe='')}/items/search",
            access_token=access_token,
            params={"limit": 50},
            mensagem_erro="Falha ao listar anúncios da QuickStore",
        )
        resultados = busca_dados.get("results", []) if isinstance(busca_dados, dict) else []
        if not resultados:
            return []

        # A QuickStore pode retornar objetos completos de item em `results` ou apenas lista de IDs (padrão ML).
        if isinstance(resultados[0], dict):
            produtos = []
            for item in resultados[:50]:
                if not isinstance(item, dict):
                    continue
                sub_status = item.get("sub_status") or []
                if isinstance(sub_status, list) and "deleted" in sub_status:
                    continue
                item_id = str(item.get("id") or "")
                descricao = _extrair_descricao(item.get("description")) or _extrair_descricao(item.get("plain_text"))
                if not descricao and item_id and item.get("status") != "closed":
                    descricao = self._ler_descricao(access_token, item_id)
                produtos.append(_resumo_do_item(item, descricao))
            return produtos

        lote = [str(item_id) for item_id in resultados[:20] if item_id]
        try:
            respostas = self._executar_requisicao(
                "GET",
                f"{self._base_url}/items",
                access_token=access_token,
                params={"ids": ",".join(lote)},
                mensagem_erro="Falha ao buscar detalhes dos anúncios na QuickStore",
            )
        except ErroDaQuickStore:
            respostas = None

        produtos = []
        if isinstance(respostas, list):
            for item_bloco in respostas:
                if isinstance(item_bloco, dict) and item_bloco.get("code") == 200:
                    body = item_bloco.get("body", {})
                elif isinstance(item_bloco, dict) and item_bloco.get("id"):
                    body = item_bloco
                else:
                    continue
                sub_status = body.get("sub_status") or []
                if isinstance(sub_status, list) and "deleted" in sub_status:
                    continue
                descricao = _extrair_descricao(body.get("description")) or _extrair_descricao(body.get("plain_text"))
                if not descricao:
                    descricao = self._ler_descricao(access_token, str(body.get("id") or ""))
                produtos.append(_resumo_do_item(body, descricao))
            return produtos

        for item_id in lote:
            try:
                produtos.append(self.obter_anuncio(access_token, item_id))
            except ErroDaQuickStore:
                continue
        return produtos

    def obter_anuncio(self, access_token: str, item_id: str) -> dict[str, Any]:
        """GET /items/{id} + GET /items/{id}/description para sincronizar ou exibir detalhes."""
        body = self._executar_requisicao(
            "GET",
            f"{self._base_url}/items/{quote(item_id, safe='')}",
            access_token=access_token,
            mensagem_erro="Falha ao buscar anúncio na QuickStore",
        )
        corpo = body if isinstance(body, dict) else {}
        descricao = _extrair_descricao(corpo.get("description")) or _extrair_descricao(corpo.get("plain_text"))
        if not descricao:
            descricao = self._ler_descricao(access_token, item_id)
        return _resumo_do_item(corpo, descricao)

    def publicar_anuncio(self, access_token: str, dados_produto: dict[str, Any]) -> dict[str, Any]:
        """POST /items para publicar um novo anúncio na QuickStore."""
        return self._executar_requisicao(
            "POST",
            f"{self._base_url}/items",
            access_token=access_token,
            headers={"Content-Type": "application/json"},
            json=dados_produto,
            mensagem_erro="Erro ao publicar anúncio na QuickStore",
        )

    def atualizar_anuncio(self, access_token: str, item_id: str, dados_produto: dict[str, Any]) -> dict[str, Any]:
        """PUT /items/{item_id} para atualizar preço, estoque ou status na QuickStore."""
        return self._executar_requisicao(
            "PUT",
            f"{self._base_url}/items/{quote(item_id, safe='')}",
            access_token=access_token,
            headers={"Content-Type": "application/json"},
            json=dados_produto,
            mensagem_erro="Erro ao atualizar anúncio na QuickStore",
        )

    def gravar_descricao(self, access_token: str, item_id: str, texto: str) -> Any:
        """POST /items/{item_id}/description com {"plain_text": texto}."""
        return self._executar_requisicao(
            "POST",
            f"{self._base_url}/items/{quote(item_id, safe='')}/description",
            access_token=access_token,
            headers={"Content-Type": "application/json"},
            json={"plain_text": texto},
            mensagem_erro="Falha ao gravar a descrição na QuickStore",
        )

    def atualizar_descricao(self, access_token: str, item_id: str, texto: str) -> Any:
        """PUT /items/{item_id}/description (ou POST se o item ainda não tinha descrição)."""
        url = f"{self._base_url}/items/{quote(item_id, safe='')}/description"
        try:
            return self._executar_requisicao(
                "PUT",
                url,
                access_token=access_token,
                headers={"Content-Type": "application/json"},
                json={"plain_text": texto},
                mensagem_erro="Falha ao atualizar a descrição na QuickStore",
            )
        except ErroDaQuickStore as erro:
            if erro.status not in (404, 405):
                raise
            return self.gravar_descricao(access_token, item_id, texto)

    def excluir_anuncio(self, access_token: str, item_id: str) -> dict[str, Any]:
        """DELETE /items/{item_id} (ou PUT status=closed) para encerrar o anúncio na QuickStore."""
        url = f"{self._base_url}/items/{quote(item_id, safe='')}"
        try:
            resposta = self._executar_requisicao(
                "DELETE",
                url,
                access_token=access_token,
                mensagem_erro="Falha ao excluir anúncio na QuickStore",
            )
            return resposta if isinstance(resposta, dict) else {"id": item_id, "status": "closed"}
        except ErroDaQuickStore as erro:
            if erro.status not in (404, 405):
                raise
            return self._executar_requisicao(
                "PUT",
                url,
                access_token=access_token,
                headers={"Content-Type": "application/json"},
                json={"status": "closed"},
                mensagem_erro="Falha ao encerrar anúncio na QuickStore",
            )

    def descobrir_dominio(self, termos: str, access_token: str) -> list[dict[str, Any]]:
        """GET /sites/MLB/domain_discovery/search?q=..."""
        return self._executar_requisicao(
            "GET",
            f"{self._base_url}/sites/MLB/domain_discovery/search",
            access_token=access_token,
            params={"q": termos, "limit": 1},
            mensagem_erro="Falha ao descobrir a categoria na QuickStore",
        ) or []

    def atributos_da_categoria(self, categoria_id: str, access_token: str) -> list[dict[str, Any]]:
        """GET /categories/{category_id}/attributes para ler a ficha técnica na QuickStore."""
        return self._executar_requisicao(
            "GET",
            f"{self._base_url}/categories/{quote(categoria_id, safe='')}/attributes",
            access_token=access_token,
            mensagem_erro="Falha ao ler os atributos da categoria na QuickStore",
        ) or []

    def subir_imagem(self, access_token: str, jpeg: bytes, nome: str = "foto.jpg") -> str:
        """POST /pictures/items/upload (multipart, campo file) ou fallback data:image/jpeg;base64 quando não suportado."""
        try:
            dados = self._executar_requisicao(
                "POST",
                f"{self._base_url}/pictures/items/upload",
                access_token=access_token,
                files={"file": (nome, jpeg, "image/jpeg")},
                mensagem_erro="Falha ao subir a foto para a QuickStore",
            )
        except ErroDaQuickStore as erro:
            if erro.status in (404, 405, 501):
                codificado = base64.b64encode(jpeg).decode("ascii")
                return f"data:image/jpeg;base64,{codificado}"
            raise
        imagem_id = (
            (dados or {}).get("id")
            or (dados or {}).get("secure_url")
            or (dados or {}).get("url")
            or (dados or {}).get("source")
        )
        if not imagem_id:
            raise ErroDaQuickStore("A QuickStore não devolveu o id da foto.")
        return str(imagem_id)

    def obter_pedido(self, access_token: str, resource_ou_order_id: str) -> dict[str, Any]:
        """GET /orders/{order_id} para consultar os detalhes completos de uma venda recebida via webhook."""
        recurso = str(resource_ou_order_id or "").strip()
        if not recurso:
            raise ValueError("Identificador do pedido vazio.")
        if recurso.startswith("/orders/"):
            order_id = recurso.removeprefix("/orders/").strip("/")
        elif recurso.startswith("orders/"):
            order_id = recurso.removeprefix("orders/").strip("/")
        else:
            order_id = recurso.strip("/")
        if not order_id or len(order_id) > 64 or "/" in order_id or ".." in order_id or not order_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Identificador do pedido inválido.")
        dados = self._executar_requisicao(
            "GET",
            f"{self._base_url}/orders/{quote(order_id, safe='')}",
            access_token=access_token,
            mensagem_erro="Falha ao consultar pedido na QuickStore",
        )
        return dados if isinstance(dados, dict) else {}

    def validar_assinatura_webhook(self, corpo_bruto: bytes, assinatura_header: str | None) -> bool:
        """Valida o cabeçalho X-QuickStore-Signature (`sha256=<hex>`) com HMAC-SHA256 usando QUICKSTORE_CLIENT_SECRET."""
        if not self._client_secret:
            return False
        assinatura = (assinatura_header or "").strip()
        if not assinatura:
            return False
        if assinatura.lower().startswith("sha256="):
            recebida_hex = assinatura[7:].strip().lower()
        else:
            recebida_hex = assinatura.lower()
        if not recebida_hex:
            return False
        esperada_hex = hmac.new(
            self._client_secret.encode("utf-8"),
            corpo_bruto,
            hashlib.sha256,
        ).hexdigest().lower()
        return hmac.compare_digest(esperada_hex, recebida_hex)
