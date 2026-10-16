"""
Infraestrutura · Gateway OAuth 2.0 e API REST do Mercado Livre.

Comunicação direta com a API do Mercado Livre (https://api.mercadolibre.com)
usando httpx, em conformidade com as diretrizes oficiais de desenvolvimento do Meli.
"""

import os
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from backend.domain.conta_vinculada import CredenciaisOAuth

URL_AUTH_ML = "https://auth.mercadolivre.com.br/authorization"
URL_TOKEN_ML = "https://api.mercadolibre.com/oauth/token"
URL_API_BASE = "https://api.mercadolibre.com"


def _agora_utc() -> datetime:
    return datetime.now(UTC)


class GatewayMercadoLivre:
    slug = "mercado-livre"
    validade_do_token = timedelta(hours=6)

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        agora: Callable[[], datetime] = _agora_utc,
        client: httpx.Client | None = None,
    ):
        self._agora = agora
        self._client_id = client_id or os.getenv("MERCADO_LIVRE_CLIENT_ID", "").strip()
        self._client_secret = client_secret or os.getenv("MERCADO_LIVRE_CLIENT_SECRET", "").strip()
        self._redirect_uri = (
            redirect_uri
            or os.getenv(
                "MERCADO_LIVRE_REDIRECT_URI",
                "https://quickclick.azurewebsites.net/api/marketplaces/mercado-livre/callback",
            )
        ).strip()
        self._client = client

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
                "Credenciais do Mercado Livre não configuradas no ambiente. "
                "Defina MERCADO_LIVRE_CLIENT_ID e MERCADO_LIVRE_CLIENT_SECRET no painel da Azure."
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
        mensagem_erro: str = "Falha na comunicação com o Mercado Livre",
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
            )
            resposta.raise_for_status()
            return resposta.json()
        except httpx.HTTPStatusError as erro:
            detalhe = erro.response.text
            raise RuntimeError(f"{mensagem_erro} ({erro.response.status_code}): {detalhe}") from erro
        except Exception as erro:
            raise RuntimeError(f"{mensagem_erro}: {erro}") from erro

    def gerar_url_autorizacao(self, estado: str) -> str:
        """Gera a URL oficial para o vendedor autorizar a conta no Mercado Livre."""
        self._garantir_configurado()
        return (
            f"{URL_AUTH_ML}?response_type=code"
            f"&client_id={quote(self._client_id, safe='')}"
            f"&redirect_uri={quote(self._redirect_uri, safe='')}"
            f"&state={quote(estado, safe='')}"
        )

    def _requisitar_token(self, payload: dict[str, Any], mensagem_erro: str) -> dict[str, Any]:
        self._garantir_configurado()
        return self._executar_requisicao(
            "POST",
            URL_TOKEN_ML,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
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
    ) -> CredenciaisOAuth:
        expires_in = dados.get("expires_in", 21600)
        return CredenciaisOAuth(
            access_token=dados["access_token"],
            refresh_token=dados.get("refresh_token", refresh_padrao),
            expira_em=self._agora() + timedelta(seconds=expires_in),
            conta_externa_id=str(dados.get("user_id", "")),
            apelido=apelido,
        )

    def trocar_codigo_por_token(self, codigo: str) -> CredenciaisOAuth:
        """Troca o authorization_code retornado pelo Mercado Livre pelos tokens reais de acesso."""
        if not codigo:
            raise ValueError("Código de autorização vazio.")

        dados = self._requisitar_token(
            {
                "grant_type": "authorization_code",
                "code": codigo,
                "redirect_uri": self._redirect_uri,
            },
            mensagem_erro="Erro ao obter token do Mercado Livre",
        )

        access_token = dados["access_token"]
        user_id = str(dados.get("user_id", ""))
        try:
            perfil = self.obter_perfil_usuario(access_token)
            apelido = perfil.get("nickname")
        except Exception:
            apelido = f"ML_{user_id}" if user_id else "MERCADO_LIVRE"

        return self._criar_credenciais(dados, apelido=apelido)

    def renovar_token(self, refresh_token: str) -> CredenciaisOAuth:
        """Renova o access token utilizando o refresh token junto à API do Mercado Livre."""
        if not refresh_token:
            raise ValueError("Refresh token vazio.")

        dados = self._requisitar_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            mensagem_erro="Falha ao renovar token com o Mercado Livre",
        )
        return self._criar_credenciais(dados, refresh_padrao=refresh_token)

    def obter_perfil_usuario(self, access_token: str) -> dict[str, Any]:
        """Obtém dados cadastrais e apelido do vendedor no Mercado Livre."""
        return self._executar_requisicao(
            "GET",
            f"{URL_API_BASE}/users/me",
            access_token=access_token,
            mensagem_erro="Falha ao obter perfil do usuário no Mercado Livre",
        )

    def listar_anuncios(self, access_token: str, conta_externa_id: str | None = None) -> list[dict[str, Any]]:
        """Lista os produtos/anúncios reais para monitoramento de preços, estoque e status."""
        user_id = conta_externa_id
        if not user_id:
            perfil = self.obter_perfil_usuario(access_token)
            user_id = str(perfil.get("id", ""))

        busca_dados = self._executar_requisicao(
            "GET",
            f"{URL_API_BASE}/users/{user_id}/items/search",
            access_token=access_token,
            params={"limit": 50},
            mensagem_erro="Falha ao listar anúncios do Mercado Livre",
        )
        item_ids = busca_dados.get("results", [])

        if not item_ids:
            return []

        lote = item_ids[:20]
        respostas = self._executar_requisicao(
            "GET",
            f"{URL_API_BASE}/items",
            access_token=access_token,
            params={"ids": ",".join(lote)},
            mensagem_erro="Falha ao buscar detalhes dos anúncios no Mercado Livre",
        )

        produtos = []
        for item_bloco in respostas:
            if item_bloco.get("code") == 200:
                body = item_bloco.get("body", {})
                produtos.append({
                    "id": body.get("id"),
                    "title": body.get("title"),
                    "price": body.get("price"),
                    "status": body.get("status"),
                    "available_quantity": body.get("available_quantity"),
                    "sold_quantity": body.get("sold_quantity"),
                    "permalink": body.get("permalink"),
                    "thumbnail": body.get("thumbnail"),
                })
        return produtos

    def publicar_anuncio(self, access_token: str, dados_produto: dict[str, Any]) -> dict[str, Any]:
        """Publica um novo produto na conta do vendedor no Mercado Livre."""
        return self._executar_requisicao(
            "POST",
            f"{URL_API_BASE}/items",
            access_token=access_token,
            headers={"Content-Type": "application/json"},
            json=dados_produto,
            mensagem_erro="Erro ao publicar anúncio no Mercado Livre",
        )
