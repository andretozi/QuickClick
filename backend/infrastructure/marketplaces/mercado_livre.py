"""
Infraestrutura · Gateway OAuth 2.0 e API REST do Mercado Livre.

Comunicação direta com a API do Mercado Livre (https://api.mercadolibre.com)
usando httpx, em conformidade com as diretrizes oficiais de desenvolvimento do Meli.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from backend.application.portas import FalhaNoMarketplace
from backend.domain.conta_vinculada import CredenciaisOAuth

URL_AUTH_ML = "https://auth.mercadolivre.com.br/authorization"
URL_TOKEN_ML = "https://api.mercadolibre.com/oauth/token"
URL_API_BASE = "https://api.mercadolibre.com"
REDIRECT_URI_PADRAO = "https://quickclick.azurewebsites.net/api/marketplaces/mercado-livre/callback"


def _agora_utc() -> datetime:
    return datetime.now(UTC)


class ErroDoMercadoLivre(FalhaNoMarketplace):
    """Resposta de erro da API do Mercado Livre, com o status HTTP (0 quando nem respondeu)."""


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
        # Os valores vêm da configuração (backend/infrastructure/configuracao), pela raiz de composição
        self._client_id = (client_id or "").strip()
        self._client_secret = (client_secret or "").strip()
        self._redirect_uri = (redirect_uri or REDIRECT_URI_PADRAO).strip()
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
                "Credenciais do Mercado Livre não configuradas. "
                "Defina MERCADO_LIVRE_CLIENT_ID e MERCADO_LIVRE_CLIENT_SECRET (rode python -m scripts.verificar_config)."
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
                files=files,
            )
            resposta.raise_for_status()
            return resposta.json()
        except httpx.HTTPStatusError as erro:
            detalhe = erro.response.text
            try:
                corpo = erro.response.json()
            except Exception:
                corpo = None
            raise ErroDoMercadoLivre(f"{mensagem_erro} ({erro.response.status_code}): {detalhe[:500]}",
                                     erro.response.status_code, corpo) from erro
        except Exception as erro:
            raise ErroDoMercadoLivre(f"{mensagem_erro}: {type(erro).__name__}") from erro

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

    # ------------------------------------------------------------------
    # Dados para a IA do criar anúncio e a publicação montada no back
    # ------------------------------------------------------------------

    def descobrir_dominio(self, termos: str, access_token: str) -> list[dict[str, Any]]:
        """Preditor de categoria: GET /sites/MLB/domain_discovery/search?q=..."""
        return self._executar_requisicao(
            "GET", f"{URL_API_BASE}/sites/MLB/domain_discovery/search", access_token=access_token,
            params={"q": termos, "limit": 1}, mensagem_erro="Falha ao descobrir a categoria no Mercado Livre",
        ) or []

    def atributos_da_categoria(self, categoria_id: str, access_token: str) -> list[dict[str, Any]]:
        """GET /categories/{id}/attributes"""
        return self._executar_requisicao(
            "GET", f"{URL_API_BASE}/categories/{quote(categoria_id, safe='')}/attributes", access_token=access_token,
            mensagem_erro="Falha ao ler os atributos da categoria no Mercado Livre",
        ) or []

    def buscar_itens(self, termos: str, categoria_id: str | None, condicao: str | None,
                     access_token: str, limite: int = 50) -> dict[str, Any]:
        """GET /sites/MLB/search (itens ativos parecidos). Para muitos apps responde 403: quem chama trata."""
        params: dict[str, Any] = {"q": termos, "limit": limite}
        if categoria_id:
            params["category"] = categoria_id
        if condicao in ("new", "used"):
            params["condition"] = condicao
        return self._executar_requisicao(
            "GET", f"{URL_API_BASE}/sites/MLB/search", access_token=access_token, params=params,
            mensagem_erro="Falha ao buscar itens parecidos no Mercado Livre",
        )

    def custo_de_venda(self, preco: float, categoria_id: str, access_token: str,
                       tipo_de_anuncio: str = "gold_special") -> Any:
        """GET /sites/MLB/listing_prices (tarifa do anúncio; gold_special é o Clássico)."""
        return self._executar_requisicao(
            "GET", f"{URL_API_BASE}/sites/MLB/listing_prices", access_token=access_token,
            params={"price": f"{preco:.2f}", "category_id": categoria_id, "listing_type_id": tipo_de_anuncio},
            mensagem_erro="Falha ao consultar a tarifa no Mercado Livre",
        )

    def subir_imagem(self, access_token: str, jpeg: bytes, nome: str = "foto.jpg") -> str:
        """POST /pictures/items/upload (multipart, campo file). Devolve o id da imagem."""
        dados = self._executar_requisicao(
            "POST", f"{URL_API_BASE}/pictures/items/upload", access_token=access_token,
            files={"file": (nome, jpeg, "image/jpeg")}, mensagem_erro="Falha ao subir a foto para o Mercado Livre",
        )
        imagem_id = (dados or {}).get("id")
        if not imagem_id:
            raise ErroDoMercadoLivre("O Mercado Livre não devolveu o id da foto.")
        return str(imagem_id)

    def gravar_descricao(self, access_token: str, item_id: str, texto: str) -> Any:
        """POST /items/{id}/description com a descrição em texto simples (plain_text)."""
        return self._executar_requisicao(
            "POST", f"{URL_API_BASE}/items/{quote(item_id, safe='')}/description", access_token=access_token,
            headers={"Content-Type": "application/json"}, json={"plain_text": texto},
            mensagem_erro="Falha ao gravar a descrição no Mercado Livre",
        )

