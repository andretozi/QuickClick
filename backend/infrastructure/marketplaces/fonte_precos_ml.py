"""
Infraestrutura · Dados reais do Mercado Livre para a IA (com o token do vendedor)

    descobrir_categoria    GET /sites/MLB/domain_discovery/search?q=...
    atributos_da_categoria GET /categories/{id}/attributes (cache no banco por 24 horas)
    buscar_parecidos       GET /sites/MLB/search (até 50 ativos parecidos)
    tarifa                 GET /sites/MLB/listing_prices (anúncio Clássico, gold_special)

A busca de itens responde 403 para muitos apps (restrição do Mercado Livre, mesmo com token válido):
nesse caso devolve None, avisa uma vez no log e só tenta de novo depois de uma hora. A análise então
usa a reserva (busca na web nos marketplaces, no pago) ou pede o preço ao vendedor.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.application.ia.modelos import CategoriaSugerida, PrecoObservado
from backend.application.ia.portas import CacheDeCategoriasML
from backend.domain.ia.atributos_ml import AtributoML
from backend.infrastructure.marketplaces.mercado_livre import ErroDoMercadoLivre, GatewayMercadoLivre

log = logging.getLogger("quickclick.marketplaces")

VALIDADE_DOS_ATRIBUTOS = timedelta(hours=24)
PAUSA_DEPOIS_DE_403 = timedelta(hours=1)
CONDICAO_NO_ML = {"novo": "new", "usado": "used", "recondicionado": "used"}


def _agora() -> datetime:
    return datetime.now(UTC)


def _resumo_do_atributo(bruto: dict[str, Any]) -> dict[str, Any]:
    """O que interessa guardar no cache (o atributo completo do ML é bem maior)."""
    return {
        "id": bruto.get("id"),
        "name": bruto.get("name"),
        "tags": {k: v for k, v in (bruto.get("tags") or {}).items() if k in ("required", "catalog_required")},
        "values": [{"id": v.get("id"), "name": v.get("name")} for v in (bruto.get("values") or [])[:200]
                   if isinstance(v, dict)],
    }


class FontePrecosMercadoLivre:
    def __init__(self, gateway: GatewayMercadoLivre, cache: CacheDeCategoriasML,
                 relogio: Callable[[], datetime] = _agora):
        self._gateway = gateway
        self._cache = cache
        self._relogio = relogio
        self._busca_pausada_ate: datetime | None = None

    def descobrir_categoria(self, termos: list[str], access_token: str) -> CategoriaSugerida | None:
        if not termos:
            return None
        try:
            achados = self._gateway.descobrir_dominio(termos[0], access_token)
        except ErroDoMercadoLivre as erro:
            log.warning("Mercado Livre: categoria não descoberta (%s).", erro.status or "sem resposta")
            return None
        primeiro = next((a for a in achados if isinstance(a, dict) and a.get("category_id")), None)
        if primeiro is None:
            return None
        return CategoriaSugerida(str(primeiro["category_id"]), str(primeiro.get("category_name") or ""),
                                 str(primeiro.get("domain_name") or ""))

    def atributos_da_categoria(self, categoria_id: str, access_token: str) -> list[AtributoML]:
        agora = self._relogio()
        guardados = self._cache.obter(categoria_id, agora)
        if guardados is None:
            try:
                brutos = self._gateway.atributos_da_categoria(categoria_id, access_token)
            except ErroDoMercadoLivre as erro:
                log.warning("Mercado Livre: atributos da categoria não lidos (%s).", erro.status or "sem resposta")
                return []
            guardados = [_resumo_do_atributo(b) for b in brutos if isinstance(b, dict) and b.get("id")]
            self._cache.salvar(categoria_id, guardados, agora + VALIDADE_DOS_ATRIBUTOS)
        return [AtributoML.de_api(a) for a in guardados]

    def buscar_parecidos(self, termos: list[str], categoria_id: str | None, condicao: str,
                         access_token: str) -> list[PrecoObservado] | None:
        agora = self._relogio()
        if not termos or (self._busca_pausada_ate and agora < self._busca_pausada_ate):
            return None
        try:
            dados = self._gateway.buscar_itens(termos[0], categoria_id, CONDICAO_NO_ML.get(condicao), access_token)
        except ErroDoMercadoLivre as erro:
            if erro.status in (401, 403):
                self._busca_pausada_ate = agora + PAUSA_DEPOIS_DE_403
                log.warning("Mercado Livre: a busca de itens está restrita para este app (%s). "
                            "Usando a reserva do preço por uma hora.", erro.status)
            else:
                log.warning("Mercado Livre: busca de itens falhou (%s).", erro.status or "sem resposta")
            return None
        observados = []
        for item in (dados or {}).get("results") or []:
            if not isinstance(item, dict) or item.get("currency_id", "BRL") != "BRL":
                continue
            try:
                preco = round(float(item.get("price") or 0) * 100)
            except (TypeError, ValueError):
                continue
            if preco > 0:
                frete = bool((item.get("shipping") or {}).get("free_shipping"))
                observados.append(PrecoObservado(preco, frete))
        return observados

    def tarifa(self, preco_centavos: int, categoria_id: str, access_token: str) -> int | None:
        try:
            dados = self._gateway.custo_de_venda(preco_centavos / 100, categoria_id, access_token)
        except ErroDoMercadoLivre as erro:
            log.warning("Mercado Livre: tarifa não consultada (%s).", erro.status or "sem resposta")
            return None
        if isinstance(dados, list):
            dados = next((d for d in dados if isinstance(d, dict) and d.get("listing_type_id") == "gold_special"),
                         dados[0] if dados else None)
        try:
            return round(float((dados or {}).get("sale_fee_amount")) * 100)
        except (TypeError, ValueError):
            return None
