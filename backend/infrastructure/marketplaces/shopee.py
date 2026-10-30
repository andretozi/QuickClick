"""
Infraestrutura · Shopee Open Platform API v2: cliente assinado e o esboço do gateway.

Sem OAuth nem chamada real nesta fase: o cliente assina e monta as chamadas, e os testes usam
transporte falso. Tudo o que vem da documentação da Shopee está marcado "conferir na doc oficial da Shopee".
"""

import hashlib
import hmac
import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from backend.application.portas import FalhaNoMarketplace, GatewayMarketplace
from backend.domain.erros import ServicoIndisponivel
from backend.infrastructure.configuracao import LeitorDeConfiguracao, configuracao

# Produção global; conferir na doc oficial da Shopee qual host atende o Brasil e qual é o de teste
HOST_SHOPEE = "https://partner.shopeemobile.com"


class _SemQueryAssinadaNoLog(logging.Filter):
    """O httpx registra a URL de cada pedido em INFO (o main.py liga INFO): na Shopee ela leva sign e access_token."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                a.copy_with(query=None) if isinstance(a, httpx.URL) and "sign" in a.params else a for a in record.args
            )
        return True


logging.getLogger("httpx").addFilter(_SemQueryAssinadaNoLog())


def assinar(partner_key: str, partner_id: str, caminho: str, timestamp: int,
            access_token: str = "", shop_id: str = "") -> str:
    """HMAC SHA256 (hex minúsculo) de partner_id + caminho + timestamp + access_token + shop_id; a chamada
    pública (autorização) vai sem token e sem loja. Ordem do plano multimarketplace: conferir na doc oficial da Shopee."""
    base = f"{partner_id}{caminho}{timestamp}{access_token}{shop_id}"
    return hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()


class ClienteShopee:
    def __init__(self, partner_id: str | None, partner_key: str | None, host: str = HOST_SHOPEE,
                 client: httpx.Client | None = None, relogio: Callable[[], float] = time.time):
        self._partner_id = (partner_id or "").strip()
        self._partner_key = (partner_key or "").strip()
        self._host = host.rstrip("/")
        self._client = client
        self._relogio = relogio

    def __repr__(self) -> str:
        return f"ClienteShopee(host={self._host!r})"

    def _parametros(self, caminho: str, access_token: str, shop_id: str) -> dict[str, str]:
        if not self._partner_id or not self._partner_key:
            raise ServicoIndisponivel("A integração com a Shopee ainda não está configurada.")
        timestamp = int(self._relogio())
        parametros = {"partner_id": self._partner_id, "timestamp": str(timestamp),
                      "sign": assinar(self._partner_key, self._partner_id, caminho, timestamp, access_token, shop_id)}
        if access_token or shop_id:
            parametros |= {"access_token": access_token, "shop_id": shop_id}
        return parametros

    def get(self, caminho: str, params: dict[str, Any] | None = None, *,
            access_token: str = "", shop_id: str = "") -> dict[str, Any]:
        return self._chamar("GET", caminho, access_token, shop_id, params=params)

    def post(self, caminho: str, *, json: dict[str, Any] | None = None, files: dict[str, Any] | None = None,
             access_token: str = "", shop_id: str = "") -> dict[str, Any]:
        """POST com corpo JSON ou multipart (files, como no upload de foto)."""
        return self._chamar("POST", caminho, access_token, shop_id, json=json, files=files)

    def _chamar(self, metodo: str, caminho: str, access_token: str, shop_id: str, *,
                params: dict[str, Any] | None = None, **corpo: Any) -> dict[str, Any]:
        parametros = {**(params or {}), **self._parametros(caminho, access_token, shop_id)}
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=15.0)
        # Erros relançados fora do except: a exceção do httpx (com a URL assinada) não fica nem no __context__
        try:
            resposta = self._client.request(metodo, f"{self._host}{caminho}", params=parametros, **corpo)
        except httpx.HTTPError:
            resposta = None
        if resposta is None:
            raise FalhaNoMarketplace("A Shopee não respondeu. Tente de novo em instantes.")
        try:
            dados = resposta.json()
        except ValueError:
            dados = None
        if resposta.is_error or not isinstance(dados, dict) or dados.get("error"):
            erro = str(dados.get("error") or "") if isinstance(dados, dict) else ""
            # Só o código do erro: a mensagem da Shopee pode repetir parâmetros do pedido
            raise FalhaNoMarketplace(f"A Shopee recusou o pedido ({resposta.status_code}).",
                                     resposta.status_code, {"error": erro} if erro else None)
        return dados


def cliente_shopee_da_configuracao(leitor: LeitorDeConfiguracao | None = None,
                                   client: httpx.Client | None = None) -> ClienteShopee:
    leitor = leitor or configuracao()
    return ClienteShopee(leitor.texto("SHOPEE_PARTNER_ID"), leitor.texto("SHOPEE_PARTNER_KEY"), client=client)


class GatewayShopee(GatewayMarketplace):
    slug = "shopee"
